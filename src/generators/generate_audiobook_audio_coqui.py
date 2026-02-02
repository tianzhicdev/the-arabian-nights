#!/usr/bin/env python3
"""
Generate audio for audiobook episodes using Coqui TTS (local, free).

Reads audiobook.json and generates one MP3 file per episode.
Uses XTTS-v2 for high-quality voice cloning with reference audio.

Usage:
    python src/generators/generate_audiobook_audio_coqui.py audiobook.json --voice-ref voice.mp3
    python src/generators/generate_audiobook_audio_coqui.py audiobook.json --model tts_models/en/ljspeech/vits
"""

import os
import sys
import json
import re
import time
import tempfile
import subprocess
import numpy as np
import scipy.io.wavfile as wav
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Default model - XTTS-v2 for voice cloning, fallback to VITS
DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
FALLBACK_MODEL = "tts_models/en/ljspeech/vits"

# XTTS-v2 settings optimized for storytelling (tested 2026-02-01)
# Based on extensive quality testing - see experiments/xtts_quality_tests/XTTS_QUALITY_REPORT.md
XTTS_SETTINGS = {
    "temperature": 0.3,           # Low = deterministic, clear speech
    "repetition_penalty": 10.0,   # High = prevents loops/gibberish
    "top_p": 0.85,                # Nucleus sampling threshold
}

# Voice conditioning settings
GPT_COND_LEN = 24
GPT_COND_CHUNK_LEN = 6

# XTTS has 250 char limit - use 200 to be safe
MAX_CHUNK_CHARS = 200

# Pause duration between chunks (seconds)
CHUNK_PAUSE = 1.0


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS - remove unsupported characters that cause issues.

    Removes: # * ** *** markdown headers, emotion tags, etc.
    """
    # Remove emotion tags like [calm], [serious], etc.
    text = re.sub(r'\[.*?\]', '', text)

    # Remove markdown headers (# ## ### etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove markdown bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)

    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove standalone # symbols
    text = re.sub(r'(?<!\w)#(?!\w)', '', text)

    # Remove em-dashes and replace with commas for better pacing
    text = text.replace('—', ', ')
    text = text.replace('--', ', ')

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Clean up multiple punctuation
    text = re.sub(r'[,;:]{2,}', ',', text)

    return text.strip()


def split_into_chunks(text: str, max_chars: int = 200) -> List[str]:
    """
    Split text into chunks that respect the XTTS 250 character limit.
    Tries to split at sentence boundaries first, then at clause boundaries.
    """
    # First split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If sentence itself is too long, split it further at commas/semicolons
        if len(sentence) > max_chars:
            parts = re.split(r'(?<=[,;])\s+', sentence)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if len(current_chunk) + len(part) + 1 <= max_chars:
                    current_chunk = (current_chunk + " " + part).strip() if current_chunk else part
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    # If part is still too long, just take it (will be truncated by model)
                    current_chunk = part[:max_chars] if len(part) > max_chars else part
        else:
            # Normal case: sentence fits
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]


def trim_silence(audio: np.ndarray, threshold: float = 0.01, min_samples: int = 1000) -> np.ndarray:
    """Trim silence from ends of audio to reduce gaps."""
    above_threshold = np.abs(audio) > threshold
    if not np.any(above_threshold):
        return audio
    nonzero = np.where(above_threshold)[0]
    start = max(0, nonzero[0] - min_samples)
    end = min(len(audio), nonzero[-1] + min_samples)
    return audio[start:end]


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


def create_silence(duration: float, sample_rate: int = 24000) -> np.ndarray:
    """Create silence array for pauses between sentences."""
    return np.zeros(int(duration * sample_rate), dtype=np.float32)


def apply_ffmpeg_enhance(input_path: Path, output_path: Path) -> bool:
    """Apply FFmpeg audio enhancement filters (EQ, compression, normalization)."""
    filter_chain = ','.join([
        'afftdn=nf=-25:nr=12:nt=w',           # FFT denoiser
        'highpass=f=80,lowpass=f=8000',        # Voice frequency isolation
        'agate=threshold=0.01:attack=20:release=200:ratio=2',  # Noise gate
        'acompressor=threshold=-20dB:ratio=4:attack=5:release=50',  # Compression
        'loudnorm=I=-16:TP=-1.5:LRA=11',      # Loudness normalization
    ])

    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-af', filter_chain,
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def generate_episode_audio_xtts(
    episode: Dict,
    book_title: str,
    output_dir: Path,
    model,
    gpt_cond_latent,
    speaker_embedding,
    post_process: bool = True,
) -> float:
    """
    Generate audio for a single episode using XTTS-v2.

    Uses optimized settings from quality testing:
    - temperature=0.3, repetition_penalty=10.0
    - 200 char chunks to avoid truncation
    - Trim silence between chunks
    - FFmpeg post-processing for better quality
    """
    episode_num = episode['episode_number']

    # Combine all chapter narrated text
    narrated_parts = []
    for chapter in episode['chapters']:
        chapter_title = chapter['title']
        narrated_text = chapter['narrated_text']
        narrated_parts.append(f"{chapter_title}.")
        narrated_parts.append(narrated_text)

    full_text = " ".join(narrated_parts)

    # Clean text for TTS
    full_text = clean_text_for_tts(full_text)

    # Create filename
    clean_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_title = clean_title.replace(' ', '_').lower()
    output_path = output_dir / f"{clean_title}_episode_{episode_num:02d}.mp3"

    # Skip if already exists
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"  Episode {episode_num}: Already exists, skipping", flush=True)
        return get_audio_duration(output_path)

    print(f"\n  Generating Episode {episode_num} with XTTS-v2...", flush=True)

    word_count = len(full_text.split())
    chapters = episode.get('chapters', [])
    print(f"  Chapters: {[c.get('chapter_number', i+1) for i, c in enumerate(chapters)]}", flush=True)
    print(f"  Total words: {word_count:,}", flush=True)

    start_time = time.time()

    # Split into chunks (200 char max to avoid XTTS truncation)
    chunks = split_into_chunks(full_text, MAX_CHUNK_CHARS)
    print(f"  Chunks: {len(chunks)} (max {MAX_CHUNK_CHARS} chars)", flush=True)

    # Generate audio for each chunk with pauses
    audio_parts = []
    silence = create_silence(CHUNK_PAUSE)

    for i, chunk in enumerate(chunks):
        progress = (i + 1) / len(chunks) * 100
        if i % 20 == 0 or i == len(chunks) - 1:
            print(f"    [{i+1}/{len(chunks)}] ({progress:.1f}%) {chunk[:40]}...", flush=True)

        try:
            out = model.inference(
                chunk,
                "en",
                gpt_cond_latent,
                speaker_embedding,
                **XTTS_SETTINGS
            )
            # Trim silence from chunk to reduce gaps
            audio = trim_silence(out["wav"])
            audio_parts.append(audio)

            # Add pause after chunk (except last one)
            if i < len(chunks) - 1:
                audio_parts.append(silence)
        except Exception as e:
            print(f"    ERROR on chunk {i+1}: {e}", flush=True)
            continue

    if not audio_parts:
        print(f"  ERROR: No audio generated for episode {episode_num}", flush=True)
        return 0.0

    # Concatenate all audio
    print(f"    Concatenating {len(audio_parts)} parts...", flush=True)
    full_audio = np.concatenate(audio_parts)

    # Save as WAV then convert to MP3
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = Path(tmp.name)

    wav.write(str(wav_path), 24000, full_audio)

    # Convert to MP3 (with or without enhancement)
    if post_process:
        print(f"    Post-processing (EQ, compression, normalize)...", flush=True)
        # First convert to MP3
        raw_mp3 = output_path.with_stem(output_path.stem + '_raw')
        subprocess.run([
            'ffmpeg', '-y', '-i', str(wav_path),
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            str(raw_mp3)
        ], capture_output=True)

        # Apply enhancement
        if apply_ffmpeg_enhance(raw_mp3, output_path):
            raw_mp3.unlink()
        else:
            # Fallback to raw if enhancement fails
            raw_mp3.rename(output_path)
    else:
        subprocess.run([
            'ffmpeg', '-y', '-i', str(wav_path),
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            str(output_path)
        ], capture_output=True)

    wav_path.unlink()

    elapsed = time.time() - start_time
    duration = get_audio_duration(output_path)
    size_mb = output_path.stat().st_size / 1024 / 1024

    print(f"  Episode {episode_num}: Generated in {elapsed:.1f}s", flush=True)
    print(f"  Saved: {output_path.name}", flush=True)
    print(f"  Size: {size_mb:.2f} MB, Duration: {duration:.1f}s ({duration/60:.1f} min)", flush=True)

    return duration


def generate_episode_audio(
    episode: Dict,
    book_title: str,
    output_dir: Path,
    tts,
    model_name: str
) -> float:
    """
    Generate audio for a single episode using basic Coqui TTS (non-XTTS).

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
        narrated_text = chapter['narrated_text']
        narrated_parts.append(f"{chapter_title}.")
        narrated_parts.append(narrated_text)

    full_text = " ".join(narrated_parts)

    # Clean text for TTS
    full_text = clean_text_for_tts(full_text)

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
    model_name: str,
    voice_ref: Optional[Path] = None
) -> int:
    """
    Generate audio for all episodes in audiobook.

    Args:
        audiobook_path: Path to audiobook.json
        output_dir: Directory to save MP3 files
        model_name: Coqui TTS model name
        voice_ref: Optional voice reference for XTTS-v2

    Returns:
        Number of episodes generated
    """
    import torch

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

    use_xtts = voice_ref is not None and "xtts" in model_name.lower()

    print(f"\n{'='*60}")
    print(f"🎧 Audiobook Audio Generation (Coqui TTS)")
    print(f"{'='*60}")
    print(f"Book: {book_title}")
    print(f"Author: {author}")
    print(f"Episodes: {len(episodes)}")
    print(f"Total words: {total_words:,}")
    print(f"Estimated duration: {est_minutes:.1f} minutes")
    print(f"Model: {model_name}")
    if voice_ref:
        print(f"Voice reference: {voice_ref}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model
    if use_xtts:
        print(f"\nLoading XTTS-v2 model...")
        from TTS.tts.configs.xtts_config import XttsConfig
        from TTS.tts.models.xtts import Xtts

        model_dir = Path.home() / "Library/Application Support/tts/tts_models--multilingual--multi-dataset--xtts_v2"
        config = XttsConfig()
        config.load_json(str(model_dir / "config.json"))
        model = Xtts.init_from_config(config)
        model.load_checkpoint(config, checkpoint_dir=str(model_dir), eval=True)

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Using device: {device}")
        model = model.to(device)

        print(f"Getting voice conditioning from: {voice_ref}")
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[str(voice_ref)],
            gpt_cond_len=GPT_COND_LEN,
            gpt_cond_chunk_len=GPT_COND_CHUNK_LEN,
        )
        print(f"Model loaded with voice cloning (gpt_cond_len={GPT_COND_LEN})")
        tts = None
    else:
        print(f"\nLoading Coqui TTS model...")
        from TTS.api import TTS
        tts = TTS(model_name=model_name, progress_bar=False)
        print(f"✓ Model loaded")
        model = None
        gpt_cond_latent = None
        speaker_embedding = None

    # Generate each episode
    success_count = 0
    fail_count = 0
    total_duration = 0
    total_start = time.time()

    for episode in episodes:
        try:
            if use_xtts:
                duration = generate_episode_audio_xtts(
                    episode=episode,
                    book_title=book_title,
                    output_dir=output_dir,
                    model=model,
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                )
            else:
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
            import traceback
            print(f"  ✗ Episode {episode['episode_number']}: {e}")
            traceback.print_exc()
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
    parser.add_argument(
        '--voice-ref', '-v',
        help='Voice reference audio file for XTTS-v2 voice cloning'
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

    # Voice reference
    voice_ref = Path(args.voice_ref) if args.voice_ref else None
    if voice_ref and not voice_ref.exists():
        print(f"Error: Voice reference file not found: {voice_ref}")
        return 1

    count = process_audiobook(audiobook_path, output_dir, args.model, voice_ref)
    return 0 if count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
