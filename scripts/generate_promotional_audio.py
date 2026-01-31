#!/usr/bin/env python3
"""
Generate TTS audio for promotional shorts and calculate video timing.

Workflow:
1. Read audiobook.json with promotional_shorts
2. For each scene in each short:
   - Generate ElevenLabs TTS audio
   - Measure actual audio duration with ffprobe
   - Calculate required Sora duration (4, 8, or 12s)
   - Calculate silence padding needed
3. Update JSON with timing data
4. Save audio files organized by chapter/short/scene
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.secrets')

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_KEY")
VOICE_ID = "ePiPWpzcHZrcqRzFrgQg"  # Default voice
MODEL_ID = "eleven_v3"  # Required for emotion tags
SORA_DURATIONS = [4, 8, 12]  # Valid Sora video durations in seconds


def get_audio_duration(audio_path: Path) -> float:
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


def pick_sora_duration(audio_duration: float) -> int:
    """Pick the smallest Sora duration that is >= audio duration"""
    for sora_duration in SORA_DURATIONS:
        if sora_duration >= audio_duration:
            return sora_duration

    # If audio is longer than 12 seconds, return 12 (will need to trim or split)
    return SORA_DURATIONS[-1]


def generate_scene_audio(
    scene: Dict,
    output_path: Path,
    voice_id: str,
    api_key: str
) -> Dict:
    """
    Generate audio for a promotional scene.

    Returns:
        Dictionary with audio_duration, sora_duration, silence_padding
    """
    # Skip if file already exists
    if output_path.exists() and output_path.stat().st_size > 0:
        duration = get_audio_duration(output_path)
        sora_duration = pick_sora_duration(duration)
        silence_padding = sora_duration - duration

        print(f"    ⏭️  Scene {scene['scene_id']}: {duration:.2f}s (exists, using {sora_duration}s Sora)")

        return {
            "audio_duration": round(duration, 2),
            "sora_duration": sora_duration,
            "silence_padding": round(silence_padding, 2),
            "audio_file": str(output_path.name)
        }

    # Generate audio
    text = scene['promotional_narrated_text']

    print(f"    🎙️  Scene {scene['scene_id']}: Generating audio...")
    print(f"       Text: {text[:60]}{'...' if len(text) > 60 else ''}")

    api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        start_time = time.time()
        response = requests.post(
            api_url,
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

        # Measure duration
        duration = get_audio_duration(output_path)
        sora_duration = pick_sora_duration(duration)
        silence_padding = sora_duration - duration
        elapsed = time.time() - start_time

        print(f"       ✓ Generated in {elapsed:.1f}s: {duration:.2f}s audio → {sora_duration}s Sora (pad {silence_padding:.2f}s)")

        return {
            "audio_duration": round(duration, 2),
            "sora_duration": sora_duration,
            "silence_padding": round(silence_padding, 2),
            "audio_file": str(output_path.name)
        }

    except requests.exceptions.Timeout:
        raise Exception(f"Scene {scene['scene_id']}: Request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Scene {scene['scene_id']}: Network error: {e}")


def process_audiobook(
    audiobook_path: Path,
    output_dir: Path,
    voice_id: str,
    api_key: str
) -> int:
    """
    Generate promotional audio for all shorts in audiobook.

    Returns:
        Number of scenes processed
    """
    # Load audiobook JSON
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"🎙️  Promotional Audio Generation")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    print(f"Chapters: {len(audiobook['chapters'])}")
    print(f"Voice ID: {voice_id}")
    print(f"Output: {output_dir}")
    print(f"{'='*80}\n")

    # Process each chapter's promotional shorts
    total_scenes = 0
    total_start = time.time()

    for chapter in audiobook['chapters']:
        chapter_num = chapter['chapter_number']
        promotional_shorts = chapter.get('promotional_shorts', [])

        if not promotional_shorts:
            print(f"\nChapter {chapter_num}: No promotional shorts, skipping")
            continue

        print(f"\n📖 Chapter {chapter_num}: {chapter['title']}")
        print(f"   Promotional shorts: {len(promotional_shorts)}")

        for short_idx, short in enumerate(promotional_shorts, start=1):
            short_id = short_idx  # Use array index as short_id
            short_name = short['name']

            print(f"\n  🎬 Short {short_id}: {short_name}")
            print(f"     Scenes: {len(short['scenes'])}")

            for scene in short['scenes']:
                scene_id = scene['scene_id']

                # Create output path: chapter_XX/short_YY/scene_ZZ.mp3
                scene_path = output_dir / f"chapter_{chapter_num:02d}" / f"short_{short_id:02d}" / f"scene_{scene_id:02d}.mp3"

                try:
                    timing_data = generate_scene_audio(
                        scene=scene,
                        output_path=scene_path,
                        voice_id=voice_id,
                        api_key=api_key
                    )

                    # Update scene with timing data
                    scene.update(timing_data)
                    total_scenes += 1

                except Exception as e:
                    print(f"    ✗ Scene {scene_id} failed: {e}")
                    scene['error'] = str(e)

    total_elapsed = time.time() - total_start

    # Save updated JSON
    output_json = audiobook_path.parent / "audiobook_with_timing.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(audiobook, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*80}")
    print(f"✅ Generation Complete")
    print(f"{'='*80}")
    print(f"Total scenes processed: {total_scenes}")
    print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"Average time per scene: {total_elapsed/total_scenes:.1f}s" if total_scenes > 0 else "")
    print(f"\n📁 Audio files: {output_dir}")
    print(f"📄 Updated JSON: {output_json}")
    print(f"{'='*80}\n")

    return total_scenes


def main():
    """Generate promotional audio for audiobook"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate promotional audio for audiobook shorts')
    parser.add_argument('audiobook_json', help='Path to audiobook.json file')
    parser.add_argument('--output-dir', help='Output directory for audio files (default: same dir as JSON + /promo_audio)')
    parser.add_argument('--voice-id', default=VOICE_ID, help=f'ElevenLabs voice ID (default: {VOICE_ID})')
    parser.add_argument('--api-key', help='ElevenLabs API key (or set ELEVEN_LABS_KEY env var)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or ELEVENLABS_API_KEY
    if not api_key:
        print("Error: No API key provided. Use --api-key or set ELEVEN_LABS_KEY environment variable")
        return 1

    # Load audiobook
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = audiobook_path.parent / "promo_audio"

    # Process audiobook
    num_scenes = process_audiobook(
        audiobook_path=audiobook_path,
        output_dir=output_dir,
        voice_id=args.voice_id,
        api_key=api_key
    )

    return 0 if num_scenes > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
