#!/usr/bin/env python3
"""
ElevenLabs Text-to-Dialogue Generator
Converts dialogue text files to MP3 audio using the text-to-dialogue API
Handles large files by chunking and combining
"""

import os
import re
import sys
import json
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from project root
project_root_env = Path(__file__).parent.parent
load_dotenv(project_root_env / ".env.secrets")

# Configuration
API_KEY = os.getenv("ELEVEN_LABS_KEY")
if not API_KEY:
    print("ERROR: ELEVEN_LABS_KEY not found in .env.secrets")
    sys.exit(1)

# Voice IDs for different characters
# Using custom ElevenLabs voices
VOICES = {
    # Art of War dialogue
    "Napoleon": "2h7ex7B1yGrkcLFI8zUO",
    "Sun Tzu": "p9KVucfSoJI7y6G681mZ",
    # Meditations dialogue
    "Freud": "2h7ex7B1yGrkcLFI8zUO",  # Analytical, professorial
    "Marcus Aurelius": "p9KVucfSoJI7y6G681mZ",  # Calm, wise
}

# API Configuration
API_URL = "https://api.elevenlabs.io/v1/text-to-dialogue"
MODEL_ID = "eleven_v3"  # Default model for text-to-dialogue (v3 family required)
MAX_CHARS_PER_REQUEST = 4500  # Keep under 5000 limit with margin


def parse_dialogue_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a dialogue line and extract speaker and text.
    Strips stage directions in brackets.

    Format: "Speaker: [stage direction] dialogue text"
    Returns: (speaker, cleaned_text) or None if not a dialogue line
    """
    line = line.strip()
    if not line or ":" not in line:
        return None

    # Split speaker and content
    parts = line.split(":", 1)
    if len(parts) != 2:
        return None

    speaker = parts[0].strip()
    content = parts[1].strip()

    # Remove stage directions in brackets
    content = re.sub(r'\[.*?\]', '', content).strip()

    # Skip if no content left
    if not content:
        return None

    return (speaker, content)


def chunk_dialogues(dialogues: List[Tuple[str, str]], max_chars: int) -> List[List[Tuple[str, str]]]:
    """
    Split dialogues into chunks that don't exceed max_chars total length.

    Args:
        dialogues: List of (speaker, text) tuples
        max_chars: Maximum total character count per chunk

    Returns:
        List of dialogue chunks
    """
    chunks = []
    current_chunk = []
    current_length = 0

    for speaker, text in dialogues:
        text_len = len(text)

        # If adding this would exceed limit, start new chunk
        if current_chunk and current_length + text_len > max_chars:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0

        current_chunk.append((speaker, text))
        current_length += text_len

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_dialogue_chunk(dialogues: List[Tuple[str, str]], chunk_num: int, total_chunks: int,
                           voice_mapping: Dict[str, str] = None) -> bytes:
    """
    Generate audio for a chunk of dialogue.

    Args:
        dialogues: List of (speaker, text) tuples for this chunk
        chunk_num: Current chunk number (1-indexed)
        total_chunks: Total number of chunks
        voice_mapping: Dict mapping speaker names to voice IDs. If None, uses global VOICES

    Returns:
        Audio bytes
    """
    # Use provided voice_mapping or fall back to global VOICES
    voices = voice_mapping if voice_mapping is not None else VOICES

    # Build inputs array for API
    inputs = []
    for speaker, text in dialogues:
        voice_id = voices.get(speaker)
        if not voice_id:
            print(f"Warning: No voice found for speaker '{speaker}', using default")
            voice_id = list(voices.values())[0] if voices else list(VOICES.values())[0]

        inputs.append({
            "text": text,
            "voice_id": voice_id
        })

    # Build request payload
    payload = {
        "inputs": inputs,
        "model_id": MODEL_ID,
    }

    # Make API request
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"\n[Chunk {chunk_num}/{total_chunks}] Making API request...")
    print(f"  Segments: {len(inputs)}")
    print(f"  Characters: {sum(len(inp['text']) for inp in inputs)}")

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=600  # 10 minute timeout
        )

        # Check for errors
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

        print(f"  ✓ Received {len(audio_bytes):,} bytes")
        return audio_bytes

    except requests.exceptions.Timeout:
        raise Exception("Request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")


def combine_audio_files(audio_files: List[str], output_file: str):
    """
    Combine multiple MP3 files into one using ffmpeg.

    Args:
        audio_files: List of audio file paths to combine
        output_file: Output file path
    """
    print(f"\nCombining {len(audio_files)} audio chunks...")

    # Create a concat file for ffmpeg
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        for audio_file in audio_files:
            # Write absolute path and escape single quotes
            abs_path = os.path.abspath(audio_file)
            f.write(f"file '{abs_path}'\n")

    try:
        # Use ffmpeg to concatenate
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_file
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"ffmpeg error: {result.stderr}")

        print(f"✓ Combined audio saved to {output_file}")

    finally:
        # Clean up
        os.unlink(concat_file)


def generate_dialogue_audio(dialogues: List[Tuple[str, str]], output_file: str,
                           voice_mapping: Dict[str, str] = None):
    """
    Generate audio for entire dialogue using text-to-dialogue API.
    Handles chunking for large dialogues.

    Args:
        dialogues: List of (speaker, text) tuples
        output_file: Path to save the output MP3
        voice_mapping: Dict mapping speaker names to voice IDs. If None, uses global VOICES
    """
    print(f"\n=== Generating Audio ===")
    print(f"Total dialogue segments: {len(dialogues)}")

    # Calculate total characters
    total_chars = sum(len(text) for _, text in dialogues)
    print(f"Total characters: {total_chars:,}")

    # Check if we need to chunk
    if total_chars <= MAX_CHARS_PER_REQUEST:
        print("Processing in single request...")
        audio_bytes = generate_dialogue_chunk(dialogues, 1, 1, voice_mapping)

        # Write to file
        with open(output_file, 'wb') as f:
            f.write(audio_bytes)

        file_size = os.path.getsize(output_file)
        print(f"\n✓ Success!")
        print(f"  File: {output_file}")
        print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")

    else:
        # Need to chunk
        chunks = chunk_dialogues(dialogues, MAX_CHARS_PER_REQUEST)
        print(f"Dialogue will be processed in {len(chunks)} chunks")

        # Generate audio for each chunk
        temp_files = []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                for i, chunk in enumerate(chunks, 1):
                    audio_bytes = generate_dialogue_chunk(chunk, i, len(chunks), voice_mapping)

                    # Save to temporary file
                    temp_file = os.path.join(tmpdir, f"chunk_{i:03d}.mp3")
                    with open(temp_file, 'wb') as f:
                        f.write(audio_bytes)
                    temp_files.append(temp_file)

                # Combine all chunks
                combine_audio_files(temp_files, output_file)

                file_size = os.path.getsize(output_file)
                print(f"\n✓ Success!")
                print(f"  File: {output_file}")
                print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")

        except Exception as e:
            # Clean up on error
            if os.path.exists(output_file):
                os.remove(output_file)
            raise


def process_dialogue_file(input_file: str, output_file: str):
    """Process dialogue file and generate MP3."""
    print(f"\n=== ElevenLabs Text-to-Dialogue Generator ===")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}\n")

    # Read and parse input file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse dialogue
    dialogues = []
    for line_num, line in enumerate(lines, 1):
        result = parse_dialogue_line(line)
        if result:
            speaker, text = result
            dialogues.append((speaker, text))
            # Show first 60 chars of text
            preview = text[:60] + "..." if len(text) > 60 else text
            print(f"Line {line_num}: {speaker} - {preview}")

    if not dialogues:
        raise Exception("No dialogue found in input file")

    print(f"\nParsed {len(dialogues)} dialogue segments")

    # Generate audio using text-to-dialogue API
    generate_dialogue_audio(dialogues, output_file)


def main():
    # Default paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / "test_excerpt.txt"
    output_dir = project_root / "audio_output"
    output_file = output_dir / "test_dialogue.mp3"

    # Allow command line arguments
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Process
    try:
        process_dialogue_file(str(input_file), str(output_file))
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
