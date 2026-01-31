#!/usr/bin/env python3
"""
Generate audio for audiobook episodes using ElevenLabs.

Reads audiobook.json and generates one MP3 file per episode.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.secrets')

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_KEY")
VOICE_ID = "ePiPWpzcHZrcqRzFrgQg"  # User-specified voice
MODEL_ID = "eleven_v3"  # Required for emotion tags


def split_text_into_chunks(text: str, max_chars: int = 4800) -> List[str]:
    """
    Split text into chunks that fit within ElevenLabs character limit.

    Tries to split on sentence boundaries to maintain natural flow.
    """
    # Split on sentence boundaries
    sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence would exceed limit, save current chunk
        if len(current_chunk) + len(sentence) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def generate_episode_audio(
    episode: Dict,
    book_title: str,
    output_dir: Path,
    voice_id: str,
    api_key: str
) -> float:
    """
    Generate audio for a single episode.

    Args:
        episode: Episode dictionary with chapters
        book_title: Book title for filename
        output_dir: Directory to save MP3 file
        voice_id: ElevenLabs voice ID
        api_key: ElevenLabs API key

    Returns:
        Duration in seconds
    """
    episode_num = episode['episode_number']

    # Combine all chapter narrated text
    narrated_parts = []
    for chapter in episode['chapters']:
        # Add chapter title as spoken introduction
        chapter_title = chapter['title']
        narrated_parts.append(f"[calm] {chapter_title}.")
        narrated_parts.append(chapter['narrated_text'])

    full_text = " ".join(narrated_parts)

    # Split text into chunks to fit ElevenLabs limit (5000 chars)
    text_chunks = split_text_into_chunks(full_text, max_chars=4800)

    # Create filename
    # Clean book title for filename
    clean_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_title = clean_title.replace(' ', '_').lower()

    output_path = output_dir / f"{clean_title}_episode_{episode_num:02d}.mp3"

    # Skip if already exists
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"  ⏭️  Episode {episode_num}: Already exists, skipping")
        return 0.0

    print(f"\n🎙️  Generating Episode {episode_num}...")
    print(f"  Estimated duration: {episode['estimated_minutes']} minutes")
    print(f"  Chapters: {[c['chapter_number'] for c in episode['chapters']]}")
    print(f"  Total words: {episode['total_words']:,}")
    print(f"  Text chunks: {len(text_chunks)}")

    # Generate audio for each chunk
    api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_files = []

    try:
        start_time = time.time()

        # Generate audio for each chunk
        for i, text_chunk in enumerate(text_chunks, 1):
            print(f"    Chunk {i}/{len(text_chunks)} ({len(text_chunk)} chars)...")

            payload = {
                "text": text_chunk,
                "model_id": MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=1200  # 20 minutes for large chunks
            )

            if response.status_code != 200:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get('detail', {}).get('message', error_text)
                except:
                    error_msg = error_text
                raise Exception(f"API Error (status {response.status_code}): {error_msg}")

            # Save chunk audio
            chunk_path = output_dir / f"temp_ep{episode_num}_chunk{i:03d}.mp3"
            audio_bytes = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    audio_bytes += chunk

            with open(chunk_path, 'wb') as f:
                f.write(audio_bytes)

            chunk_files.append(chunk_path)

        # Concatenate all chunks using ffmpeg
        print(f"    Concatenating {len(chunk_files)} chunks...")

        # Create file list for ffmpeg
        list_file = output_dir / f"temp_ep{episode_num}_list.txt"
        with open(list_file, 'w') as f:
            for chunk_file in chunk_files:
                f.write(f"file '{chunk_file.name}'\n")

        # Use ffmpeg to concatenate
        import subprocess
        subprocess.run([
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
            '-c', 'copy', str(output_path), '-y'
        ], capture_output=True, check=True)

        # Clean up temporary files
        list_file.unlink()
        for chunk_file in chunk_files:
            chunk_file.unlink()

        elapsed = time.time() - start_time
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"  ✓ Episode {episode_num}: Generated in {elapsed:.1f}s")
        print(f"  📁 Saved: {output_path.name}")
        print(f"  📊 Size: {file_size_mb:.2f} MB")

        return elapsed

    except requests.exceptions.Timeout:
        raise Exception(f"Episode {episode_num}: Request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Episode {episode_num}: Network error: {e}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Episode {episode_num}: ffmpeg concatenation failed: {e.stderr}")
    except Exception as e:
        # Clean up temp files on error
        for chunk_file in chunk_files:
            if chunk_file.exists():
                chunk_file.unlink()
        raise


def main():
    """Generate audio for all episodes in an audiobook"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate audio for audiobook episodes using ElevenLabs')
    parser.add_argument('audiobook_json', help='Path to audiobook.json file')
    parser.add_argument('--output-dir', help='Output directory for MP3 files (default: same as JSON)')
    parser.add_argument('--voice-id', default=VOICE_ID, help=f'ElevenLabs voice ID (default: {VOICE_ID})')
    parser.add_argument('--api-key', help='ElevenLabs API key (or set ELEVEN_LABS_KEY env var)')

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or ELEVENLABS_API_KEY
    if not api_key:
        print("Error: No API key provided. Use --api-key or set ELEVEN_LABS_KEY environment variable")
        return 1

    # Load audiobook JSON
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    with open(audiobook_path) as f:
        audiobook = json.load(f)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = audiobook_path.parent / "episode_audio"

    # Print info
    print(f"\n{'='*60}")
    print(f"🎧 Audiobook Audio Generation")
    print(f"{'='*60}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    print(f"Episodes: {audiobook['stats']['total_episodes']}")
    print(f"Total estimated time: {audiobook['stats']['estimated_total_minutes']} minutes")
    print(f"Voice ID: {args.voice_id}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    # Generate audio for each episode
    total_start = time.time()
    successes = 0
    failures = []

    for episode in audiobook['episodes']:
        try:
            generate_episode_audio(
                episode=episode,
                book_title=audiobook['metadata']['title'],
                output_dir=output_dir,
                voice_id=args.voice_id,
                api_key=api_key
            )
            successes += 1
        except Exception as e:
            failures.append((episode['episode_number'], str(e)))
            print(f"  ✗ Episode {episode['episode_number']} failed: {e}")

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n{'='*60}")
    print(f"Generation Complete")
    print(f"{'='*60}")
    print(f"Total episodes: {len(audiobook['episodes'])}")
    print(f"Successful: {successes}")
    print(f"Failed: {len(failures)}")
    print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")

    if failures:
        print(f"\nErrors:")
        for ep_num, error in failures:
            print(f"  Episode {ep_num}: {error}")

    print(f"\n📁 Audio files saved to: {output_dir}")
    print(f"{'='*60}\n")

    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
