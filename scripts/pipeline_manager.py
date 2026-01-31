"""
Pipeline Manager - Orchestrates the full video generation pipeline

Stages:
1. Scene Generation: Text → structured scenes
2. Test Mode Trimming: Trim to 3 scenes if --test
3. Audio Generation: Generate audio for each scene
4. Image Generation: Generate styled images (if --art-reference)
5. Video Generation: Generate videos from images
6. Assembly: Combine into final video
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scene_generator import SceneGenerator
# TODO: Import other components as stages are implemented
# from audio_generator import ParallelAudioGenerator
# from openai_responses_image_client import OpenAIResponsesImageClient
# from video_generator import VideoGenerator
# from openai_client import OpenAIClient
# from checkpoint_manager import CheckpointManager
import subprocess


class PipelineManager:
    """Manages the complete video generation pipeline."""

    def __init__(self, args, output_dir):
        """
        Initialize pipeline manager.

        Args:
            args: Parsed command line arguments
            output_dir: Path to output directory
        """
        self.args = args
        self.output_dir = Path(output_dir)
        # self.checkpoint = CheckpointManager(self.output_dir / 'checkpoint.json')

        # Initialize clients (TODO: as stages are implemented)
        self.image_client = None
        # if args.art_reference:
        #     self.image_client = OpenAIResponsesImageClient()

        self.scenes_file = self.output_dir / 'scenes.json'
        self.metadata_file = self.output_dir / 'metadata.json'

    def run(self):
        """Execute the full pipeline."""
        print("=" * 80)
        print("STARTING PIPELINE")
        print("=" * 80)
        print()

        start_time = datetime.now()

        try:
            # Stage 1: Scene Generation
            if self.args.text:
                original_scenes_data = self.generate_scenes()
            else:
                original_scenes_data = self.load_scenes()

            # Save original scenes first
            self.save_scenes(original_scenes_data)

            # Stage 2: Test Mode Trimming
            if self.args.test:
                scenes_data = self.trim_to_test_mode(original_scenes_data)
            else:
                scenes_data = original_scenes_data

            # Stage 3: Audio Generation
            if not self.args.skip_audio:
                self.generate_audio(scenes_data)

            # Stage 4: Image Generation
            if self.args.art_reference and not self.args.skip_video:
                self.generate_images(scenes_data)

            # Stage 5: Video Generation
            if not self.args.skip_video:
                self.generate_videos(scenes_data)

            # Stage 6: Assembly
            # Run assembly if:
            # 1. Video generation just completed, OR
            # 2. We're using existing scenes/videos and want to assemble them
            if not self.args.skip_video or self.args.scenes:
                self.assemble_final_video(scenes_data)

            # Generate report
            self.generate_report(scenes_data, start_time)

            print()
            print("=" * 80)
            print("✓ PIPELINE COMPLETE")
            print("=" * 80)
            print(f"Output: {self.output_dir}")
            print()

        except Exception as e:
            print(f"\n✗ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def generate_scenes(self):
        """Generate scenes from text."""
        print("─" * 80)
        print("STAGE 1: Scene Generation")
        print("─" * 80)

        # Read text file
        with open(self.args.text, 'r') as f:
            text_content = f.read()

        # Calculate default length if not specified
        # Formula: words ÷ 150 words/min = minutes
        # Convert to seconds: (words ÷ 150) × 60 = words × 0.4
        if self.args.length is None:
            word_count = len(text_content.split())
            calculated_minutes = word_count / 150
            self.args.length = int(calculated_minutes * 60)
            print(f"Input text: {len(text_content)} characters, {word_count} words")
            print(f"Auto-calculated length: {calculated_minutes:.1f} minutes ({self.args.length} seconds) @ 150 words/min")
        else:
            word_count = len(text_content.split())
            print(f"Input text: {len(text_content)} characters, {word_count} words")
            print(f"Target length: ~{self.args.length} seconds ({self.args.length/60:.1f} minutes)")
        print()

        # Determine if using local Ollama or OpenRouter
        scene_model = getattr(self.args, 'scene_model', 'anthropic/claude-sonnet-4.5')
        is_local_ollama = scene_model in ['dolphin-mistral', 'qwen2.5:32b', 'qwen2.5:14b', 'llama3', 'mistral']

        if is_local_ollama:
            print(f"Initializing local Ollama model: {scene_model}")
            from ollama_client import OllamaClient
            ollama_client = OllamaClient(model=scene_model)
            generator = SceneGenerator(
                client=ollama_client,
                model=scene_model,
                output_dir=self.output_dir  # Save intermediate chunks
            )
        else:
            print(f"Initializing OpenRouter model: {scene_model}")
            generator = SceneGenerator(model=scene_model)

        # Determine art style description
        if self.args.art_style:
            art_style = self.args.art_style
        else:
            art_style = "Watercolor storybook illustration with warm tones, visible brushstrokes, soft lighting"

        # Generate scenes
        model_name = "Ollama" if is_local_ollama else "OpenRouter"
        print(f"Generating scenes with {model_name} ({scene_model})...")
        scenes_data = generator.generate_scenes_from_text(
            text=text_content,
            target_length_minutes=self.args.length / 60.0,
            art_style=art_style,
            narrator_style=self.args.narration_style
        )

        # Save intermediate creative narrative if available (two-step mode)
        if hasattr(generator, '_last_creative_narrative'):
            narrative_file = self.output_dir / 'creative_narrative.txt'
            with open(narrative_file, 'w') as f:
                f.write(generator._last_creative_narrative)
            print(f"Creative narrative saved: {narrative_file}")

        print(f"✓ Generated {len(scenes_data['scenes'])} scenes")
        print()

        return scenes_data

    def load_scenes(self):
        """Load existing scenes from file."""
        print("─" * 80)
        print("STAGE 1: Loading Scenes")
        print("─" * 80)

        with open(self.args.scenes, 'r') as f:
            scenes_data = json.load(f)

        print(f"✓ Loaded {len(scenes_data['scenes'])} scenes from {self.args.scenes}")
        print()

        return scenes_data

    def trim_to_test_mode(self, scenes_data):
        """Trim scenes to first 3 for test mode and save to separate file."""
        print("─" * 80)
        print("STAGE 2: Test Mode Trimming")
        print("─" * 80)

        original_count = len(scenes_data['scenes'])

        # Create a deep copy and trim scenes
        import copy
        trimmed_data = copy.deepcopy(scenes_data)
        trimmed_data['scenes'] = trimmed_data['scenes'][:3]

        # Save trimmed version to scenes_short.json
        short_scenes_file = self.output_dir / 'scenes_short.json'
        with open(short_scenes_file, 'w') as f:
            json.dump(trimmed_data, f, indent=2)

        print(f"Trimmed from {original_count} scenes to {len(trimmed_data['scenes'])} scenes")
        print(f"Trimmed scenes saved: {short_scenes_file}")
        print()

        return trimmed_data

    def save_scenes(self, scenes_data):
        """Save scenes to file."""
        with open(self.scenes_file, 'w') as f:
            json.dump(scenes_data, f, indent=2)

        print(f"Scenes saved: {self.scenes_file}")
        print()

    def generate_audio(self, scenes_data):
        """Generate audio for all scenes."""
        print("─" * 80)
        print("STAGE 3: Audio Generation")
        print("─" * 80)

        from audio_generator import ParallelAudioGenerator

        audio_dir = self.output_dir / 'audio'

        print(f"Generating audio with Chatterbox...")
        print(f"  Reference: {self.args.audio_reference}")
        print(f"  Workers: {self.args.audio_workers}")
        print()

        # Initialize audio generator
        generator = ParallelAudioGenerator(
            audio_prompt_path=self.args.audio_reference,
            device='cpu',  # TODO: Add --device parameter if GPU support needed
            speed=1.0,
            max_workers=self.args.audio_workers
        )

        # Generate audio for all scenes
        durations = generator.generate_all_scenes(
            scenes=scenes_data['scenes'],
            audio_dir=audio_dir,
            checkpoint_mgr=None  # TODO: Add checkpoint support
        )

        # Update scenes with actual durations
        for scene in scenes_data['scenes']:
            scene_id = scene['scene_id']
            if scene_id in durations:
                scene['actual_duration'] = durations[scene_id]

        print(f"✓ Generated audio for {len(durations)} scenes")
        print()

    def generate_images(self, scenes_data):
        """Generate styled images for all scenes."""
        print("─" * 80)
        print("STAGE 4: Image Generation")
        print("─" * 80)

        from openai_responses_image_client import OpenAIResponsesImageClient
        import subprocess

        client = OpenAIResponsesImageClient()
        images_dir = self.output_dir / 'images'

        # Map quality to model
        quality_model_map = {
            'low': 'gpt-4o-mini',
            'medium': 'gpt-4o',
            'high': 'gpt-4o'
        }
        model = quality_model_map.get(self.args.image_quality, 'gpt-4o')

        print(f"Generating images with GPT-Image-1.5...")
        print(f"  Model: {model}")
        print(f"  Reference: {self.args.art_reference}")
        print(f"  Scenes: {len(scenes_data['scenes'])}")
        print()

        # Get consistent objects from episode
        episode_objects = scenes_data.get('episode', {}).get('consistent_objects', {})
        if episode_objects:
            print(f"  Consistent objects: {', '.join(episode_objects.keys())}")
            print()

        # Helper function for parallel image generation
        def generate_single_image(scene_data):
            scene, idx = scene_data
            scene_id = f"scene_{scene['scene_id']:03d}"
            image_path_temp = images_dir / f"{scene_id}_temp.png"
            image_path_final = images_dir / f"{scene_id}.png"

            # Skip if image already exists (either temp or final)
            if image_path_temp.exists() or image_path_final.exists():
                print(f"  [{idx}/{len(scenes_data['scenes'])}] {scene_id}... ⏭️  (already exists)")
                return None

            print(f"  [{idx}/{len(scenes_data['scenes'])}] {scene_id}...", end=' ', flush=True)

            try:
                # Get scene-specific consistent objects
                scene_object_ids = scene.get('consistent_objects', [])
                scene_objects = {obj_id: episode_objects[obj_id]
                                for obj_id in scene_object_ids
                                if obj_id in episode_objects}

                # Generate image with style reference
                b64_data = client.generate_with_style_reference(
                    prompt=scene['video_description'],
                    style_reference_path=str(self.args.art_reference),
                    model=model,
                    size="1536x1024",  # Closest to 16:9, will resize
                    consistent_objects=scene_objects
                )

                # Save temporary image
                temp_path = images_dir / f"{scene_id}_temp.png"
                final_path = images_dir / f"{scene_id}.png"

                client.save_base64_image(b64_data, str(temp_path))

                # Resize to exact 1280x720 for Sora
                subprocess.run([
                    "sips", "-z", "720", "1280",
                    str(temp_path), "--out", str(final_path)
                ], check=True, capture_output=True)

                # Remove temp file
                temp_path.unlink()

                print(f"✓")
                return scene_id

            except Exception as e:
                print(f"✗ Error: {e}")
                raise

        # Parallel image generation with 10 workers
        scenes_with_index = [(scene, i) for i, scene in enumerate(scenes_data['scenes'], 1)]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(generate_single_image, scenes_with_index))

        print()
        generated_count = sum(1 for r in results if r is not None)
        print(f"✓ Generated {generated_count} new images ({len(scenes_data['scenes'])} total)")
        print()

    def generate_static_videos(self, scenes_data):
        """Generate static background videos with waveform animation."""
        from video_assembler import VideoAssembler

        video_dir = self.output_dir / 'video'
        audio_dir = self.output_dir / 'audio'

        print(f"Generating static background videos with waveform...")
        print(f"  Background: {self.args.static_background}")
        print(f"  Scenes: {len(scenes_data['scenes'])}")
        print()

        assembler = VideoAssembler()

        for i, scene in enumerate(scenes_data['scenes'], 1):
            scene_id = f"scene_{scene['scene_id']:03d}"
            audio_path = audio_dir / f"{scene_id}.wav"
            video_path = video_dir / f"{scene_id}_static.mp4"

            if not audio_path.exists():
                print(f"  [{i}/{len(scenes_data['scenes'])}] ⚠️  Skipping {scene_id}: audio not found")
                continue

            print(f"  [{i}/{len(scenes_data['scenes'])}] {scene_id}...", end=' ', flush=True)

            try:
                assembler.create_static_video_with_waveform(
                    background_image_path=Path(self.args.static_background),
                    audio_path=audio_path,
                    output_path=video_path
                )
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
                raise

        print()
        print(f"✓ Generated {len(scenes_data['scenes'])} static videos")
        print()

    def generate_slide_videos(self, scenes_data):
        """Generate static slide videos from images with audio."""
        from video_assembler import VideoAssembler

        video_dir = self.output_dir / 'video'
        images_dir = self.output_dir / 'images'
        audio_dir = self.output_dir / 'audio'

        print(f"Generating slide videos from images...")
        print(f"  Scenes: {len(scenes_data['scenes'])}")
        print()

        assembler = VideoAssembler()

        for i, scene in enumerate(scenes_data['scenes'], 1):
            scene_id = f"scene_{scene['scene_id']:03d}"
            image_path = images_dir / f"{scene_id}.png"
            audio_path = audio_dir / f"{scene_id}.wav"
            video_path = video_dir / f"{scene_id}_slides.mp4"

            if not image_path.exists():
                print(f"  [{i}/{len(scenes_data['scenes'])}] ⚠️  Skipping {scene_id}: image not found")
                continue

            if not audio_path.exists():
                print(f"  [{i}/{len(scenes_data['scenes'])}] ⚠️  Skipping {scene_id}: audio not found")
                continue

            print(f"  [{i}/{len(scenes_data['scenes'])}] {scene_id}...", end=' ', flush=True)

            try:
                assembler.create_slide_video(
                    image_path=image_path,
                    audio_path=audio_path,
                    output_path=video_path
                )
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
                raise

        print()
        print(f"✓ Generated {len(scenes_data['scenes'])} slide videos")
        print()

    def generate_videos(self, scenes_data):
        """Generate videos for all scenes - routes to appropriate mode."""
        print("─" * 80)
        print("STAGE 5: Video Generation")
        print("─" * 80)

        # Route to appropriate method based on mode
        if self.args.mode == 'static':
            self.generate_static_videos(scenes_data)
        elif self.args.mode == 'slides':
            self.generate_slide_videos(scenes_data)
        elif self.args.mode == 'video':
            self.generate_sora_videos(scenes_data)

    def generate_sora_videos(self, scenes_data):
        """Generate full motion videos with Sora."""
        import asyncio
        from openai_client import OpenAIClient
        from video_generator import ParallelVideoGenerator
        from video_assembler import VideoAssembler

        video_dir = self.output_dir / 'video'
        images_dir = self.output_dir / 'images'

        print(f"Generating videos with Sora...")
        print(f"  Mode: {self.args.mode}")
        print(f"  Quality: {self.args.video_quality}")
        print()

        # Initialize clients
        openai_client = OpenAIClient()
        video_generator = ParallelVideoGenerator(
            openai_client=openai_client,
            model='sora-2',
            max_concurrent=3  # Conservative rate limit
        )
        assembler = VideoAssembler()

        # Get episode context and consistent objects
        episode_context = scenes_data['episode']['context']
        art_style = scenes_data['episode']['art_style']
        episode_objects = scenes_data.get('episode', {}).get('consistent_objects', {})

        if episode_objects:
            print(f"  Consistent objects: {', '.join(episode_objects.keys())}")
            print()

        # For each scene, we need to use the generated image as input_reference
        # The video generator will handle this internally
        # First, update scenes with reference image paths
        for scene in scenes_data['scenes']:
            scene_id = f"scene_{scene['scene_id']:03d}"
            image_path = images_dir / f"{scene_id}.png"
            if image_path.exists():
                scene['input_reference'] = str(image_path)

        # Run async video generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            video_paths = loop.run_until_complete(
                video_generator.generate_all_scenes(
                    scenes=scenes_data['scenes'],
                    episode_context=episode_context,
                    art_style=art_style,
                    video_dir=video_dir,
                    assembler=assembler,
                    checkpoint_mgr=None,
                    episode_objects=episode_objects
                )
            )
            print(f"✓ Generated {len(video_paths)} videos")
            print()
        finally:
            loop.close()

    def assemble_final_video(self, scenes_data):
        """Assemble final video from scenes."""
        print("─" * 80)
        print("STAGE 6: Assembly")
        print("─" * 80)

        from video_assembler import VideoAssembler

        assembler = VideoAssembler()
        video_dir = self.output_dir / 'video'
        audio_dir = self.output_dir / 'audio'

        print(f"Assembling final video...")
        print()

        # Merge audio and video for each scene
        scene_videos_with_audio = []

        for scene in scenes_data['scenes']:
            scene_id = f"scene_{scene['scene_id']:03d}"

            # Find video file - try mode-specific naming first, then legacy
            audio_path = audio_dir / f"{scene_id}.wav"
            mode_suffix = self.args.mode  # 'static', 'slides', or 'video'
            output_path = video_dir / f"{scene_id}_with_audio.mp4"

            # Try to find existing video in order of preference
            video_path = None
            for candidate in [
                video_dir / f"{scene_id}_{mode_suffix}.mp4",  # Mode-specific naming
                video_dir / f"{scene_id}_video.mp4",          # Video mode
                video_dir / f"{scene_id}_final.mp4",          # Legacy naming
                video_dir / f"{scene_id}_trimmed.mp4",        # Legacy static naming
                video_dir / f"{scene_id}.mp4"                 # Basic naming
            ]:
                if candidate.exists():
                    video_path = candidate
                    break

            if video_path and audio_path.exists():
                print(f"  Merging {scene_id}...", end=' ', flush=True)
                assembler.add_audio_to_video(video_path, audio_path, output_path)
                scene_videos_with_audio.append(output_path)
                print("✓")
            else:
                print(f"  ⚠️  Missing files for {scene_id}")
                if not video_path or not video_path.exists():
                    print(f"      Missing video (tried multiple naming conventions)")
                if not audio_path.exists():
                    print(f"      Missing audio: {audio_path}")

        # Concatenate all scenes
        if scene_videos_with_audio:
            mode_suffix = self.args.mode  # 'static', 'slides', or 'video'
            final_output = self.output_dir / f"{scenes_data['episode']['title'].replace(' ', '_')}_{mode_suffix}.mp4"
            print(f"\n  Concatenating {len(scene_videos_with_audio)} scenes...")
            assembler.concatenate_videos(scene_videos_with_audio, final_output)
            print(f"  ✓ Final video: {final_output.name}")
        else:
            print("  ✗ No scene videos to assemble")

        print()

    def generate_report(self, scenes_data, start_time):
        """Generate scene report."""
        end_time = datetime.now()
        duration = end_time - start_time

        report_file = self.output_dir / 'scene_report.txt'

        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("VIDEO GENERATION REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {duration}\n\n")

            f.write(f"Episode: {scenes_data['episode']['title']}\n")
            f.write(f"Total Scenes: {len(scenes_data['scenes'])}\n\n")

            f.write("Scenes:\n")
            f.write("-" * 80 + "\n")
            for scene in scenes_data['scenes']:
                f.write(f"\n{scene['scene_id']}:\n")
                f.write(f"  Duration: {scene.get('expected_duration', 'N/A')}s\n")
                f.write(f"  Description: {scene['video_description'][:80]}...\n")

        print(f"Report saved: {report_file}")
        print()
