#!/usr/bin/env python3
"""
Create an opening segment for Animal Farm episodes.
Usage: python scripts/create_episode_opening.py --episode-number 1 --output opening.mp4
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
import requests
import json

def generate_opening_audio(episode_number: int, voice_id: str, api_key: str, output_path: Path):
    """Generate opening narration using ElevenLabs."""

    # Convert episode number to word
    episode_words = {
        1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
        6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"
    }

    episode_word = episode_words.get(episode_number, str(episode_number))
    text = f"Animal Farm by George Orwell. Episode {episode_word}. Narrated by Wormhole Podcast."

    print(f"Generating opening audio...")
    print(f"  Text: {text}")
    print(f"  Voice ID: {voice_id}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    # Save MP3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(response.content)

    print(f"  ✓ Audio saved: {output_path}")

    # Get duration
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)],
        capture_output=True,
        text=True
    )

    duration = float(result.stdout.strip())
    print(f"  ✓ Duration: {duration:.2f}s")

    return duration

def create_opening_video(
    logo_path: Path,
    audio_path: Path,
    output_path: Path,
    audio_duration: float,
    silence_duration: float = 2.0
):
    """Create opening video with logo/black background and audio."""

    total_duration = audio_duration + silence_duration

    # Check if logo exists and get dimensions
    if logo_path and logo_path.exists():
        # Get logo dimensions
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height',
             '-of', 'json', str(logo_path)],
            capture_output=True,
            text=True
        )

        info = json.loads(result.stdout)
        logo_width = info['streams'][0]['width']
        logo_height = info['streams'][0]['height']

        print(f"Logo dimensions: {logo_width}x{logo_height}")

        # Create video with logo centered on black background (1280x720)
        # Scale logo to fit if needed
        filter_complex = (
            f"color=c=black:s=1280x720:d={total_duration}:r=30[bg];"
            f"[1:v]scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease[logo];"
            f"[bg][logo]overlay=(W-w)/2:(H-h)/2[v]"
        )

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={total_duration}:r=30',
            '-i', str(logo_path),
            '-i', str(audio_path),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-map', '2:a',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-t', str(total_duration),
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
    else:
        # No logo - just black background
        print("No logo found, using black background")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={total_duration}:r=30',
            '-i', str(audio_path),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]

    print(f"Creating opening video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise Exception("Failed to create opening video")

    print(f"  ✓ Opening video created: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Create episode opening segment')
    parser.add_argument('--episode-number', type=int, required=True,
                        help='Episode number (1-10)')
    parser.add_argument('--output', type=str, required=True,
                        help='Output video path')
    parser.add_argument('--voice-id', type=str,
                        default='ePiPWpzcHZrcqRzFrgQg',
                        help='ElevenLabs voice ID')
    parser.add_argument('--logo', type=str,
                        help='Path to logo image (optional)')
    parser.add_argument('--silence-duration', type=float, default=2.0,
                        help='Silence duration after audio (seconds)')

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable not set")
        sys.exit(1)

    output_path = Path(args.output)
    audio_path = output_path.parent / f"{output_path.stem}_audio.mp3"
    logo_path = Path(args.logo) if args.logo else None

    # Generate audio
    duration = generate_opening_audio(
        args.episode_number,
        args.voice_id,
        api_key,
        audio_path
    )

    # Create video
    create_opening_video(
        logo_path,
        audio_path,
        output_path,
        duration,
        args.silence_duration
    )

    print(f"\n✓ Opening segment complete: {output_path}")
    print(f"  Total duration: {duration + args.silence_duration:.2f}s")

if __name__ == '__main__':
    main()
