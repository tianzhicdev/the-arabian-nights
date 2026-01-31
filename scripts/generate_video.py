#!/usr/bin/env python3
"""
Video Generator: Create YouTube videos from podcast audio with AI-generated images.

Usage:
    python3 scripts/generate_video.py \
        --audio audio_output/episode/short.wav \
        --theme "colored chalk drawing with a dark theme"
"""

import argparse
import json
import os
import sys
import base64
import time
from pathlib import Path
from typing import List, Dict, Optional
import re

# Import required libraries
try:
    import whisper
    from pydub import AudioSegment
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    from PIL import Image
    import requests
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    print("Install with: pip install openai-whisper pydub moviepy pillow requests")
    sys.exit(1)

from openrouter_client import OpenRouterClient
from openai_client import OpenAIClient


class SceneDetector:
    """Detect visual scenes using LLM analysis of transcript."""

    def __init__(self, client: OpenRouterClient):
        """
        Initialize scene detector.

        Args:
            client: OpenRouter client for LLM calls
        """
        self.client = client

    def detect_scenes(
        self,
        transcript: str,
        min_duration: float = 3.0,
        max_duration: float = 30.0
    ) -> List[Dict]:
        """
        Analyze transcript and identify distinct visual scenes.

        Args:
            transcript: Full text transcript
            min_duration: Minimum scene duration (for validation)
            max_duration: Maximum scene duration (for splitting hints)

        Returns:
            List of scene dicts with visual_concept and text
        """
        print(f"Analyzing transcript for visual scenes...")

        system_prompt = """You are an expert at analyzing narratives and identifying distinct visual scenes for illustration.

A "visual scene" is a coherent visual concept that deserves a single illustration. Multiple sentences describing the same scene, person, or location should be grouped together.

Rules:
1. Group consecutive sentences that describe the same visual concept
2. A scene change occurs when: location changes, new character introduced, or visual focus shifts
3. Each scene should be 1-5 sentences
4. Prefer natural narrative breaks (paragraphs, pauses in action)
5. Scenes describing the same thing (e.g., "a poster" across multiple sentences) should be ONE scene

Output a JSON array of scenes:
[
  {
    "scene_id": 1,
    "visual_concept": "Brief description of what should be illustrated",
    "text": "The exact text from the transcript for this scene"
  },
  ...
]"""

        user_prompt = f"""Analyze this transcript and identify distinct visual scenes:

{transcript}

Identify visual scenes following the rules. Output JSON only."""

        try:
            response = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent scene detection
                max_tokens=2000
            )

            content = response['content'].strip()

            # Extract JSON from response (handle markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            scenes = json.loads(content)
            print(f"Detected {len(scenes)} visual scenes")

            return scenes

        except Exception as e:
            print(f"Error detecting scenes: {e}")
            # Fallback: treat entire transcript as one scene
            return [{
                "scene_id": 1,
                "visual_concept": "Full narrative",
                "text": transcript
            }]


class AudioAnalyzer:
    """Transcribe audio and extract word-level timestamps."""

    def __init__(self, whisper_model: str = "base"):
        """
        Initialize audio analyzer.

        Args:
            whisper_model: Whisper model size (tiny/base/small/medium/large)
        """
        self.whisper_model = whisper_model
        print(f"Loading Whisper model: {whisper_model}...")
        self.model = whisper.load_model(whisper_model)

    def analyze(
        self,
        audio_path: str,
        scenes: List[Dict],
        min_duration: float = 3.0,
        max_duration: float = 30.0
    ) -> List[Dict]:
        """
        Transcribe audio and map scenes to timestamps.

        Args:
            audio_path: Path to audio file
            scenes: List of scene dicts from SceneDetector
            min_duration: Minimum seconds per scene
            max_duration: Maximum seconds per scene

        Returns:
            List of segment dicts with start, end, duration, text, scene info
        """
        print(f"Transcribing audio: {audio_path}")

        # Transcribe with word timestamps
        result = self.model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )

        print(f"Transcription complete. Mapping {len(scenes)} scenes to timestamps...")

        # Get total audio duration
        audio = AudioSegment.from_wav(audio_path)
        total_duration = len(audio) / 1000.0  # Convert ms to seconds

        # Extract ALL words with timestamps
        all_words = []
        for seg in result['segments']:
            all_words.extend(seg.get('words', []))

        # Get full transcript
        full_transcript = ' '.join([seg['text'].strip() for seg in result['segments']])

        # Map scenes to word-level timestamps
        segments = self._map_scenes_to_timestamps(
            scenes, all_words, full_transcript, min_duration, max_duration, total_duration
        )

        print(f"Created {len(segments)} segments from {len(scenes)} scenes")
        return segments

    def _map_scenes_to_timestamps(
        self,
        scenes: List[Dict],
        all_words: List[Dict],
        full_transcript: str,
        min_duration: float,
        max_duration: float,
        total_duration: float
    ) -> List[Dict]:
        """
        Map scene text to word-level timestamps.

        Args:
            scenes: Scene descriptions from LLM
            all_words: All words with timestamps from Whisper
            full_transcript: Full transcript text
            min_duration: Minimum scene duration
            max_duration: Maximum scene duration
            total_duration: Total audio duration

        Returns:
            List of segments with timing information
        """
        segments = []
        current_word_idx = 0

        for scene in scenes:
            scene_text = scene['text'].strip()

            # Find scene text in transcript (approximate matching)
            # Count words in scene
            scene_words = scene_text.split()
            num_words = len(scene_words)

            if current_word_idx >= len(all_words):
                break

            # Map to words
            start_word_idx = current_word_idx
            end_word_idx = min(current_word_idx + num_words, len(all_words))

            if start_word_idx < len(all_words) and end_word_idx <= len(all_words):
                start_time = all_words[start_word_idx]['start']
                end_time = all_words[end_word_idx - 1]['end'] if end_word_idx > 0 else all_words[start_word_idx]['end']

                # Handle pauses - extend to next word's start if gap is small
                if end_word_idx < len(all_words):
                    gap = all_words[end_word_idx]['start'] - end_time
                    if gap < 2.0:  # Less than 2 second pause
                        end_time = all_words[end_word_idx]['start']

                duration = end_time - start_time

                # Apply duration constraints
                if duration < min_duration and end_word_idx < len(all_words):
                    # Extend to meet minimum
                    while duration < min_duration and end_word_idx < len(all_words):
                        end_word_idx += 1
                        end_time = all_words[end_word_idx - 1]['end']
                        duration = end_time - start_time

                if duration > max_duration:
                    # Split scene if too long
                    mid_idx = start_word_idx + (end_word_idx - start_word_idx) // 2
                    mid_time = all_words[mid_idx]['start']

                    # First half
                    segments.append({
                        'segment_id': len(segments) + 1,
                        'start': start_time,
                        'end': mid_time,
                        'duration': mid_time - start_time,
                        'text': ' '.join([w['word'] for w in all_words[start_word_idx:mid_idx]]),
                        'scene_id': scene['scene_id'],
                        'visual_concept': scene['visual_concept'],
                        'words': all_words[start_word_idx:mid_idx]
                    })

                    # Second half
                    segments.append({
                        'segment_id': len(segments) + 1,
                        'start': mid_time,
                        'end': end_time,
                        'duration': end_time - mid_time,
                        'text': ' '.join([w['word'] for w in all_words[mid_idx:end_word_idx]]),
                        'scene_id': scene['scene_id'],
                        'visual_concept': scene['visual_concept'],
                        'words': all_words[mid_idx:end_word_idx]
                    })
                else:
                    # Normal segment
                    segments.append({
                        'segment_id': len(segments) + 1,
                        'start': start_time,
                        'end': end_time,
                        'duration': duration,
                        'text': scene_text,
                        'scene_id': scene['scene_id'],
                        'visual_concept': scene['visual_concept'],
                        'words': all_words[start_word_idx:end_word_idx]
                    })

                current_word_idx = end_word_idx

        # Extend last segment to cover full audio
        if segments and segments[-1]['end'] < total_duration:
            segments[-1]['end'] = total_duration
            segments[-1]['duration'] = total_duration - segments[-1]['start']

        return segments


class PromptGenerator:
    """Generate visual prompts from transcribed text."""

    def __init__(self, client: OpenRouterClient):
        """
        Initialize prompt generator.

        Args:
            client: OpenRouter client for LLM calls
        """
        self.client = client

    def generate_prompts(
        self,
        segments: List[Dict],
        theme: str
    ) -> List[Dict]:
        """
        Generate image prompts for each segment.

        Args:
            segments: List of transcribed segments
            theme: Visual theme/style

        Returns:
            Segments with added 'image_prompt' field
        """
        print(f"Generating image prompts for {len(segments)} segments...")
        print(f"Theme: {theme}")

        system_prompt = """You are an expert at creating visual descriptions for story illustrations.
Your task is to convert narrative text into detailed visual scene descriptions.
Focus on key visual elements, atmosphere, and mood.
Avoid including text or words in the image description.
Keep descriptions concise but vivid (2-3 sentences)."""

        # Group segments by scene_id to generate one image per scene
        scenes_to_process = {}
        for seg in segments:
            scene_id = seg.get('scene_id', seg['segment_id'])
            if scene_id not in scenes_to_process:
                scenes_to_process[scene_id] = seg

        for i, (scene_id, seg) in enumerate(scenes_to_process.items(), 1):
            # Use the visual_concept if available (from scene detection)
            visual_concept = seg.get('visual_concept', '')

            if visual_concept:
                # Scene-based prompt generation
                user_prompt = f"""Create a detailed image prompt for this visual scene.

Visual Concept: {visual_concept}
Narrative Text: "{seg['text']}"

Theme/Style: {theme}

Create a vivid, detailed description focusing on the visual concept.

Requirements:
- Style must match: {theme}
- Landscape aspect ratio (16:9-ish), cinematic composition
- Atmospheric and evocative
- No text or words visible in the image
- Consistent art style

Output only the image generation prompt, no other text."""
            else:
                # Fallback to text-based prompt
                user_prompt = f"""Convert this narrative segment into a detailed visual scene description.

Text: "{seg['text']}"

Theme/Style: {theme}

Requirements:
- Style must match: {theme}
- Landscape aspect ratio, cinematic composition
- Atmospheric and evocative
- Focus on key visual elements from the text
- No text or words visible in the image

Output only the visual description, no other text."""

            print(f"  Generating prompt {i}/{len(scenes_to_process)}... (scene {scene_id})", end=" ")

            try:
                response = self.client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )

                image_prompt = response['content'].strip()

                # Apply this prompt to ALL segments with the same scene_id
                for s in segments:
                    if s.get('scene_id', s['segment_id']) == scene_id:
                        s['image_prompt'] = image_prompt
                        s['image_path'] = None

                print("✓")

            except Exception as e:
                print(f"✗ (Error: {e})")
                # Fallback to simple prompt
                fallback_prompt = f"{visual_concept or seg['text']}. Style: {theme}. Landscape, cinematic."
                for s in segments:
                    if s.get('scene_id', s['segment_id']) == scene_id:
                        s['image_prompt'] = fallback_prompt
                        s['image_path'] = None

        print(f"Generated {len(segments)} image prompts")
        return segments


class ImageGenerator:
    """Generate images using OpenAI DALL-E or OpenRouter."""

    def __init__(self, openai_client: Optional[OpenAIClient] = None, openrouter_client: Optional[OpenRouterClient] = None, model: str = "dall-e-3"):
        """
        Initialize image generator.

        Args:
            openai_client: OpenAI client (preferred if provided)
            openrouter_client: OpenRouter client (fallback)
            model: Image model to use (dall-e-3, dall-e-2, or OpenRouter model)
        """
        self.openai_client = openai_client
        self.openrouter_client = openrouter_client
        self.model = model

        # Determine which client to use
        if openai_client:
            self.use_openai = True
            print(f"Using OpenAI DALL-E for image generation")
        elif openrouter_client:
            self.use_openai = False
            print(f"Using OpenRouter for image generation")
        else:
            raise ValueError("Either openai_client or openrouter_client must be provided")

    def generate_images(
        self,
        segments: List[Dict],
        output_dir: Path,
        resolution: str = "720p"
    ) -> List[Dict]:
        """
        Generate images for unique scenes (one image per scene_id).

        Args:
            segments: List of segments with image_prompt and scene_id
            output_dir: Directory to save images
            resolution: Video resolution (720p or 1080p)

        Returns:
            Segments with updated image_path field
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine image size based on resolution
        if resolution == "1080p":
            width, height = 1920, 1080
        else:  # 720p
            width, height = 1280, 720

        # Group segments by scene_id to generate one image per scene
        scenes_to_generate = {}
        for seg in segments:
            scene_id = seg.get('scene_id', seg['segment_id'])
            if scene_id not in scenes_to_generate:
                scenes_to_generate[scene_id] = seg

        num_scenes = len(scenes_to_generate)
        print(f"Generating {num_scenes} unique scene images at {width}×{height}...")
        print(f"Model: {self.model}")
        print(f"(Will be reused across {len(segments)} segments)")

        # Generate one image per unique scene
        for i, (scene_id, seg) in enumerate(scenes_to_generate.items(), 1):
            print(f"  Scene {scene_id} ({i}/{num_scenes}): ", end="", flush=True)

            image_path = output_dir / f"scene_{scene_id:03d}.png"

            # No caching - always regenerate images
            # if image_path.exists():
            #     print(f"✓ (cached)")
            #     # Apply to all segments with this scene_id
            #     for s in segments:
            #         if s.get('scene_id', s['segment_id']) == scene_id:
            #             s['image_path'] = str(image_path)
            #     continue

            try:
                if self.use_openai:
                    # Use OpenAI DALL-E
                    # Always use landscape aspect ratio for video content
                    size = "1792x1024"  # 16:9-ish landscape (1.75:1)

                    # Generate image
                    image_url = self.openai_client.generate_image(
                        prompt=seg['image_prompt'],
                        model=self.model,
                        size=size,
                        quality="standard"
                    )

                    # Download image from URL
                    import requests
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()

                    with open(image_path, 'wb') as f:
                        f.write(img_response.content)

                else:
                    # Use OpenRouter
                    image_data_url = self.openrouter_client.image_generation(
                        prompt=seg['image_prompt'],
                        model=self.model,
                        width=width,
                        height=height
                    )

                    # Handle base64 data URL
                    if image_data_url.startswith('data:image'):
                        image_data = image_data_url.split(',')[1]
                    else:
                        image_data = image_data_url

                    # Decode and save
                    image_bytes = base64.b64decode(image_data)
                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)

                # Fit to target dimensions using letterboxing (no stretching)
                img = Image.open(image_path)
                if img.size != (width, height):
                    img = self._letterbox_image(img, width, height)
                    img.save(image_path)

                # Apply this image to ALL segments with the same scene_id
                for s in segments:
                    if s.get('scene_id', s['segment_id']) == scene_id:
                        s['image_path'] = str(image_path)

                print("✓")

            except Exception as e:
                print(f"✗ (Error: {e})")
                # Create placeholder image
                self._create_placeholder(image_path, width, height, seg['text'])
                # Apply to all segments with this scene_id
                for s in segments:
                    if s.get('scene_id', s['segment_id']) == scene_id:
                        s['image_path'] = str(image_path)

            # Rate limiting
            time.sleep(0.5)

        print(f"Generated {num_scenes} unique scene images")
        return segments

    def _letterbox_image(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """
        Resize image to fit target dimensions while preserving aspect ratio.
        Adds black bars (letterboxing) if needed.

        Args:
            img: Source image
            target_width: Target width
            target_height: Target height

        Returns:
            Letterboxed image at target dimensions
        """
        # Calculate aspect ratios
        img_aspect = img.width / img.height
        target_aspect = target_width / target_height

        # Scale image to fit within target dimensions
        if img_aspect > target_aspect:
            # Image is wider - fit to width, add bars on top/bottom
            new_width = target_width
            new_height = int(target_width / img_aspect)
        else:
            # Image is taller - fit to height, add bars on left/right
            new_height = target_height
            new_width = int(target_height * img_aspect)

        # Resize image preserving aspect ratio
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create black canvas at target size
        canvas = Image.new('RGB', (target_width, target_height), color=(0, 0, 0))

        # Center the resized image on the canvas
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        canvas.paste(img_resized, (x_offset, y_offset))

        return canvas

    def _create_placeholder(self, path: Path, width: int, height: int, text: str):
        """Create a placeholder image for failed generations."""
        from PIL import ImageDraw, ImageFont

        img = Image.new('RGB', (width, height), color=(50, 50, 50))
        draw = ImageDraw.Draw(img)

        # Try to use a simple font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        except:
            font = ImageFont.load_default()

        # Draw text
        text_wrapped = text[:100] + "..." if len(text) > 100 else text
        draw.text((width//2, height//2), text_wrapped, fill=(200, 200, 200), anchor="mm", font=font)

        img.save(path)


class VideoAssembler:
    """Assemble images and audio into final video."""

    def __init__(self):
        """Initialize video assembler."""
        pass

    def create_video(
        self,
        segments: List[Dict],
        audio_path: str,
        output_path: Path,
        resolution: str = "720p",
        fps: int = 24
    ):
        """
        Create video from images and audio.

        Args:
            segments: List of segments with image_path and timing
            audio_path: Path to audio file
            output_path: Output video path
            resolution: Video resolution
            fps: Frames per second
        """
        print(f"Assembling video...")
        print(f"  Output: {output_path}")
        print(f"  Resolution: {resolution} @ {fps} fps")

        # Load audio
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration

        print(f"  Audio duration: {audio_duration:.2f}s")
        print(f"  Creating {len(segments)} image clips...")

        # Create image clips with exact timing
        clips = []
        for i, seg in enumerate(segments, 1):
            if not seg['image_path'] or not Path(seg['image_path']).exists():
                print(f"  Warning: Missing image for segment {i}, skipping")
                continue

            duration = seg['duration']

            print(f"    Clip {i}: {duration:.2f}s", end=" ")

            try:
                # MoviePy 2.x: duration and fps are constructor parameters
                clip = ImageClip(seg['image_path'], duration=duration)
                clip = clip.with_fps(fps)
                clips.append(clip)
                print("✓")
            except Exception as e:
                print(f"✗ (Error: {e})")

        if not clips:
            raise Exception("No valid image clips created")

        # Concatenate all clips
        print(f"  Concatenating {len(clips)} clips...")
        final_video = concatenate_videoclips(clips, method="compose")

        # Add audio (MoviePy 2.x uses with_audio instead of set_audio)
        print(f"  Adding audio track...")
        final_video = final_video.with_audio(audio_clip)

        # Verify timing
        video_duration = final_video.duration
        print(f"  Video duration: {video_duration:.2f}s")

        if abs(video_duration - audio_duration) > 0.5:
            print(f"  Warning: Video/audio duration mismatch: {video_duration:.2f}s vs {audio_duration:.2f}s")

        # Export video
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  Exporting to {output_path}...")

        final_video.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            bitrate='2500k',
            preset='medium',
            threads=4
        )

        print(f"✓ Video created successfully: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate YouTube videos from podcast audio with AI images",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--audio',
        type=Path,
        required=True,
        help='Path to audio file (WAV, MP3, etc.)'
    )

    parser.add_argument(
        '--theme',
        type=str,
        required=True,
        help='Visual theme/style (e.g., "colored chalk drawing with dark theme")'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output video path (default: auto-generated)'
    )

    parser.add_argument(
        '--resolution',
        choices=['720p', '1080p'],
        default='720p',
        help='Video resolution (default: 720p)'
    )

    parser.add_argument(
        '--min-duration',
        type=float,
        default=5.0,
        help='Minimum seconds per image (default: 5)'
    )

    parser.add_argument(
        '--max-duration',
        type=float,
        default=15.0,
        help='Maximum seconds per image (default: 15)'
    )

    parser.add_argument(
        '--model',
        default='dall-e-3',
        help='Image model: dall-e-3, dall-e-2 (OpenAI), or OpenRouter models (default: dall-e-3)'
    )

    parser.add_argument(
        '--fps',
        type=int,
        default=24,
        help='Video frame rate (default: 24)'
    )

    parser.add_argument(
        '--whisper-model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )

    parser.add_argument(
        '--keep-images',
        action='store_true',
        default=True,
        help='Keep generated images after video creation'
    )

    args = parser.parse_args()

    # Validate input
    if not args.audio.exists():
        print(f"ERROR: Audio file not found: {args.audio}")
        sys.exit(1)

    # Generate output path if not specified
    if not args.output:
        audio_stem = args.audio.stem
        output_dir = Path('output') / audio_stem
        args.output = output_dir / 'video.mp4'

    # Create output directory structure
    output_dir = args.output.parent
    images_dir = output_dir / 'images'

    print("=" * 80)
    print("VIDEO GENERATOR")
    print("=" * 80)
    print(f"Audio:      {args.audio}")
    print(f"Theme:      {args.theme}")
    print(f"Output:     {args.output}")
    print(f"Resolution: {args.resolution}")
    print(f"Duration:   {args.min_duration}s - {args.max_duration}s per image")
    print("=" * 80)
    print()

    try:
        # Initialize API clients
        # Try OpenAI first (preferred), fallback to OpenRouter
        openai_client = None
        openrouter_client = None

        try:
            openai_client = OpenAIClient()
            print("Using OpenAI for image generation")
        except ValueError:
            print("OpenAI API key not found, trying OpenRouter...")
            try:
                openrouter_client = OpenRouterClient()
                print("Using OpenRouter for image generation")
            except ValueError:
                raise ValueError("Neither OpenAI nor OpenRouter API keys found. Set OPENAI_API_KEY/OPEN_AI_API or OPENROUTER_API_KEY environment variable.")

        # Use OpenRouter for text (prompt generation and scene detection)
        if not openrouter_client:
            openrouter_client = OpenRouterClient()

        # Stage 0: Quick transcription for scene detection
        print("Stage 0: Scene Detection")
        print("-" * 80)
        print("Loading Whisper for quick transcript...")
        temp_whisper = whisper.load_model(args.whisper_model)
        quick_result = temp_whisper.transcribe(str(args.audio), language="en")
        full_transcript = ' '.join([seg['text'].strip() for seg in quick_result['segments']])

        # Detect visual scenes using LLM
        scene_detector = SceneDetector(openrouter_client)
        scenes = scene_detector.detect_scenes(
            full_transcript,
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )

        # Save scenes
        scenes_file = output_dir / 'detected_scenes.json'
        scenes_file.parent.mkdir(parents=True, exist_ok=True)
        with open(scenes_file, 'w') as f:
            json.dump(scenes, f, indent=2)
        print(f"Saved detected scenes: {scenes_file}")
        print()

        # Stage 1: Map scenes to timestamps
        print("Stage 1: Scene Timing Analysis")
        print("-" * 80)
        analyzer = AudioAnalyzer(whisper_model=args.whisper_model)
        segments = analyzer.analyze(
            str(args.audio),
            scenes,
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )

        # Save timing segments
        timing_file = output_dir / 'timing_segments.json'
        timing_file.parent.mkdir(parents=True, exist_ok=True)
        with open(timing_file, 'w') as f:
            json.dump(segments, f, indent=2)
        print(f"Saved timing data: {timing_file}")
        print()

        # Stage 2: Generate image prompts
        print("Stage 2: Image Prompt Generation")
        print("-" * 80)
        prompt_gen = PromptGenerator(openrouter_client)
        segments = prompt_gen.generate_prompts(segments, args.theme)

        # Save prompts
        prompts_file = output_dir / 'image_prompts.json'
        with open(prompts_file, 'w') as f:
            json.dump(segments, f, indent=2)
        print(f"Saved image prompts: {prompts_file}")
        print()

        # Stage 3: Generate images
        print("Stage 3: Image Generation")
        print("-" * 80)
        image_gen = ImageGenerator(openai_client=openai_client, openrouter_client=openrouter_client, model=args.model)
        segments = image_gen.generate_images(segments, images_dir, args.resolution)

        # Update prompts file with image paths
        with open(prompts_file, 'w') as f:
            json.dump(segments, f, indent=2)
        print()

        # Stage 4: Assemble video
        print("Stage 4: Video Assembly")
        print("-" * 80)
        assembler = VideoAssembler()
        assembler.create_video(
            segments,
            str(args.audio),
            args.output,
            resolution=args.resolution,
            fps=args.fps
        )
        print()

        # Summary
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"Video:        {args.output}")
        print(f"Images:       {images_dir} ({len(segments)} images)")
        print(f"Timing data:  {timing_file}")
        print(f"Prompts:      {prompts_file}")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"ERROR: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
