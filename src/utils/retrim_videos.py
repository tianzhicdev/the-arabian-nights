#!/usr/bin/env python3
"""
Re-trim existing videos to match audio durations exactly.
"""

import json
from pathlib import Path
import subprocess
from src.generators.video_assembler import VideoAssembler

def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr}")

    return float(result.stdout.strip())

def main():
    # Load checkpoint to get scene durations
    checkpoint_path = Path('output/anansi-and-the-scattered-wisdom/checkpoint.json')

    with open(checkpoint_path) as f:
        checkpoint = json.load(f)

    scenes = checkpoint['scenes_data']['scenes']

    assembler = VideoAssembler()

    print("\n" + "="*80)
    print("RE-TRIMMING VIDEOS TO EXACT AUDIO DURATIONS")
    print("="*80 + "\n")

    for scene in scenes:
        scene_id = scene['scene_id']
        target_duration = scene['actual_duration']

        # Check if video exists
        video_path = Path(f'output/anansi-and-the-scattered-wisdom/raw_videos/scene_{scene_id:03d}_final.mp4')
        audio_path = Path(f'output/anansi-and-the-scattered-wisdom/raw_audio/scene_{scene_id:03d}.wav')

        if not video_path.exists():
            print(f"Scene {scene_id}: SKIP (video not found)")
            continue

        if not audio_path.exists():
            print(f"Scene {scene_id}: SKIP (audio not found)")
            continue

        # Get actual audio duration (more reliable than checkpoint)
        actual_audio_duration = get_audio_duration(audio_path)

        # Get current video duration
        current_video_duration = get_audio_duration(video_path)  # Works for video too

        diff = current_video_duration - actual_audio_duration

        print(f"Scene {scene_id:2d}: Audio={actual_audio_duration:.3f}s, Video={current_video_duration:.3f}s, Diff={diff:+.3f}s")

        if abs(diff) < 0.05:  # Within 50ms tolerance
            print(f"           ✓ Already in sync, skipping")
            continue

        # Re-trim video
        print(f"           Re-trimming to {actual_audio_duration:.3f}s...")

        temp_path = video_path.parent / f"{video_path.stem}_retrimmed{video_path.suffix}"

        try:
            assembler.trim_video(video_path, actual_audio_duration, temp_path)

            # Replace original with re-trimmed version
            video_path.unlink()
            temp_path.rename(video_path)

            print(f"           ✓ Successfully re-trimmed")

        except Exception as e:
            print(f"           ✗ Error: {e}")
            temp_path.unlink(missing_ok=True)

    print("\n" + "="*80)
    print("RE-TRIMMING COMPLETE")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
