#!/usr/bin/env python3
"""
Podcast Audio Generator
Generates audio from podcast source directories using ElevenLabs or Chatterbox TTS
"""

import os
import re
import sys
import json
import argparse
import requests
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dotenv import load_dotenv

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from audio_backend import create_backend, AudioBackend

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.secrets")

# API Configuration (ElevenLabs)
API_KEY = os.getenv("ELEVEN_LABS_KEY")
API_URL = "https://api.elevenlabs.io/v1/text-to-dialogue"
MODEL_ID = "eleven_v3"  # v3 supports emotion tags
MAX_CHARS_PER_REQUEST = 4500


def parse_dialogue_line(line: str, narration_mode: bool = False, default_speaker: str = "Narrator") -> Optional[Tuple[str, str]]:
    """
    Parse a dialogue line and extract speaker and text.
    Does NOT strip emotion tags - keeps all [tags] intact.

    Format:
      - Dialogue mode: "Speaker: [emotion] dialogue text"
      - Narration mode: "dialogue text" (no speaker prefix)

    Returns: (speaker, full_text_with_tags) or None if not a dialogue line
    """
    line = line.strip()

    # Skip empty lines
    if not line:
        return None

    # Skip comment lines (starting with #)
    if line.startswith('#'):
        return None

    if narration_mode:
        # Narration mode: treat entire line as content (no speaker prefix)
        content = line

        # Check if there's actual text or pause tags
        text_without_tags = re.sub(r'\[.*?\]', '', content).strip()
        has_pause = re.search(r'\[pause(?:-\d+(?:\.\d+)?)?\]', content)

        # Skip only if no text AND no pause tags
        if not text_without_tags and not has_pause:
            return None

        return (default_speaker, content)

    else:
        # Dialogue mode: expect "Speaker: text" format
        if ":" not in line:
            return None

        # Split speaker and content
        parts = line.split(":", 1)
        if len(parts) != 2:
            return None

        speaker = parts[0].strip()
        content = parts[1].strip()

        # Skip if no content
        if not content:
            return None

        # Check if there's actual text or pause tags
        text_without_tags = re.sub(r'\[.*?\]', '', content).strip()
        has_pause = re.search(r'\[pause(?:-\d+(?:\.\d+)?)?\]', content)

        # Skip only if no text AND no pause tags
        if not text_without_tags and not has_pause:
            return None

        return (speaker, content)


def load_config(source_dir: Path, narration_mode: bool = False) -> Dict:
    """Load and validate config.json from source directory"""
    config_file = source_dir / "config.json"

    if not config_file.exists():
        raise FileNotFoundError(f"config.json not found in {source_dir}")

    with open(config_file, 'r') as f:
        config = json.load(f)

    # Validate required fields
    if 'id' not in config:
        raise ValueError(f"config.json missing required field: id")

    if narration_mode:
        # Narration mode: only need narrator info
        if 'narrator' not in config:
            raise ValueError(f"config.json missing required field for narration mode: narrator")
        if 'name' not in config['narrator']:
            raise ValueError(f"config.json narrator missing name")
    else:
        # Dialogue mode: need host_1 and host_2
        required = ['host_1', 'host_2']
        for field in required:
            if field not in config:
                raise ValueError(f"config.json missing required field: {field}")

        for host in ['host_1', 'host_2']:
            if 'name' not in config[host]:
                raise ValueError(f"config.json {host} missing name")
            # voice_id is only required for ElevenLabs, not for Chatterbox

    return config


def build_voice_mapping(config: Dict) -> Dict[str, str]:
    """
    Build voice mapping from config.
    Maps speaker names (full name, first name, last name) to voice IDs.
    """
    voice_mapping = {}

    for host_key in ['host_1', 'host_2']:
        full_name = config[host_key]['name']
        voice_id = config[host_key]['voice_id']

        # Add full name
        voice_mapping[full_name] = voice_id

        # Add first name and last name variants
        if ' ' in full_name:
            parts = full_name.split()
            first_name = parts[0]
            last_name = parts[-1]
            voice_mapping[first_name] = voice_id
            voice_mapping[last_name] = voice_id

    return voice_mapping


def load_dialogues(source_dir: Path, short_mode: bool = False, narration_mode: bool = False, narrator_name: str = "Narrator") -> List[Tuple[str, str]]:
    """Load dialogues from script.txt"""
    script_file = source_dir / "script.txt"

    if not script_file.exists():
        raise FileNotFoundError(f"script.txt not found in {source_dir}")

    with open(script_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse all dialogues
    dialogues = []
    for line in lines:
        result = parse_dialogue_line(line, narration_mode=narration_mode, default_speaker=narrator_name)
        if result:
            dialogues.append(result)

    if not dialogues:
        raise ValueError("No valid dialogues found in script.txt")

    # If short mode, take first 5-8 dialogue exchanges
    if short_mode:
        # Take first 8 dialogues (should be ~1 minute)
        dialogues = dialogues[:8]

    return dialogues


def chunk_dialogues(dialogues: List[Tuple[str, str]], max_chars: int) -> List[List[Tuple[str, str]]]:
    """Split dialogues into chunks that don't exceed max_chars total length"""
    chunks = []
    current_chunk = []
    current_length = 0

    for speaker, text in dialogues:
        text_len = len(text)

        if current_chunk and current_length + text_len > max_chars:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0

        current_chunk.append((speaker, text))
        current_length += text_len

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_dialogue_chunk(dialogues: List[Tuple[str, str]],
                           voice_mapping: Dict[str, str],
                           chunk_num: int,
                           total_chunks: int) -> bytes:
    """Generate audio for a chunk of dialogue using text-to-dialogue API"""

    # Build inputs array
    inputs = []
    for speaker, text in dialogues:
        voice_id = voice_mapping.get(speaker)
        if not voice_id:
            raise ValueError(f"No voice mapping found for speaker: {speaker}")

        inputs.append({
            "text": text,
            "voice_id": voice_id
        })

    # Build request payload
    payload = {
        "inputs": inputs,
        "model_id": MODEL_ID,
    }

    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"  [Chunk {chunk_num}/{total_chunks}] Generating audio...")
    print(f"    Segments: {len(inputs)}")
    print(f"    Characters: {sum(len(inp['text']) for inp in inputs)}")

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=600
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

        print(f"    ✓ Received {len(audio_bytes):,} bytes")
        return audio_bytes

    except requests.exceptions.Timeout:
        raise Exception("Request timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")


def combine_audio_files(audio_files: List[str], output_file: str):
    """Combine multiple MP3 files using ffmpeg"""
    print(f"  Combining {len(audio_files)} audio chunks...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        for audio_file in audio_files:
            abs_path = os.path.abspath(audio_file)
            f.write(f"file '{abs_path}'\n")

    try:
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

    finally:
        os.unlink(concat_file)


def generate_audio_with_backend(dialogues: List[Tuple[str, str]],
                                backend: AudioBackend,
                                output_file: str):
    """Generate audio for dialogues using the specified backend"""

    total_chars = sum(len(text) for _, text in dialogues)

    print(f"\nGenerating audio:")
    print(f"  Total dialogues: {len(dialogues)}")
    print(f"  Total characters: {total_chars:,}")

    # Check if we need to chunk
    if total_chars <= MAX_CHARS_PER_REQUEST:
        print(f"  Processing in single request...")
        audio_bytes = backend.generate_chunk(dialogues, 1, 1)

        with open(output_file, 'wb') as f:
            f.write(audio_bytes)

    else:
        # Need to chunk
        chunks = chunk_dialogues(dialogues, MAX_CHARS_PER_REQUEST)
        print(f"  Processing in {len(chunks)} chunks...")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_files = []

            for i, chunk in enumerate(chunks, 1):
                audio_bytes = backend.generate_chunk(chunk, i, len(chunks))

                # Use backend's output format
                ext = backend.output_format
                temp_file = os.path.join(tmpdir, f"chunk_{i:03d}.{ext}")
                with open(temp_file, 'wb') as f:
                    f.write(audio_bytes)
                temp_files.append(temp_file)

            combine_audio_files(temp_files, output_file)

    file_size = os.path.getsize(output_file)
    print(f"\n✓ Audio generated: {output_file}")
    print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")


# Legacy function for backwards compatibility
def generate_audio(dialogues: List[Tuple[str, str]],
                   voice_mapping: Dict[str, str],
                   output_file: str):
    """Legacy function - use generate_audio_with_backend instead"""
    from audio_backend import ElevenLabsBackend
    backend = ElevenLabsBackend(voice_mapping, API_KEY)
    generate_audio_with_backend(dialogues, backend, output_file)


def validate_config_for_backend(config: Dict, audio_type: str, audio_prompt_path: Optional[str], narration_mode: bool = False):
    """Validate that config is compatible with selected backend"""

    if audio_type == 'chatterbox':
        # Check for ElevenLabs-only parameters in config
        elevenlabs_params = []

        if narration_mode:
            # Narration mode - check narrator field
            if 'narrator' in config and 'voice_id' in config['narrator']:
                elevenlabs_params.append("narrator.voice_id")
        else:
            # Dialogue mode - check host fields
            for host_key in ['host_1', 'host_2']:
                if host_key in config:
                    if 'voice_id' in config[host_key]:
                        elevenlabs_params.append(f"{host_key}.voice_id")

        if elevenlabs_params:
            print(f"\n{'='*70}")
            print("✗ ERROR: Incompatible configuration for chatterbox backend")
            print(f"{'='*70}")
            print(f"\nFound ElevenLabs-only parameters in config:")
            for param in elevenlabs_params:
                print(f"  - {param}")
            print(f"\nThese parameters are only valid for --audio elevenlabs")
            print(f"\nFor chatterbox backend:")
            print(f"  1. Remove voice_id from config.json")
            print(f"  2. Provide --audio-prompt-path <speaker-voice-sample.wav>")
            print(f"\nOr switch back to ElevenLabs:")
            print(f"  --audio elevenlabs")
            print(f"\n{'='*70}\n")
            sys.exit(1)

        # Validate audio_prompt_path provided
        if not audio_prompt_path:
            # Check if in config
            config_key = 'narrator' if narration_mode else 'host_1'
            if 'audio_prompt_path' not in config.get(config_key, {}):
                print(f"\n✗ ERROR: --audio-prompt-path required for chatterbox backend")
                print(f"\nProvide voice sample file (5-10 seconds):")
                print(f"  --audio-prompt-path /path/to/speaker-voice.wav")
                sys.exit(1)

    elif audio_type == 'elevenlabs':
        # Validate voice_id present
        if narration_mode:
            if 'narrator' in config and 'voice_id' not in config['narrator']:
                print(f"\n✗ ERROR: narrator.voice_id required for ElevenLabs backend")
                sys.exit(1)
        else:
            for host_key in ['host_1', 'host_2']:
                if host_key in config:
                    if 'voice_id' not in config[host_key]:
                        print(f"\n✗ ERROR: {host_key}.voice_id required for ElevenLabs backend")
                        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Generate podcast audio from source directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Audio Backends:
  elevenlabs  - Cloud API with multiple voice support (requires API key)
  chatterbox  - Local TTS with voice cloning (free, slower, single narrator)

Examples:
  # ElevenLabs (default)
  python3 scripts/generate_podcast_audio.py --source resources/sources/episode1-consciousness

  # Chatterbox with voice cloning
  python3 scripts/generate_podcast_audio.py \\
    --source resources/sources/crime-punishment-part1 \\
    --audio chatterbox \\
    --audio-prompt-path speaker_voice.wav
        """
    )
    parser.add_argument('--source', required=True, help='Source directory containing config.json and script.txt')
    parser.add_argument('--short', '--test', dest='short', action='store_true',
                       help='Generate short preview (~1 min, first 8 dialogues)')
    parser.add_argument('--audio', choices=['elevenlabs', 'chatterbox'], default='elevenlabs',
                       help='Audio generation backend (default: elevenlabs)')
    parser.add_argument('--audio-prompt-path', help='Audio file for chatterbox voice cloning (5-10s sample)')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu',
                       help='Device for chatterbox (default: cpu)')
    parser.add_argument('--speed', type=float, default=1.0,
                       help='Playback speed for chatterbox (0.5=slower, 1.0=normal, 1.5=faster). Default: 1.0')
    parser.add_argument('--narration', action='store_true',
                       help='Narration mode: script has no "Speaker:" prefixes, all text read by single narrator')

    args = parser.parse_args()

    # Validate API key for ElevenLabs
    if args.audio == 'elevenlabs' and not API_KEY:
        print("✗ Error: ELEVEN_LABS_KEY not found in .env.secrets")
        print("\nFor ElevenLabs backend, add to .env.secrets:")
        print("  ELEVEN_LABS_KEY=your_api_key_here")
        print("\nOr use local chatterbox backend:")
        print("  --audio chatterbox --audio-prompt-path speaker.wav")
        sys.exit(1)

    # Validate source directory
    source_dir = Path(args.source).resolve()
    if not source_dir.exists():
        print(f"✗ Error: Source directory not found: {source_dir}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"PODCAST AUDIO GENERATOR")
    print(f"  Backend: {args.audio}")
    print(f"{'='*60}\n")

    try:
        # Load configuration
        print("Loading configuration...")
        config = load_config(source_dir, narration_mode=args.narration)
        print(f"  ID: {config['id']}")

        # Validate config for backend
        validate_config_for_backend(config, args.audio, args.audio_prompt_path, narration_mode=args.narration)

        # Display config based on backend
        if args.narration:
            narrator_name = config['narrator']['name']
            print(f"  Narrator: {narrator_name}")
            if args.audio == 'elevenlabs' and 'voice_id' in config['narrator']:
                print(f"    Voice ID: {config['narrator']['voice_id']}")
        else:
            if args.audio == 'elevenlabs':
                print(f"  Host 1: {config['host_1']['name']} (voice: {config['host_1']['voice_id']})")
                print(f"  Host 2: {config['host_2']['name']} (voice: {config['host_2']['voice_id']})")
            else:
                print(f"  Host 1: {config['host_1']['name']}")
                if 'host_2' in config:
                    print(f"  Host 2: {config['host_2']['name']}")

        # Load dialogues
        print(f"\nLoading script...")
        narrator_name = config['narrator']['name'] if args.narration else "Narrator"
        dialogues = load_dialogues(source_dir, short_mode=args.short, narration_mode=args.narration, narrator_name=narrator_name)
        print(f"  ✓ Loaded {len(dialogues)} dialogues")

        # Setup output directory
        output_dir = project_root / "audio_output" / config['id']
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create backend
        print(f"\nInitializing {args.audio} backend...")
        if args.audio == 'elevenlabs':
            voice_mapping = build_voice_mapping(config)
            backend = create_backend(
                'elevenlabs',
                voice_mapping=voice_mapping,
                api_key=API_KEY
            )
            output_ext = "mp3"
        else:  # chatterbox
            audio_prompt = args.audio_prompt_path or config['host_1'].get('audio_prompt_path')
            backend = create_backend(
                'chatterbox',
                audio_prompt_path=audio_prompt,
                device=args.device,
                speed=args.speed
            )
            output_ext = "wav"

        # Determine output filename
        if args.short:
            output_file = output_dir / f"short.{output_ext}"
            print(f"  Mode: Short preview (~1 minute)")
        else:
            output_file = output_dir / f"full.{output_ext}"
            print(f"  Mode: Full audio")

        # Generate audio with backend
        generate_audio_with_backend(dialogues, backend, str(output_file))

        # Copy config to output directory
        config_dest = output_dir / "config.json"
        shutil.copy2(source_dir / "config.json", config_dest)
        print(f"  ✓ Copied config to: {config_dest}")

        print(f"\n{'='*60}")
        print(f"✓ SUCCESS")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
