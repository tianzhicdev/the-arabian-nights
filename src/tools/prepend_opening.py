#!/usr/bin/env python3
"""
Prepend opening segment to an episode video.
Usage: python scripts/prepend_opening.py --episode-video episode.mp4 --opening opening.mp4 --output final.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

def prepend_opening(opening_path: Path, episode_path: Path, output_path: Path):
    """Concatenate opening and episode videos."""

    # Create concat file list
    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"

    with open(concat_file, 'w') as f:
        f.write(f"file '{opening_path.absolute()}'\n")
        f.write(f"file '{episode_path.absolute()}'\n")

    print(f"Concatenating videos...")
    print(f"  Opening: {opening_path}")
    print(f"  Episode: {episode_path}")
    print(f"  Output: {output_path}")

    # Concatenate using ffmpeg
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise Exception("Failed to concatenate videos")

    # Clean up concat file
    concat_file.unlink()

    print(f"  ✓ Final video created: {output_path}")

    # Get final duration
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)],
        capture_output=True,
        text=True
    )

    duration = float(result.stdout.strip())
    print(f"  ✓ Total duration: {duration:.2f}s")

def main():
    parser = argparse.ArgumentParser(description='Prepend opening to episode video')
    parser.add_argument('--opening', type=str, required=True,
                        help='Path to opening video')
    parser.add_argument('--episode-video', type=str, required=True,
                        help='Path to episode video')
    parser.add_argument('--output', type=str, required=True,
                        help='Output video path')

    args = parser.parse_args()

    opening_path = Path(args.opening)
    episode_path = Path(args.episode_video)
    output_path = Path(args.output)

    if not opening_path.exists():
        print(f"Error: Opening video not found: {opening_path}")
        sys.exit(1)

    if not episode_path.exists():
        print(f"Error: Episode video not found: {episode_path}")
        sys.exit(1)

    prepend_opening(opening_path, episode_path, output_path)

    print(f"\n✓ Episode with opening complete: {output_path}")

if __name__ == '__main__':
    main()
