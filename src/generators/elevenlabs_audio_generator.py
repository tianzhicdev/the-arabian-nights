#!/usr/bin/env python3
"""
Parallel ElevenLabs Audio Generation for Scenes.

Uses ThreadPoolExecutor for concurrent HTTP requests to ElevenLabs API.
Supports ElevenLabs v3 with emotion tags.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


class ElevenLabsSceneGenerator:
    """Generate audio for individual scenes using ElevenLabs API with emotion support"""

    # Year words for TTS normalization
    ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen']
    TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

    def __init__(self, voice_id: str, api_key: str, model_id: str = "eleven_v3"):
        """
        Initialize ElevenLabs scene generator.

        Args:
            voice_id: ElevenLabs voice ID to use
            api_key: ElevenLabs API key
            model_id: Model ID (eleven_v3 for audio tags, eleven_turbo_v2_5, or eleven_multilingual_v2)
                     For emotion tags, MUST use eleven_v3
        """
        self.voice_id = voice_id
        self.api_key = api_key
        self.model_id = model_id
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def _number_to_words(self, n: int, use_hyphen: bool = False) -> str:
        """Convert a number (0-99) to words."""
        if n < 20:
            return self.ONES[n]
        elif n < 100:
            sep = '-' if use_hyphen and n % 10 != 0 else ' '
            return self.TENS[n // 10] + ('' if n % 10 == 0 else sep + self.ONES[n % 10])
        return str(n)

    def _year_to_words(self, year: int) -> str:
        """Convert a year to spoken form (e.g., 2026 → 'twenty twenty-six')."""
        if 2000 <= year <= 2009:
            return f"two thousand {self._number_to_words(year - 2000)}".strip()
        elif 2010 <= year <= 2099:
            return f"{self._number_to_words(year // 100 % 100)} {self._number_to_words(year % 100, use_hyphen=True)}"
        elif 1900 <= year <= 1999:
            return f"nineteen {self._number_to_words(year % 100, use_hyphen=True)}"
        elif 1800 <= year <= 1899:
            return f"eighteen {self._number_to_words(year % 100, use_hyphen=True)}"
        return str(year)

    def _normalize_text_for_tts(self, text: str) -> str:
        """
        Normalize text for better TTS pronunciation.
        Converts years (1800-2099) to spoken form to avoid mispronunciation.
        """
        import re

        def replace_year(match):
            year = int(match.group(0))
            return self._year_to_words(year)

        # Replace years (4-digit numbers between 1800-2099 that look like years)
        # Use word boundaries to avoid replacing numbers in the middle of other numbers
        normalized = re.sub(r'\b(1[89]\d{2}|20[0-9]{2})\b', replace_year, text)
        return normalized

    def generate_scene_audio(self, scene: Dict, output_path: Path) -> float:
        """
        Generate audio for a single scene.

        Args:
            scene: Scene dictionary with 'sentences' and optional 'pause_after'
            output_path: Path to save MP3 file

        Returns:
            Duration in seconds
        """
        # Skip if file already exists
        if output_path.exists() and output_path.stat().st_size > 0:
            duration = self._get_audio_duration(output_path)
            print(f"  ⏭️  Scene {scene['scene_id']}: {duration:.2f}s (already exists, skipping)")
            return duration

        # Combine all sentences into one text with emotion tags preserved
        text_parts = []
        for sentence in scene['sentences']:
            text_parts.append(sentence)

        full_text = " ".join(text_parts)

        # Normalize text for better TTS pronunciation (years, numbers, etc.)
        full_text = self._normalize_text_for_tts(full_text)

        # Add pause if specified (ElevenLabs doesn't have native pause support,
        # so we'll handle this after generation if needed)
        pause_duration = scene.get('pause_after', 0)

        print(f"\nGenerating audio for Scene {scene['scene_id']}...")
        print(f"  Text preview: {full_text[:100]}{'...' if len(full_text) > 100 else ''}")
        print(f"  Characters: {len(full_text)}")

        # Build request payload
        payload = {
            "text": full_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,  # 0.0 = more consistent, 1.0 = more expressive
                "use_speaker_boost": True
            }
        }

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=300
            )

            if response.status_code != 200:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get('detail', {}).get('message', error_text)
                except:
                    error_msg = error_text
                raise Exception(f"API Error (status {response.status_code}): {error_msg}")

            # Collect audio bytes
            audio_bytes = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    audio_bytes += chunk

            # Save audio
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            # Add pause if needed
            if pause_duration > 0:
                self._add_silence(output_path, pause_duration)

            # Measure duration
            duration = self._get_audio_duration(output_path)
            elapsed = time.time() - start_time

            print(f"  ✓ Scene {scene['scene_id']}: {duration:.2f}s (generated in {elapsed:.1f}s)")
            return duration

        except requests.exceptions.Timeout:
            raise Exception(f"Scene {scene['scene_id']}: Request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Scene {scene['scene_id']}: Network error: {e}")

    def _add_silence(self, audio_path: Path, duration: float):
        """Add silence to the end of an audio file"""
        # Use ffmpeg to add silence
        temp_path = audio_path.with_suffix('.tmp.mp3')

        subprocess.run([
            'ffmpeg', '-i', str(audio_path),
            '-f', 'lavfi', '-t', str(duration), '-i', 'anullsrc=r=24000:cl=mono',
            '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1',
            str(temp_path), '-y'
        ], capture_output=True, check=True)

        temp_path.replace(audio_path)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe"""
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(audio_path)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data['format']['duration'])


class ParallelElevenLabsGenerator:
    """
    Parallel audio generation using ThreadPoolExecutor for concurrent HTTP requests.

    Since ElevenLabs is HTTP-based, we use threads instead of processes for better performance.
    Can process 10-20 scenes concurrently depending on API rate limits.
    """

    def __init__(
        self,
        voice_id: str,
        api_key: str,
        model_id: str = "eleven_v3",
        max_workers: int = 10
    ):
        """
        Initialize parallel ElevenLabs generator.

        Args:
            voice_id: ElevenLabs voice ID
            api_key: ElevenLabs API key
            model_id: Model ID for generation
            max_workers: Number of concurrent threads (default: 10)
                        Adjust based on your API rate limits
        """
        self.voice_id = voice_id
        self.api_key = api_key
        self.model_id = model_id
        self.max_workers = max_workers

    def generate_all_scenes(
        self,
        scenes: List[Dict],
        output_dir: Path
    ) -> Dict[int, float]:
        """
        Generate audio for all scenes in parallel.

        Args:
            scenes: List of scene dictionaries
            output_dir: Directory to save audio files

        Returns:
            Dictionary mapping scene_id to duration in seconds
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Parallel ElevenLabs Audio Generation")
        print(f"{'='*60}")
        print(f"Scenes: {len(scenes)}")
        print(f"Voice ID: {self.voice_id}")
        print(f"Model: {self.model_id}")
        print(f"Max Workers: {self.max_workers}")
        print(f"Output: {output_dir}")
        print(f"{'='*60}\n")

        # Create generator instance for each worker thread
        def generate_scene_wrapper(scene: Dict) -> tuple:
            generator = ElevenLabsSceneGenerator(
                voice_id=self.voice_id,
                api_key=self.api_key,
                model_id=self.model_id
            )

            scene_id = scene['scene_id']
            output_path = output_dir / f"scene_{scene_id:03d}.mp3"

            try:
                duration = generator.generate_scene_audio(scene, output_path)
                return (scene_id, duration, None)
            except Exception as e:
                return (scene_id, 0.0, str(e))

        # Process scenes in parallel
        durations = {}
        errors = {}
        completed_count = 0

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_scene = {
                executor.submit(generate_scene_wrapper, scene): scene
                for scene in scenes
            }

            # Process results as they complete
            for future in as_completed(future_to_scene):
                scene_id, duration, error = future.result()
                completed_count += 1

                if error:
                    errors[scene_id] = error
                    print(f"✗ Scene {scene_id} failed: {error}")
                else:
                    durations[scene_id] = duration

                # Progress update
                progress = (completed_count / len(scenes)) * 100
                print(f"\nProgress: {completed_count}/{len(scenes)} ({progress:.1f}%)")

        elapsed = time.time() - start_time

        # Summary
        print(f"\n{'='*60}")
        print(f"Generation Complete")
        print(f"{'='*60}")
        print(f"Total scenes: {len(scenes)}")
        print(f"Successful: {len(durations)}")
        print(f"Failed: {len(errors)}")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Average time per scene: {elapsed/len(scenes):.1f}s")
        print(f"Total audio duration: {sum(durations.values()):.1f}s")

        if errors:
            print(f"\nErrors:")
            for scene_id, error in errors.items():
                print(f"  Scene {scene_id}: {error}")

        print(f"{'='*60}\n")

        return durations


def main():
    """CLI for testing ElevenLabs parallel generation"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate audio for scenes using ElevenLabs')
    parser.add_argument('--scenes', required=True, help='Path to scenes JSON file')
    parser.add_argument('--output-dir', required=True, help='Output directory for audio files')
    parser.add_argument('--voice-id', required=True, help='ElevenLabs voice ID')
    parser.add_argument('--api-key', help='ElevenLabs API key (or set ELEVENLABS_API_KEY env var)')
    parser.add_argument('--model-id', default='eleven_v3', help='Model ID (use eleven_v3 for audio tags)')
    parser.add_argument('--max-workers', type=int, default=10, help='Number of concurrent workers')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("Error: No API key provided. Use --api-key or set ELEVENLABS_API_KEY environment variable")
        return 1

    # Load scenes
    with open(args.scenes) as f:
        data = json.load(f)
        scenes = data['scenes']

    # Generate audio
    generator = ParallelElevenLabsGenerator(
        voice_id=args.voice_id,
        api_key=api_key,
        model_id=args.model_id,
        max_workers=args.max_workers
    )

    durations = generator.generate_all_scenes(scenes, Path(args.output_dir))

    print(f"✓ Generated audio for {len(durations)} scenes")
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
