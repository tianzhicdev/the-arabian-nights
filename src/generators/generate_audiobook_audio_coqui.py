#!/usr/bin/env python3
"""
Generate audio for audiobook episodes using Coqui TTS (local, free).

Reads audiobook.json and generates one MP3 file per episode.
Uses local GPU/CPU instead of cloud API - much cheaper but may be slower.

Usage:
    python src/generators/generate_audiobook_audio_coqui.py audiobook.json
    python src/generators/generate_audiobook_audio_coqui.py audiobook.json --model tts_models/en/vctk/vits
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Default Coqui model - VITS is fast and good quality
DEFAULT_MODEL = "tts_models/en/ljspeech/vits"


def split_text_into_chunks(text: str, max_chars: int = 500) -> List[str]:
    """
    Split text into chunks for Coqui TTS.

    Coqui works better with smaller chunks than ElevenLabs.
    """
    import re

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def concatenate_audio_files(audio_files: List[Path], output_path: Path):
    """Concatenate multiple audio files into one MP3."""
    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")
        concat_file = Path(f.name)

    try:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-codec:a', 'libmp3lame',
            '-qscale:a', '2',
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    finally:
        concat_file.unlink()


def generate_episode_audio(
    episode: Dict,
    book_title: str,
    output_dir: Path,
    tts,
    model_name: str
) -> float:
    """
    Generate audio for a single episode using Coqui TTS.

    Args:
        episode: Episode dictionary with chapters
        book_title: Book title for filename
        output_dir: Directory to save MP3 file
        tts: Loaded TTS model
        model_name: Model name for logging

    Returns:
        Duration in seconds
    """
    episode_num = episode['episode_number']

    # Combine all chapter narrated text
    narrated_parts = []
    for chapter in episode['chapters']:
        chapter_title = chapter['title']
        # Remove emotion tags that ElevenLabs uses
        narrated_text = chapter['narrated_text']
        # Strip [emotion] tags
        import re
        narrated_text = re.sub(r'\[.*?\]', '', narrated_text)

        narrated_parts.append(f"{chapter_title}.")
        narrated_parts.append(narrated_text)

    full_text = " ".join(narrated_parts)

    # Create filename
    clean_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_title = clean_title.replace(' ', '_').lower()
    output_path = output_dir / f"{clean_title}_episode_{episode_num:02d}.mp3"

    # Skip if already exists
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"  ⏭️  Episode {episode_num}: Already exists, skipping")
        return get_audio_duration(output_path)

    print(f"\n🎙️  Generating Episode {episode_num} with Coqui TTS...")

    word_count = len(full_text.split())
    chapters = episode.get('chapters', [])
    print(f"  Chapters: {[c.get('chapter_number', i+1) for i, c in enumerate(chapters)]}")
    print(f"  Total words: {word_count:,}")

    start_time = time.time()

    # Split into chunks
    text_chunks = split_text_into_chunks(full_text, max_chars=500)
    print(f"  Text chunks: {len(text_chunks)}")

    # Generate audio for each chunk
    temp_files = []
    try:
        for i, chunk in enumerate(text_chunks):
            print(f"    Chunk {i+1}/{len(text_chunks)} ({len(chunk)} chars)...")

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_path = Path(tmp.name)

            tts.tts_to_file(text=chunk, file_path=str(temp_path))
            temp_files.append(temp_path)

        # Concatenate all chunks
        print(f"    Concatenating {len(temp_files)} chunks...")
        concatenate_audio_files(temp_files, output_path)

    finally:
        # Clean up temp files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()

    elapsed = time.time() - start_time
    duration = get_audio_duration(output_path)
    size_mb = output_path.stat().st_size / 1024 / 1024

    print(f"  ✓ Episode {episode_num}: Generated in {elapsed:.1f}s")
    print(f"  📁 Saved: {output_path.name}")
    print(f"  📊 Size: {size_mb:.2f} MB, Duration: {duration:.1f}s")
    print(f"  ⏱️  Time per 1000 words: {elapsed / word_count * 1000:.1f}s")

    return duration


def process_audiobook(
    audiobook_path: Path,
    output_dir: Path,
    model_name: str
) -> int:
    """
    Generate audio for all episodes in audiobook.

    Args:
        audiobook_path: Path to audiobook.json
        output_dir: Directory to save MP3 files
        model_name: Coqui TTS model name

    Returns:
        Number of episodes generated
    """
    # Load audiobook
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']
    episodes = audiobook.get('episodes', [])

    # Calculate total duration estimate
    total_words = sum(
        len(chapter.get('narrated_text', '').split())
        for episode in episodes
        for chapter in episode.get('chapters', [])
    )
    # Rough estimate: 150 words per minute
    est_minutes = total_words / 150

    print(f"\n{'='*60}")
    print(f"🎧 Audiobook Audio Generation (Coqui TTS)")
    print(f"{'='*60}")
    print(f"Book: {book_title}")
    print(f"Author: {author}")
    print(f"Episodes: {len(episodes)}")
    print(f"Total words: {total_words:,}")
    print(f"Estimated duration: {est_minutes:.1f} minutes")
    print(f"Model: {model_name}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    # Load TTS model once
    print(f"\nLoading Coqui TTS model...")
    from TTS.api import TTS
    tts = TTS(model_name=model_name, progress_bar=False)
    print(f"✓ Model loaded")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate each episode
    success_count = 0
    fail_count = 0
    total_duration = 0
    total_start = time.time()

    for episode in episodes:
        try:
            duration = generate_episode_audio(
                episode=episode,
                book_title=book_title,
                output_dir=output_dir,
                tts=tts,
                model_name=model_name
            )
            total_duration += duration
            success_count += 1
        except Exception as e:
            print(f"  ✗ Episode {episode['episode_number']}: {e}")
            fail_count += 1

    total_time = time.time() - total_start

    # Summary
    print(f"\n{'='*60}")
    print(f"Generation Complete")
    print(f"{'='*60}")
    print(f"Total episodes: {len(episodes)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Total audio duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"\n📁 Audio files saved to: {output_dir}")
    print(f"{'='*60}\n")

    return success_count


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate audiobook audio using Coqui TTS (local, free)'
    )
    parser.add_argument(
        'audiobook_json',
        help='Path to audiobook.json file'
    )
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for MP3 files (default: same dir + /episode_audio)'
    )
    parser.add_argument(
        '--model', '-m',
        default=DEFAULT_MODEL,
        help=f'Coqui TTS model (default: {DEFAULT_MODEL})'
    )

    args = parser.parse_args()

    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = audiobook_path.parent / "episode_audio"

    count = process_audiobook(audiobook_path, output_dir, args.model)
    return 0 if count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
