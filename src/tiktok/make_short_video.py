#!/usr/bin/env python3
"""
Create branded short-form videos from episode scene videos.

Takes horizontal scene videos, converts them to vertical, concatenates them,
and adds branding (title, subtitle, logo, social handle).
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def run_command(cmd: List[str], description: str = ""):
    """Run a shell command and handle errors."""
    if description:
        print(f"  {description}...")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error: {description or 'Command'} failed")
        print(result.stderr)
        sys.exit(1)

    return result


def convert_to_vertical(input_file: Path, output_file: Path):
    """Convert horizontal video to vertical (1080x1920)."""
    cmd = [
        'ffmpeg', '-i', str(input_file),
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'copy',
        str(output_file), '-y'
    ]
    run_command(cmd, f"Converting {input_file.name} to vertical")


def concatenate_videos(video_files: List[Path], output_file: Path):
    """Concatenate multiple videos using ffmpeg concat."""
    # Create concat list file
    concat_file = output_file.parent / 'concat_list.txt'
    with open(concat_file, 'w') as f:
        for video_file in video_files:
            f.write(f"file '{video_file.absolute()}'\n")

    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        str(output_file), '-y'
    ]
    run_command(cmd, f"Concatenating {len(video_files)} videos")

    # Clean up concat list
    concat_file.unlink()


def add_branding(
    input_file: Path,
    output_file: Path,
    title: str,
    subtitle: str,
    social_handle: str,
    logo_path: Path
):
    """Add title, subtitle, logo, and social handle to video."""
    # Build filter_complex for text and logo overlay
    filter_complex = (
        f"[1:v]scale=-1:200[logo];"
        f"[0:v]drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='{title}':"
        f"fontcolor=white:fontsize=48:x=(w-text_w)/2:y=220:"
        f"box=1:boxcolor=black@0.6:boxborderw=10,"
        f"drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='{subtitle}':"
        f"fontcolor=white:fontsize=36:x=(w-text_w)/2:y=300:"
        f"box=1:boxcolor=black@0.6:boxborderw=10,"
        f"drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='{social_handle}':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=1720:"
        f"box=1:boxcolor=black@0.6:boxborderw=10[v];"
        f"[v][logo]overlay=(W-w)/2:1480"
    )

    cmd = [
        'ffmpeg',
        '-i', str(input_file),
        '-i', str(logo_path),
        '-filter_complex', filter_complex,
        '-codec:a', 'copy',
        str(output_file), '-y'
    ]
    run_command(cmd, "Adding branding overlay")


def main():
    parser = argparse.ArgumentParser(
        description='Create branded short-form videos from episode scenes'
    )
    parser.add_argument(
        '--source-dir',
        type=Path,
        required=True,
        help='Source directory containing scene videos (e.g., output/animal_farm/episode_1)'
    )
    parser.add_argument(
        '--scenes',
        required=True,
        help='Scene range to include (e.g., "26-35" or "1,2,5-8")'
    )
    parser.add_argument(
        '--title',
        required=True,
        help='Video title (e.g., "Animal Farm by George Orwell")'
    )
    parser.add_argument(
        '--subtitle',
        required=True,
        help='Video subtitle (e.g., "Illustrated Narration by Wormhole Podcast")'
    )
    parser.add_argument(
        '--social-handle',
        default='@the-wormhole-podcast',
        help='Social media handle (default: @the-wormhole-podcast)'
    )
    parser.add_argument(
        '--logo',
        type=Path,
        default=Path('resources/wornhole-logo.png'),
        help='Path to logo image (default: resources/wornhole-logo.png)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory (default: output/tiktok/<source-dir-name>_scenes_<range>)'
    )

    args = parser.parse_args()

    # Validate source directory
    if not args.source_dir.exists():
        print(f"Error: Source directory not found: {args.source_dir}")
        sys.exit(1)

    video_dir = args.source_dir / 'video'
    if not video_dir.exists():
        print(f"Error: Video directory not found: {video_dir}")
        sys.exit(1)

    # Validate logo
    if not args.logo.exists():
        print(f"Error: Logo file not found: {args.logo}")
        sys.exit(1)

    # Parse scene numbers
    scene_numbers = []
    for part in args.scenes.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            scene_numbers.extend(range(start, end + 1))
        else:
            scene_numbers.append(int(part))

    print(f"Creating short video from scenes: {', '.join(map(str, scene_numbers))}")

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        source_name = args.source_dir.name
        scenes_label = args.scenes.replace(',', '_')
        output_dir = Path('output/tiktok') / f"{source_name}_scenes_{scenes_label}"

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Convert scenes to vertical
    print("\nStep 1: Converting scenes to vertical format...")
    vertical_files = []
    for scene_num in scene_numbers:
        # Find scene video file (could be with_audio or slides)
        scene_pattern = f"scene_{scene_num:03d}_with_audio.mp4"
        scene_file = video_dir / scene_pattern

        if not scene_file.exists():
            # Try slides version
            scene_pattern = f"scene_{scene_num:03d}_slides.mp4"
            scene_file = video_dir / scene_pattern

        if not scene_file.exists():
            print(f"Warning: Scene {scene_num} not found, skipping")
            continue

        vertical_file = output_dir / f"clip_{scene_num:03d}.mp4"
        if not vertical_file.exists():
            convert_to_vertical(scene_file, vertical_file)
        else:
            print(f"  Skipping {scene_file.name} (already converted)")

        vertical_files.append(vertical_file)

    if not vertical_files:
        print("Error: No scene videos found")
        sys.exit(1)

    # Concatenate videos
    print(f"\nStep 2: Concatenating {len(vertical_files)} videos...")
    concat_output = output_dir / 'concatenated_no_branding.mp4'
    concatenate_videos(vertical_files, concat_output)

    # Add branding
    print("\nStep 3: Adding branding...")
    final_output = output_dir / 'final_branded.mp4'
    add_branding(
        concat_output,
        final_output,
        args.title,
        args.subtitle,
        args.social_handle,
        args.logo
    )

    print(f"\n✓ Success! Created: {final_output}")
    print(f"  Duration: {get_duration(final_output):.1f} seconds")
    print(f"  Size: {final_output.stat().st_size / 1024 / 1024:.1f} MB")


def get_duration(video_file: Path) -> float:
    """Get video duration in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_file)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


if __name__ == '__main__':
    main()
