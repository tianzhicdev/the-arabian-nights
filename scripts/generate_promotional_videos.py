#!/usr/bin/env python3
"""
Generate promotional short videos using Sora in VERTICAL format.

Workflow:
1. Read audiobook_with_timing.json (output from generate_promotional_audio.py)
2. For each scene:
   - Generate Sora video (using scene_description)
   - Convert to vertical format (1080x1920) - IMPORTANT!
   - Pad audio with silence to match video duration
   - Combine audio + video
3. Concatenate all scenes into final vertical promotional short

Requirements:
- Vertical format (1080x1920) for TikTok/Instagram Reels
- Audio-first approach: audio duration determines video duration
- Sora durations: 4, 8, or 12 seconds only
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from openai_client import OpenAIClient

# Load environment variables
load_dotenv('.env.secrets')

# Configuration
OPENAI_API_KEY = os.getenv("OPEN_AI_API")
SORA_MODEL = "sora-2"
SORA_VERTICAL_SIZE = "720x1280"  # Sora vertical format (will convert to 1080x1920)
FINAL_VERTICAL_SIZE = "1080x1920"  # Final output format for TikTok/Instagram


def add_silence_to_audio(audio_path: Path, silence_duration: float, output_path: Path):
    """Add silence to the end of an audio file using ffmpeg"""
    if silence_duration <= 0:
        # No padding needed, just copy
        subprocess.run(['cp', str(audio_path), str(output_path)], check=True)
        return

    # Generate silence and concatenate
    subprocess.run([
        'ffmpeg', '-i', str(audio_path),
        '-f', 'lavfi', '-t', str(silence_duration), '-i', 'anullsrc=r=24000:cl=mono',
        '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1',
        str(output_path), '-y', '-loglevel', 'error'
    ], check=True)


def convert_to_vertical(input_video: Path, output_video: Path):
    """Convert horizontal video to vertical (1080x1920) with black bars"""
    cmd = [
        'ffmpeg', '-i', str(input_video),
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'copy',
        str(output_video), '-y', '-loglevel', 'error'
    ]
    subprocess.run(cmd, check=True)


def combine_audio_video(video_path: Path, audio_path: Path, output_path: Path):
    """Combine video and audio files"""
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-i', str(audio_path),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        str(output_path), '-y', '-loglevel', 'error'
    ]
    subprocess.run(cmd, check=True)


def generate_sora_video(
    prompt: str,
    duration: int,
    output_path: Path,
    client: OpenAIClient
) -> Path:
    """
    Generate video using Sora API.

    Args:
        prompt: Video description
        duration: Duration in seconds (4, 8, or 12)
        output_path: Where to save video
        client: OpenAIClient instance

    Returns:
        Path to generated video
    """
    print(f"       🎬 Generating {duration}s Sora video...")
    print(f"          Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    try:
        # Call Sora API using OpenAIClient.generate_video()
        content_url = client.generate_video(
            prompt=prompt,
            model=SORA_MODEL,
            seconds=duration,
            size=SORA_VERTICAL_SIZE  # Request vertical format (720x1280)
        )

        # Download video from /content endpoint (requires authorization)
        print(f"          Downloading video...")
        import requests
        headers = {
            "Authorization": f"Bearer {client.api_key}"
        }
        video_response = requests.get(content_url, headers=headers, timeout=300)
        video_response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(video_response.content)

        print(f"          ✓ Video generated: {output_path.name}")
        return output_path

    except Exception as e:
        raise Exception(f"Sora generation failed: {e}")


def process_scene(
    scene: Dict,
    chapter_num: int,
    short_id: int,
    audio_dir: Path,
    video_dir: Path,
    client: OpenAIClient
) -> Path:
    """
    Process a single scene: generate video, pad audio, combine.

    Returns:
        Path to final scene video with audio
    """
    scene_id = scene['scene_id']

    print(f"\n    Scene {scene_id}:")

    # Check if we have timing data
    if 'audio_duration' not in scene or 'sora_duration' not in scene:
        raise Exception(f"Scene {scene_id} missing timing data. Run generate_promotional_audio.py first!")

    audio_duration = scene['audio_duration']
    sora_duration = scene['sora_duration']
    silence_padding = scene['silence_padding']
    scene_description = scene['scene_description']

    print(f"       Audio: {audio_duration}s → Sora: {sora_duration}s (pad: {silence_padding}s)")

    # Paths
    audio_file = audio_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / scene['audio_file']
    sora_raw = video_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / f"scene_{scene_id:02d}_raw.mp4"
    sora_vertical = video_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / f"scene_{scene_id:02d}_vertical.mp4"
    audio_padded = video_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / f"scene_{scene_id:02d}_audio_padded.mp3"
    final_video = video_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / f"scene_{scene_id:02d}_final.mp4"

    # Skip if final video already exists
    if final_video.exists():
        print(f"       ⏭️  Final video exists, skipping")
        return final_video

    # Step 1: Generate Sora video (if not exists)
    if not sora_raw.exists():
        generate_sora_video(
            prompt=scene_description,
            duration=sora_duration,
            output_path=sora_raw,
            client=client
        )
    else:
        print(f"       ⏭️  Sora video exists, skipping generation")

    # Step 2: Convert to vertical (if not already vertical)
    if not sora_vertical.exists():
        print(f"       📐 Converting to vertical (1080x1920)...")
        convert_to_vertical(sora_raw, sora_vertical)
        print(f"          ✓ Vertical video created")
    else:
        print(f"       ⏭️  Vertical video exists, skipping conversion")

    # Step 3: Pad audio with silence
    if not audio_padded.exists():
        print(f"       🔇 Padding audio with {silence_padding}s silence...")
        add_silence_to_audio(audio_file, silence_padding, audio_padded)
        print(f"          ✓ Padded audio created")
    else:
        print(f"       ⏭️  Padded audio exists, skipping")

    # Step 4: Combine vertical video + padded audio
    if not final_video.exists():
        print(f"       🎞️  Combining video + audio...")
        combine_audio_video(sora_vertical, audio_padded, final_video)
        print(f"          ✓ Final scene video created")

    return final_video


def create_ending_segment(output_path: Path, duration: float = 10.0) -> Path:
    """
    Create 10-second ending segment with logo and social handle.

    Args:
        output_path: Where to save the ending segment
        duration: Duration of ending in seconds (default: 10)

    Returns:
        Path to created ending video
    """
    logo_path = Path("resources/wornhole-logo.png")  # Note: typo in original filename
    social_handle = "@the-wormhole-podcast"

    if not logo_path.exists():
        raise Exception(f"Logo not found: {logo_path}")

    # Create ending: black background (1080x1920) + centered logo + text below
    # Get logo dimensions first
    probe_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json', str(logo_path)
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    import json as json_lib
    logo_info = json_lib.loads(result.stdout)
    logo_width = logo_info['streams'][0]['width']
    logo_height = logo_info['streams'][0]['height']

    # Filter complex: black background + scaled logo + text
    filter_complex = (
        f"color=c=black:s={FINAL_VERTICAL_SIZE}:d={duration}:r=30[bg];"
        f"[1:v]scale='min(800,iw)':'min(800,ih)':force_original_aspect_ratio=decrease[logo];"
        f"[bg][logo]overlay=(W-w)/2:(H-h)/2-100[v1];"  # Logo slightly above center
        f"[v1]drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
        f"text='{social_handle}':"
        f"fontcolor=white:fontsize=56:x=(w-text_w)/2:y=(h+200)/2+100[v]"  # Text below logo
    )

    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'color=c=black:s={FINAL_VERTICAL_SIZE}:d={duration}:r=30',
        '-i', str(logo_path),
        '-filter_complex', filter_complex,
        '-map', '[v]',
        '-c:v', 'libx264',
        '-t', str(duration),
        '-pix_fmt', 'yuv420p',
        '-an',  # No audio
        str(output_path), '-loglevel', 'error'
    ]

    subprocess.run(cmd, check=True)
    return output_path


def concatenate_scenes(scene_videos: List[Path], output_path: Path, add_ending: bool = True):
    """
    Concatenate multiple scene videos into one short, optionally adding ending.

    Args:
        scene_videos: List of scene video paths
        output_path: Where to save final short
        add_ending: Whether to add 10-second ending with logo and handle
    """
    print(f"\n    🔗 Concatenating {len(scene_videos)} scenes...")

    # Create ending segment if requested
    ending_video = None
    if add_ending:
        print(f"       Creating 10-second ending segment...")
        ending_video = output_path.parent / "ending_segment.mp4"
        create_ending_segment(ending_video, duration=10.0)
        print(f"       ✓ Ending segment created")

    # Create file list for ffmpeg
    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, 'w') as f:
        for video in scene_videos:
            f.write(f"file '{video.absolute()}'\n")
        if ending_video:
            f.write(f"file '{ending_video.absolute()}'\n")

    # Concatenate using ffmpeg
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
        '-c', 'copy', str(output_path), '-y', '-loglevel', 'error'
    ]
    subprocess.run(cmd, check=True)

    # Clean up
    list_file.unlink()

    print(f"       ✓ Short video created: {output_path.name}"
          f" ({len(scene_videos)} scenes" + (" + ending)" if add_ending else ")"))


def process_audiobook(
    audiobook_path: Path,
    audio_dir: Path,
    video_dir: Path,
    client: OpenAIClient
) -> int:
    """
    Generate promotional videos for all shorts in audiobook.

    Returns:
        Number of shorts processed
    """
    # Load audiobook with timing data
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"🎬 Promotional Video Generation (VERTICAL FORMAT)")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    print(f"Chapters: {len(audiobook['chapters'])}")
    print(f"Video format: {FINAL_VERTICAL_SIZE} (portrait)")
    print(f"Output: {video_dir}")
    print(f"{'='*80}\n")

    total_shorts = 0
    total_start = time.time()

    for chapter in audiobook['chapters']:
        chapter_num = chapter['chapter_number']
        promotional_shorts = chapter.get('promotional_shorts', [])

        if not promotional_shorts:
            continue

        print(f"\n📖 Chapter {chapter_num}: {chapter['title']}")

        for short in promotional_shorts:
            short_id = short['short_id']
            short_name = short['name']

            print(f"\n  🎬 Short {short_id}: {short_name}")

            scene_videos = []

            try:
                # Process each scene
                for scene in short['scenes']:
                    scene_video = process_scene(
                        scene=scene,
                        chapter_num=chapter_num,
                        short_id=short_id,
                        audio_dir=audio_dir,
                        video_dir=video_dir,
                        client=client
                    )
                    scene_videos.append(scene_video)

                # Concatenate scenes into final short
                final_short = video_dir / f"chapter_{chapter_num:02d}" / f"{short_name.replace(' ', '_')}_SHORT.mp4"
                concatenate_scenes(scene_videos, final_short)

                total_shorts += 1

            except Exception as e:
                print(f"  ✗ Short {short_id} failed: {e}")
                short['error'] = str(e)

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n{'='*80}")
    print(f"✅ Video Generation Complete")
    print(f"{'='*80}")
    print(f"Total shorts generated: {total_shorts}")
    print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"\n📁 Videos saved to: {video_dir}")
    print(f"📐 Format: {FINAL_VERTICAL_SIZE} (portrait/vertical)")
    print(f"{'='*80}\n")

    return total_shorts


def main():
    """Generate promotional videos for audiobook"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate promotional videos for audiobook shorts (VERTICAL format)')
    parser.add_argument('audiobook_json', help='Path to audiobook_with_timing.json file')
    parser.add_argument('--audio-dir', help='Directory with promotional audio files (default: same dir as JSON + /promo_audio)')
    parser.add_argument('--video-dir', help='Output directory for videos (default: same dir as JSON + /promo_videos)')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPEN_AI_API env var)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or OPENAI_API_KEY
    if not api_key:
        print("Error: No API key provided. Use --api-key or set OPEN_AI_API environment variable")
        return 1

    # Load audiobook
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine directories
    if args.audio_dir:
        audio_dir = Path(args.audio_dir)
    else:
        audio_dir = audiobook_path.parent / "promo_audio"

    if args.video_dir:
        video_dir = Path(args.video_dir)
    else:
        video_dir = audiobook_path.parent / "promo_videos"

    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        print("Run generate_promotional_audio.py first!")
        return 1

    # Create OpenAI client
    client = OpenAIClient(api_key=api_key)

    # Process audiobook
    num_shorts = process_audiobook(
        audiobook_path=audiobook_path,
        audio_dir=audio_dir,
        video_dir=video_dir,
        client=client
    )

    return 0 if num_shorts > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
