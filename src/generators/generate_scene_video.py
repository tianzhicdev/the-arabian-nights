#!/usr/bin/env python3
"""
Scene-Based Video Generation Pipeline
Generates perfectly synced video from episode JSON with scenes.

Pipeline:
1. Load episode JSON
2. Generate audio for each scene (Chatterbox)
3. Measure actual audio durations
4. Generate videos matching durations (Sora)
5. Trim videos to exact match
6. Assemble final video with audio
"""

import argparse
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.secrets'
if env_path.exists():
    load_dotenv(env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_backend import ChatterboxBackend
from src.clients.openai_client import OpenAIClient


class SceneAudioGenerator:
    """Generate audio for scenes using Chatterbox"""

    def __init__(self, audio_prompt_path: str, device: str = 'cpu', speed: float = 1.0):
        self.backend = ChatterboxBackend(
            audio_prompt_path=audio_prompt_path,
            device=device,
            exaggeration=0.7,
            speed=speed
        )

    def generate_scene_audio(self, scene: Dict, output_path: Path) -> float:
        """
        Generate audio for a single scene.

        Returns:
            Duration in seconds
        """
        # Format as dialogues for backend (speaker, text)
        dialogues = []

        # Add all sentences for the scene
        for sentence in scene['sentences']:
            dialogues.append(('Narrator', sentence))

        # Add pause at end if specified
        if scene.get('pause_after', 0) > 0:
            dialogues.append(('Narrator', f"[pause-{scene['pause_after']}]"))

        print(f"\nGenerating audio for Scene {scene['scene_id']}...")
        audio_bytes = self.backend.generate_chunk(dialogues, 1, 1)

        # Save audio
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        # Measure duration using ffprobe
        duration = self._get_audio_duration(output_path)
        print(f"  ✓ Scene {scene['scene_id']}: {duration:.2f}s → {output_path.name}")

        return duration

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


class SceneVideoGenerator:
    """Generate videos for scenes using Sora"""

    def __init__(self, openai_client: OpenAIClient, model: str = 'sora-2'):
        self.client = openai_client
        self.model = model

    def determine_video_chunks(self, duration: float) -> List[int]:
        """
        Determine optimal video chunk sizes for a given duration.
        Sora supports: 4s, 8s, 12s

        Strategy: Generate slightly longer videos, then trim to exact duration
        """
        if duration <= 4:
            return [4]
        elif duration <= 8:
            return [8]
        elif duration <= 12:
            return [12]
        else:
            # For longer durations, break into chunks
            chunks = []
            remaining = duration

            while remaining > 0:
                if remaining > 12:
                    chunks.append(12)
                    remaining -= 12
                elif remaining > 8:
                    chunks.append(12)  # Use 12s, will trim
                    remaining = 0
                elif remaining > 4:
                    chunks.append(8)  # Use 8s, will trim
                    remaining = 0
                else:
                    chunks.append(4)  # Use 4s, will trim
                    remaining = 0

            return chunks

    def generate_scene_videos(
        self,
        scene: Dict,
        duration: float,
        episode_context: str,
        art_style: str,
        output_dir: Path
    ) -> List[Path]:
        """
        Generate video(s) for a scene.

        Returns:
            List of video file paths (untrimmed)
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine chunks needed
        chunks = self.determine_video_chunks(duration)
        print(f"\nScene {scene['scene_id']} ({duration:.2f}s):")
        print(f"  Video strategy: {' + '.join(f'{c}s' for c in chunks)} = {sum(chunks)}s (will trim to {duration:.2f}s)")

        # Build prompt
        prompt = self._build_video_prompt(scene, episode_context, art_style)

        video_paths = []
        for i, chunk_duration in enumerate(chunks, 1):
            print(f"\n  Generating video {i}/{len(chunks)} ({chunk_duration}s)...")
            print(f"    Prompt: {prompt[:100]}...")

            try:
                # Generate video
                video_url = self.client.generate_video(
                    prompt=prompt,
                    model=self.model,
                    seconds=chunk_duration,
                    size="1280x720"
                )

                # Download video
                video_path = output_dir / f"scene_{scene['scene_id']:03d}_part_{i}_{chunk_duration}s.mp4"
                print(f"    Downloading video...")

                import requests
                headers = {
                    "Authorization": f"Bearer {self.client.api_key}"
                }
                response = requests.get(video_url, headers=headers, timeout=300)
                response.raise_for_status()

                with open(video_path, 'wb') as f:
                    f.write(response.content)

                video_paths.append(video_path)
                print(f"    ✓ Saved: {video_path.name}")

            except Exception as e:
                print(f"    ✗ Error: {e}")
                raise

        return video_paths

    def _build_video_prompt(self, scene: Dict, episode_context: str, art_style: str) -> str:
        """Build detailed video prompt for Sora"""
        video_desc = scene['video_description']
        camera_style = scene.get('camera_style', 'cinematic, smooth')

        prompt = (
            f"{video_desc}. "
            f"Camera: {camera_style}. "
            f"Style: {art_style}. "
            f"Context: {episode_context}"
        )

        return prompt[:500]  # Sora prompt limit


class VideoAssembler:
    """Assemble final video from scenes"""

    def trim_video(self, video_path: Path, target_duration: float, output_path: Path):
        """Trim video to exact duration"""
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-t', str(target_duration),
            '-c', 'copy',
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg trim failed: {result.stderr}")

    def concatenate_videos(self, video_paths: List[Path], output_path: Path):
        """Concatenate multiple videos"""
        # Create concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video in video_paths:
                f.write(f"file '{video.absolute()}'\n")

        try:
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"ffmpeg concat failed: {result.stderr}")
        finally:
            Path(concat_file).unlink(missing_ok=True)

    def add_audio_to_video(self, video_path: Path, audio_path: Path, output_path: Path):
        """Add audio track to video"""
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(audio_path),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v',
            '-map', '1:a',
            '-shortest',
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg audio merge failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Generate video from episode JSON")
    parser.add_argument("--episode-json", required=True, help="Path to episode JSON file")
    parser.add_argument("--audio-prompt", required=True, help="Path to voice cloning audio prompt")
    parser.add_argument("--output-dir", default="output/scene_video", help="Output directory")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device for Chatterbox")
    parser.add_argument("--speed", type=float, default=1.0, help="Audio speed multiplier")
    parser.add_argument("--model", default="sora-2", choices=["sora-2", "sora-2-pro"], help="Sora model")

    args = parser.parse_args()

    print("=" * 80)
    print("SCENE-BASED VIDEO GENERATION PIPELINE")
    print("=" * 80)
    print(f"Episode JSON: {args.episode_json}")
    print(f"Audio Prompt: {args.audio_prompt}")
    print(f"Output Dir:   {args.output_dir}")
    print(f"Device:       {args.device}")
    print(f"Speed:        {args.speed}x")
    print(f"Sora Model:   {args.model}")
    print("=" * 80)
    print()

    # Load episode JSON
    with open(args.episode_json, 'r') as f:
        episode_data = json.load(f)

    episode = episode_data['episode']
    scenes = episode_data['scenes']

    print(f"Episode: {episode['title']}")
    print(f"Scenes:  {len(scenes)}")
    print()

    output_dir = Path(args.output_dir)
    audio_dir = output_dir / 'audio'
    video_dir = output_dir / 'videos'

    # Initialize components
    openai_client = OpenAIClient()
    audio_gen = SceneAudioGenerator(args.audio_prompt, device=args.device, speed=args.speed)
    video_gen = SceneVideoGenerator(openai_client, model=args.model)
    assembler = VideoAssembler()

    # Stage 1: Generate Audio for All Scenes
    print("\n" + "=" * 80)
    print("STAGE 1: Audio Generation")
    print("=" * 80)

    scene_audio_paths = []
    for scene in scenes:
        audio_path = audio_dir / f"scene_{scene['scene_id']:03d}.wav"
        duration = audio_gen.generate_scene_audio(scene, audio_path)
        scene['actual_duration'] = duration
        scene_audio_paths.append(audio_path)

    # Save updated JSON with durations
    updated_json_path = output_dir / 'episode_with_durations.json'
    with open(updated_json_path, 'w') as f:
        json.dump(episode_data, f, indent=2)
    print(f"\n✓ Saved updated JSON: {updated_json_path}")

    # Combine all audio
    print("\nCombining scene audio...")
    from pydub import AudioSegment
    combined_audio = AudioSegment.empty()
    for audio_path in scene_audio_paths:
        combined_audio += AudioSegment.from_wav(str(audio_path))

    combined_audio_path = output_dir / 'combined_audio.wav'
    combined_audio.export(str(combined_audio_path), format='wav')
    print(f"✓ Combined audio: {combined_audio_path} ({len(combined_audio)/1000:.1f}s)")

    # Stage 2: Generate Videos for All Scenes
    print("\n" + "=" * 80)
    print("STAGE 2: Video Generation")
    print("=" * 80)

    trimmed_video_paths = []
    for scene in scenes:
        duration = scene['actual_duration']

        # Generate video(s) for scene
        raw_videos = video_gen.generate_scene_videos(
            scene,
            duration,
            episode['context'],
            episode['art_style'],
            video_dir
        )

        # If multiple chunks, concatenate first
        if len(raw_videos) > 1:
            print(f"\n  Concatenating {len(raw_videos)} video parts...")
            concat_path = video_dir / f"scene_{scene['scene_id']:03d}_concat.mp4"
            assembler.concatenate_videos(raw_videos, concat_path)
            video_to_trim = concat_path
        else:
            video_to_trim = raw_videos[0]

        # Trim to exact duration
        print(f"  Trimming to {duration:.2f}s...")
        trimmed_path = video_dir / f"scene_{scene['scene_id']:03d}_final.mp4"
        assembler.trim_video(video_to_trim, duration, trimmed_path)
        trimmed_video_paths.append(trimmed_path)
        print(f"  ✓ Final scene video: {trimmed_path.name}")

    # Stage 3: Assemble Final Video
    print("\n" + "=" * 80)
    print("STAGE 3: Final Assembly")
    print("=" * 80)

    # Concatenate all trimmed scene videos
    print("\nConcatenating all scene videos...")
    video_only_path = output_dir / 'video_only.mp4'
    assembler.concatenate_videos(trimmed_video_paths, video_only_path)
    print(f"✓ Video-only file: {video_only_path}")

    # Add combined audio
    print("\nAdding audio to video...")
    final_video_path = output_dir / 'final_video.mp4'
    assembler.add_audio_to_video(video_only_path, combined_audio_path, final_video_path)

    print("\n" + "=" * 80)
    print("SUCCESS! Video Generation Complete")
    print("=" * 80)
    print(f"Episode:      {episode['title']}")
    print(f"Scenes:       {len(scenes)}")
    print(f"Total Audio:  {len(combined_audio)/1000:.1f}s")
    print(f"Final Video:  {final_video_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
