#!/usr/bin/env python3
"""
Coqui TTS Audio Generator - Local open-source TTS.

Uses Coqui TTS (VITS model) for local text-to-speech generation.
Much cheaper than ElevenLabs (free!) but requires local compute.

Usage:
    python src/generators/coqui_audio_generator.py "Text to speak" output.mp3
    python src/generators/coqui_audio_generator.py --file input.txt output.mp3
"""

import os
import sys
import time
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

# Default model - VITS is fast and good quality
DEFAULT_MODEL = "tts_models/en/ljspeech/vits"


class CoquiAudioGenerator:
    """Generate audio using Coqui TTS."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize Coqui TTS generator.

        Args:
            model_name: Coqui TTS model name
        """
        self.model_name = model_name
        self.tts = None
        self._load_model()

    def _load_model(self):
        """Load the TTS model."""
        try:
            from TTS.api import TTS
            print(f"Loading Coqui TTS model: {self.model_name}")
            self.tts = TTS(model_name=self.model_name, progress_bar=False)
            print("✓ Model loaded")
        except Exception as e:
            raise RuntimeError(f"Failed to load Coqui TTS model: {e}")

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        speed: float = 1.0
    ) -> float:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            output_path: Output file path (.mp3 or .wav)
            speed: Speech speed multiplier (not supported by all models)

        Returns:
            Duration of generated audio in seconds
        """
        output_path = Path(output_path)
        start_time = time.time()

        # Generate to WAV first (Coqui outputs WAV)
        if output_path.suffix.lower() == '.mp3':
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                wav_path = Path(tmp.name)
        else:
            wav_path = output_path

        try:
            # Generate audio
            self.tts.tts_to_file(text=text, file_path=str(wav_path))

            # Convert to MP3 if needed
            if output_path.suffix.lower() == '.mp3':
                self._convert_to_mp3(wav_path, output_path)
                wav_path.unlink()  # Clean up temp WAV

            # Get duration
            duration = self._get_audio_duration(output_path)
            elapsed = time.time() - start_time

            return duration

        except Exception as e:
            if wav_path.exists() and wav_path != output_path:
                wav_path.unlink()
            raise RuntimeError(f"Audio generation failed: {e}")

    def _convert_to_mp3(self, wav_path: Path, mp3_path: Path):
        """Convert WAV to MP3 using ffmpeg."""
        cmd = [
            'ffmpeg', '-y',
            '-i', str(wav_path),
            '-codec:a', 'libmp3lame',
            '-qscale:a', '2',
            str(mp3_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

    def _get_audio_duration(self, audio_path: Path) -> float:
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

    def generate_long_audio(
        self,
        text: str,
        output_path: Path,
        chunk_size: int = 500
    ) -> float:
        """
        Generate audio from long text by chunking.

        Args:
            text: Long text to synthesize
            output_path: Output file path
            chunk_size: Max characters per chunk

        Returns:
            Total duration in seconds
        """
        import re

        output_path = Path(output_path)

        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        # Group sentences into chunks
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        if current_chunk:
            chunks.append(current_chunk)

        if not chunks:
            chunks = [text]

        print(f"Processing {len(chunks)} chunks...")

        # Generate audio for each chunk
        temp_files = []
        total_duration = 0

        try:
            for i, chunk in enumerate(chunks):
                print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    temp_path = Path(tmp.name)

                self.tts.tts_to_file(text=chunk, file_path=str(temp_path))
                temp_files.append(temp_path)
                total_duration += self._get_audio_duration(temp_path)

            # Concatenate all chunks
            self._concatenate_audio(temp_files, output_path)

            return self._get_audio_duration(output_path)

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def _concatenate_audio(self, audio_files: list, output_path: Path):
        """Concatenate multiple audio files."""
        output_path = Path(output_path)

        # Create concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")
            concat_file = Path(f.name)

        try:
            # Determine output format
            if output_path.suffix.lower() == '.mp3':
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-codec:a', 'libmp3lame',
                    '-qscale:a', '2',
                    str(output_path)
                ]
            else:
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
                raise RuntimeError(f"Concatenation failed: {result.stderr}")

        finally:
            concat_file.unlink()


def main():
    parser = argparse.ArgumentParser(
        description='Generate audio using Coqui TTS (local, free)'
    )
    parser.add_argument(
        'text',
        nargs='?',
        help='Text to synthesize'
    )
    parser.add_argument(
        'output',
        help='Output file path (.mp3 or .wav)'
    )
    parser.add_argument(
        '--file', '-f',
        help='Read text from file instead of argument'
    )
    parser.add_argument(
        '--model', '-m',
        default=DEFAULT_MODEL,
        help=f'Coqui TTS model (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '--chunk-size', '-c',
        type=int,
        default=500,
        help='Max characters per chunk for long text (default: 500)'
    )

    args = parser.parse_args()

    # Get text
    if args.file:
        with open(args.file, 'r') as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        print("Error: Provide text or --file")
        sys.exit(1)

    # Generate audio
    generator = CoquiAudioGenerator(model_name=args.model)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    word_count = len(text.split())
    print(f"\nGenerating audio for {word_count} words...")
    start_time = time.time()

    if len(text) > 1000:
        duration = generator.generate_long_audio(text, output_path, args.chunk_size)
    else:
        duration = generator.generate_audio(text, output_path)

    elapsed = time.time() - start_time

    print(f"\n✓ Audio generated: {output_path}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Processing time: {elapsed:.1f}s")
    print(f"  Words: {word_count}")
    print(f"  Time per 1000 words: {elapsed / word_count * 1000:.1f}s")


if __name__ == '__main__':
    main()
