"""
Convert horizontal videos to vertical 9:16 format for YouTube Shorts.

Strategy: Scale video to fit vertically, add blurred background to fill sides.
"""

import subprocess
import sys
from pathlib import Path
import argparse


def convert_to_vertical(input_video: Path, output_video: Path, target_height: int = 1920, target_width: int = 1080):
    """
    Convert horizontal video to vertical 9:16 format.

    Strategy:
    1. Create blurred background from input (scaled to 9:16)
    2. Overlay original video scaled to fit within 9:16
    3. Result: Video centered with blurred background on sides

    Args:
        input_video: Input video file
        output_video: Output video file
        target_height: Target height (default: 1920 for 9:16)
        target_width: Target width (default: 1080 for 9:16)
    """

    print(f"Converting: {input_video.name}")
    print(f"  Input: 16:9 horizontal")
    print(f"  Output: 9:16 vertical ({target_width}x{target_height})")

    # FFmpeg command for vertical conversion with blurred background
    # This is the "TikTok style" - blurred background + centered video
    cmd = [
        'ffmpeg',
        '-i', str(input_video),
        '-filter_complex', (
            # Create two streams:
            # [0] Blurred background (stretched to 9:16)
            f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},boxblur=30:5[bg];'
            # [1] Original video (scaled to fit within 9:16, maintains aspect ratio)
            f'[0:v]scale={target_width}:-1[fg];'
            # Overlay original on top of blurred background
            f'[bg][fg]overlay=(W-w)/2:(H-h)/2'
        ),
        '-c:a', 'copy',  # Copy audio without re-encoding
        '-y',  # Overwrite output file
        str(output_video)
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  ✓ Converted successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Conversion failed: {e.stderr.decode()}")
        return False


def convert_directory(input_dir: Path, output_dir: Path):
    """Convert all MP4 files in directory to vertical format."""

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all MP4 files
    mp4_files = sorted(input_dir.glob("clip_*.mp4"))

    if not mp4_files:
        print(f"❌ No clip_*.mp4 files found in {input_dir}")
        return

    print(f"📹 Found {len(mp4_files)} clips to convert")
    print(f"📂 Input: {input_dir}")
    print(f"📂 Output: {output_dir}")
    print()

    success_count = 0
    failed_count = 0

    for i, input_file in enumerate(mp4_files, 1):
        print(f"[{i}/{len(mp4_files)}] ", end="")

        output_file = output_dir / input_file.name

        if convert_to_vertical(input_file, output_file):
            success_count += 1
        else:
            failed_count += 1

        print()

    print("=" * 60)
    print(f"📊 CONVERSION SUMMARY")
    print("=" * 60)
    print(f"Total: {len(mp4_files)}")
    print(f"Success: {success_count} ✓")
    print(f"Failed: {failed_count} ✗")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Convert horizontal videos to vertical 9:16 format for YouTube Shorts"
    )
    parser.add_argument(
        '--input-dir',
        required=True,
        help="Input directory with horizontal videos"
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help="Output directory for vertical videos"
    )
    parser.add_argument(
        '--width',
        type=int,
        default=1080,
        help="Target width (default: 1080)"
    )
    parser.add_argument(
        '--height',
        type=int,
        default=1920,
        help="Target height (default: 1920)"
    )

    args = parser.parse_args()

    convert_directory(args.input_dir, args.output_dir)


if __name__ == '__main__':
    main()
