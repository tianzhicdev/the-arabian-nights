#!/usr/bin/env python3
"""
Video generation using OpenAI Sora with scene-based approach.
Optimized for video content with multiple camera angles.
"""

import argparse
import json
import os
import sys
import time
import whisper
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env.secrets
env_path = Path(__file__).parent.parent / '.env.secrets'
if env_path.exists():
    load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.clients.openai_client import OpenAIClient
from src.clients.openrouter_client import OpenRouterClient


class VideoSceneDetector:
    """Detect video scenes with action-oriented prompts and multiple angles."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    def detect_video_scenes(
        self,
        transcript: str,
        book_context: str,
        theme: str,
        angles_per_scene: int = 1
    ) -> List[Dict]:
        """
        Analyze transcript and identify distinct VIDEO scenes with camera angles.

        Args:
            transcript: Full audio transcript
            book_context: Book context (title, setting, themes)
            theme: Visual style/theme for videos
            angles_per_scene: Number of camera angles per scene (start with 1)

        Returns:
            List of scene dicts with angles
        """
        system_prompt = f"""You are a cinematic director analyzing a narrative for VIDEO adaptation.

BOOK CONTEXT:
{book_context}

VISUAL STYLE/THEME:
{theme}

Your task: Identify distinct VIDEO SCENES that focus on ACTION and MOVEMENT.

Key Requirements:
1. Each scene must have ACTION, not static descriptions
2. Each angle must be exactly 4, 8, or 12 seconds
3. Focus on cinematic potential: camera movements, character actions, environmental changes
4. Scenes should flow naturally and maintain visual continuity
5. {"Generate " + str(angles_per_scene) + " camera angle(s) per scene" if angles_per_scene > 1 else "Generate 1 camera angle per scene"}

Output JSON format:
[
  {{
    "scene_id": 1,
    "text": "Exact transcript text for this scene",
    "total_duration": 8,
    "angles": [
      {{
        "angle_id": 1,
        "duration": 8,
        "shot_type": "wide establishing shot / close-up / tracking / etc",
        "action": "Brief description of ACTION and MOVEMENT to show",
        "camera_movement": "static / pan / tilt / dolly / tracking / handheld / etc"
      }}
    ]
  }}
]

IMPORTANT:
- Duration must be 4, 8, or 12 (no other values)
- Focus on visual ACTION that can be shown in video
- total_duration = sum of all angle durations"""

        user_prompt = f"""Analyze this transcript and create cinematic video scenes:

TRANSCRIPT:
{transcript}

Generate video scenes with ACTION-oriented angles suitable for {theme} style."""

        try:
            response = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            content = response['content'].strip()

            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            scenes = json.loads(content)

            print(f"Detected {len(scenes)} video scenes")
            for scene in scenes:
                total_dur = scene.get('total_duration', 0)
                num_angles = len(scene.get('angles', []))
                print(f"  Scene {scene['scene_id']}: {total_dur}s ({num_angles} angles)")

            return scenes

        except Exception as e:
            raise Exception(f"Video scene detection failed: {str(e)}")


class VideoTimingAnalyzer:
    """Map video scenes to exact audio timestamps."""

    def __init__(self, whisper_model: str = "base"):
        print(f"Loading Whisper model: {whisper_model}...")
        self.model = whisper.load_model(whisper_model)

    def analyze(
        self,
        audio_path: str,
        scenes: List[Dict]
    ) -> List[Dict]:
        """
        Map scenes to word-level timestamps with exact audio matching.

        Args:
            audio_path: Path to audio file
            scenes: List of detected video scenes

        Returns:
            List of timing segments with scene and angle data
        """
        print(f"Transcribing audio: {audio_path}")
        result = self.model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )

        # Extract all words with timestamps
        all_words = []
        for seg in result['segments']:
            all_words.extend(seg.get('words', []))

        print(f"Mapping {len(scenes)} scenes to timestamps...")

        segments = self._map_scenes_to_timestamps(scenes, all_words)

        print(f"Created {len(segments)} timing segments")
        return segments

    def _map_scenes_to_timestamps(
        self,
        scenes: List[Dict],
        all_words: List[Dict]
    ) -> List[Dict]:
        """Map each scene to word-level timestamps."""
        segments = []
        current_word_idx = 0

        for scene in scenes:
            scene_text = scene['text'].strip()
            scene_words_count = len(scene_text.split())

            # Find word boundaries for this scene
            start_word_idx = current_word_idx
            end_word_idx = min(current_word_idx + scene_words_count, len(all_words))

            if start_word_idx >= len(all_words):
                break

            start_time = all_words[start_word_idx]['start']
            end_time = all_words[end_word_idx - 1]['end']
            duration = end_time - start_time

            # Create segment for this scene
            segment = {
                'segment_id': len(segments) + 1,
                'scene_id': scene['scene_id'],
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'text': scene_text,
                'angles': scene['angles'],
                'words': all_words[start_word_idx:end_word_idx]
            }

            segments.append(segment)
            current_word_idx = end_word_idx

        return segments


class VideoPromptGenerator:
    """Generate cinematic video prompts for Sora."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    def generate_prompts(
        self,
        segments: List[Dict],
        book_context: str,
        theme: str
    ) -> List[Dict]:
        """
        Generate detailed video prompts for each camera angle.

        Args:
            segments: List of timing segments with angles
            book_context: Book context information
            theme: Visual style/theme

        Returns:
            Segments with video_prompt added to each angle
        """
        print(f"Generating video prompts...")
        print(f"Book Context: {book_context}")
        print(f"Theme: {theme}")

        for i, segment in enumerate(segments, 1):
            for angle in segment['angles']:
                print(f"  Generating prompt {i}/{len(segments)} - Angle {angle['angle_id']}...", end="", flush=True)

                prompt = self._generate_angle_prompt(
                    segment,
                    angle,
                    book_context,
                    theme
                )

                angle['video_prompt'] = prompt
                print(" ✓")

        print(f"Generated {len(segments)} video prompts")
        return segments

    def _generate_angle_prompt(
        self,
        segment: Dict,
        angle: Dict,
        book_context: str,
        theme: str
    ) -> str:
        """Generate detailed prompt for a specific camera angle."""

        system_prompt = f"""You are a professional cinematographer creating detailed video prompts for AI video generation.

BOOK CONTEXT: {book_context}
VISUAL STYLE: {theme}

Your task: Create a highly detailed, cinematic video prompt that captures the action and movement for this specific camera angle.

Requirements:
- Describe the ACTION and MOVEMENT in detail
- Specify camera work clearly
- Maintain consistent visual style ({theme})
- Focus on what will be SHOWN visually
- Duration: {angle['duration']} seconds
- Keep prompt under 200 words but be vivid and specific"""

        user_prompt = f"""Create a detailed {angle['duration']}-second video prompt for this angle:

SCENE TEXT: {segment['text']}

THIS CAMERA ANGLE:
- Shot Type: {angle['shot_type']}
- Action to Show: {angle['action']}
- Camera Movement: {angle['camera_movement']}
- Duration: {angle['duration']} seconds

Generate a cinematic video prompt that Sora can use to create this shot."""

        try:
            response = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            prompt = response['content'].strip()

            # Remove any quotes or markdown
            prompt = prompt.replace('"', '').replace('*', '')
            if prompt.startswith('Video Prompt:'):
                prompt = prompt[len('Video Prompt:'):].strip()

            return prompt

        except Exception as e:
            # Fallback to simple prompt
            return f"{angle['shot_type']}: {angle['action']}. Camera: {angle['camera_movement']}. {theme} style. {angle['duration']} seconds."


class VideoAssembler:
    """Assemble video clips into final video with audio."""

    def assemble_final_video(
        self,
        segments: List[Dict],
        audio_path: str,
        output_path: Path
    ) -> str:
        """
        Concatenate video clips and add original audio.

        Args:
            segments: List of segments with video_path for each angle
            audio_path: Path to original audio file
            output_path: Output path for final video

        Returns:
            Path to final video file
        """
        import subprocess
        import tempfile

        print("Assembling final video...")

        # Collect all video clips in order
        video_clips = []
        for seg in segments:
            for angle in seg.get('angles', []):
                video_path = angle.get('video_path')
                if video_path and Path(video_path).exists():
                    video_clips.append(video_path)

        if not video_clips:
            raise Exception("No video clips found to assemble")

        print(f"  Found {len(video_clips)} video clips")

        # Create temporary file list for ffmpeg concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for clip in video_clips:
                # ffmpeg concat requires absolute paths and 'file' prefix
                f.write(f"file '{Path(clip).absolute()}'\n")

        try:
            # Use ffmpeg to:
            # 1. Concatenate videos using concat demuxer
            # 2. Strip video audio (-an for concat input)
            # 3. Add original audio file
            # 4. Copy video codec (no re-encoding) and encode audio
            final_video = str(output_path)

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,        # Video clips (concatenated)
                '-i', audio_path,          # Original audio
                '-map', '0:v',             # Use video from first input (concatenated clips)
                '-map', '1:a',             # Use audio from second input (original audio)
                '-c:v', 'copy',            # Copy video codec (no re-encoding)
                '-c:a', 'aac',             # Encode audio as AAC
                '-shortest',               # End when shortest stream ends
                '-y',                      # Overwrite output
                final_video
            ]

            print(f"  Running ffmpeg...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr}")

            print(f"  ✓ Final video saved: {output_path.name}")
            return final_video

        finally:
            # Clean up temp file
            Path(concat_file).unlink(missing_ok=True)


class SoraVideoGenerator:
    """Generate videos using OpenAI Sora API."""

    def __init__(self, openai_client: OpenAIClient, model: str = "sora-2"):
        self.client = openai_client
        self.model = model
        print(f"Using Sora model: {model}")

    def generate_videos(
        self,
        segments: List[Dict],
        output_dir: Path,
        reference_image: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate video for each camera angle.

        Args:
            segments: List of segments with angle prompts
            output_dir: Directory to save videos
            reference_image: Optional reference image for style consistency

        Returns:
            Segments with video_path added to angles
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Count total angles
        total_angles = sum(len(seg['angles']) for seg in segments)
        current = 0

        print(f"Generating {total_angles} video clips...")
        print(f"Output directory: {output_dir}")

        for segment in segments:
            for angle in segment['angles']:
                current += 1
                print(f"\n  Video {current}/{total_angles}:")
                print(f"    Scene {segment['scene_id']}, Angle {angle['angle_id']}")
                print(f"    Duration: {angle['duration']}s")
                print(f"    Prompt: {angle['video_prompt'][:80]}...")

                video_path = output_dir / f"scene_{segment['scene_id']:03d}_angle_{angle['angle_id']}_{angle['duration']}s.mp4"

                try:
                    # Generate video using Sora
                    video_url = self.client.generate_video(
                        prompt=angle['video_prompt'],
                        model=self.model,
                        seconds=angle['duration'],
                        size="1280x720",
                        input_reference=reference_image
                    )

                    # Download video from /content endpoint (requires authorization)
                    print(f"    Downloading video...")
                    import requests
                    headers = {
                        "Authorization": f"Bearer {self.client.api_key}"
                    }
                    response = requests.get(video_url, headers=headers, timeout=300)
                    response.raise_for_status()

                    with open(video_path, 'wb') as f:
                        f.write(response.content)

                    angle['video_path'] = str(video_path)
                    print(f"    ✓ Saved: {video_path.name}")

                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    # Create placeholder
                    angle['video_path'] = None
                    angle['error'] = str(e)

                # Rate limiting
                time.sleep(1)

        print(f"\nGenerated {total_angles} video clips")
        return segments


def main():
    parser = argparse.ArgumentParser(description="Generate video using Sora")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--theme", default="cinematic film noir", help="Visual theme/style")
    parser.add_argument("--book-context", help="Book context (optional)")
    parser.add_argument("--reference-image", help="Reference image for style consistency")
    parser.add_argument("--model", default="sora-2", choices=["sora-2", "sora-2-pro"], help="Sora model")
    parser.add_argument("--angles-per-scene", type=int, default=1, help="Camera angles per scene")
    parser.add_argument("--output-dir", default="output/video", help="Output directory")
    parser.add_argument("--whisper-model", default="base", help="Whisper model")

    args = parser.parse_args()

    print("=" * 80)
    print("SORA VIDEO GENERATOR")
    print("=" * 80)
    print(f"Audio:      {args.audio}")
    print(f"Theme:      {args.theme}")
    print(f"Model:      {args.model}")
    print(f"Angles:     {args.angles_per_scene} per scene")
    print(f"Output:     {args.output_dir}")
    print("=" * 80)
    print()

    # Initialize clients
    openai_client = OpenAIClient()
    openrouter_client = OpenRouterClient()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 0: Context Preparation
    print("Stage 0: Context Preparation")
    print("-" * 80)

    if args.book_context:
        book_context = args.book_context
    else:
        # Generate from audio/filename
        book_context = "Story narration (context not provided)"
        # TODO: Could generate summary here

    print(f"Book Context: {book_context}")

    # Save context
    context_file = output_dir / 'book_context.txt'
    with open(context_file, 'w') as f:
        f.write(book_context)
    print()

    # Stage 1: Quick transcription for scene detection
    print("Stage 1: Scene Detection")
    print("-" * 80)
    print("Loading Whisper for quick transcript...")
    temp_whisper = whisper.load_model(args.whisper_model)
    quick_result = temp_whisper.transcribe(str(args.audio), language="en")
    full_transcript = ' '.join([seg['text'].strip() for seg in quick_result['segments']])

    # Detect video scenes
    scene_detector = VideoSceneDetector(openrouter_client)
    scenes = scene_detector.detect_video_scenes(
        full_transcript,
        book_context,
        args.theme,
        angles_per_scene=args.angles_per_scene
    )

    # Save scenes
    scenes_file = output_dir / 'detected_video_scenes.json'
    with open(scenes_file, 'w') as f:
        json.dump(scenes, f, indent=2)
    print(f"Saved scenes: {scenes_file}")
    print()

    # Stage 2: Timing analysis
    print("Stage 2: Video Timing Analysis")
    print("-" * 80)
    analyzer = VideoTimingAnalyzer(whisper_model=args.whisper_model)
    segments = analyzer.analyze(str(args.audio), scenes)

    # Save timing
    timing_file = output_dir / 'video_timing_segments.json'
    with open(timing_file, 'w') as f:
        json.dump(segments, f, indent=2)
    print(f"Saved timing: {timing_file}")
    print()

    # Stage 3: Prompt generation
    print("Stage 3: Video Prompt Generation")
    print("-" * 80)
    prompt_generator = VideoPromptGenerator(openrouter_client)
    segments = prompt_generator.generate_prompts(segments, book_context, args.theme)

    # Save prompts
    prompts_file = output_dir / 'video_prompts.json'
    with open(prompts_file, 'w') as f:
        json.dump(segments, f, indent=2)
    print(f"Saved prompts: {prompts_file}")
    print()

    # Stage 4: Video generation
    print("Stage 4: Sora Video Generation")
    print("-" * 80)
    video_generator = SoraVideoGenerator(openai_client, model=args.model)
    videos_dir = output_dir / 'videos'
    segments = video_generator.generate_videos(
        segments,
        videos_dir,
        reference_image=args.reference_image
    )

    # Save final data
    final_file = output_dir / 'video_segments_final.json'
    with open(final_file, 'w') as f:
        json.dump(segments, f, indent=2)
    print(f"\nSaved final data: {final_file}")

    # Stage 5: Video Assembly
    print("\nStage 5: Video Assembly")
    print("-" * 80)
    assembler = VideoAssembler()
    final_video_path = output_dir / 'final_video.mp4'
    final_video = assembler.assemble_final_video(
        segments,
        str(args.audio),
        final_video_path
    )
    print()

    print("=" * 80)
    print("SUCCESS! Final video created")
    print("=" * 80)
    print(f"Scenes:       {scenes_file}")
    print(f"Timing:       {timing_file}")
    print(f"Prompts:      {prompts_file}")
    print(f"Video clips:  {videos_dir}")
    print(f"Final video:  {final_video}")
    print("=" * 80)


if __name__ == "__main__":
    main()
