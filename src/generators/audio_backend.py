#!/usr/bin/env python3
"""
Audio Backend Abstraction for Podcast Generation
Supports ElevenLabs (API) and Chatterbox (local TTS)
"""
import os
import sys
import tempfile
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
from pathlib import Path


class AudioBackend(ABC):
    """Abstract base class for audio generation backends"""

    @abstractmethod
    def generate_chunk(self, dialogues: List[Tuple[str, str]], chunk_num: int, total_chunks: int) -> bytes:
        """
        Generate audio for a chunk of dialogues

        Args:
            dialogues: List of (speaker, text) tuples
            chunk_num: Current chunk number (1-indexed)
            total_chunks: Total number of chunks

        Returns:
            Audio bytes (MP3 or WAV format)
        """
        pass

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Return the output audio format (e.g., 'mp3', 'wav')"""
        pass


class ElevenLabsBackend(AudioBackend):
    """ElevenLabs API backend for TTS generation"""

    def __init__(self, voice_mapping: Dict[str, str], api_key: str):
        """
        Initialize ElevenLabs backend

        Args:
            voice_mapping: Dict mapping speaker names to voice IDs
            api_key: ElevenLabs API key
        """
        self.voice_mapping = voice_mapping
        self.api_key = api_key
        self.api_url = "https://api.elevenlabs.io/v1/text-to-dialogue"
        self.model_id = "eleven_v3"

    def generate_chunk(self, dialogues: List[Tuple[str, str]], chunk_num: int, total_chunks: int) -> bytes:
        """Generate audio using ElevenLabs API"""
        import requests

        # Build inputs array for API
        inputs = []
        for speaker, text in dialogues:
            voice_id = self.voice_mapping.get(speaker)
            if not voice_id:
                raise ValueError(f"No voice mapping found for speaker: {speaker}")

            inputs.append({
                "text": text,
                "voice_id": voice_id
            })

        # Build request payload
        payload = {
            "inputs": inputs,
            "model_id": self.model_id,
        }

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        print(f"  [Chunk {chunk_num}/{total_chunks}] Generating audio...")
        print(f"    Segments: {len(inputs)}")
        print(f"    Characters: {sum(len(inp['text']) for inp in inputs)}")

        try:
            response = requests.post(
                self.api_url,
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

    @property
    def output_format(self) -> str:
        return "mp3"


class ChatterboxBackend(AudioBackend):
    """Chatterbox local TTS backend"""

    def __init__(self, audio_prompt_path: str, device: str = 'cpu', exaggeration: float = 0.7, speed: float = 1.0):
        """
        Initialize Chatterbox backend

        Args:
            audio_prompt_path: Path to audio file for voice cloning (5-10 seconds)
            device: 'cpu' or 'cuda'
            exaggeration: Emotion exaggeration level (0.0-1.0)
            speed: Playback speed multiplier (0.5 = half speed/slower, 1.0 = normal, 1.5 = faster)
        """
        try:
            from chatterbox import ChatterboxTTS
            import torchaudio as ta
        except ImportError as e:
            print(f"✗ Error: Chatterbox dependencies not installed")
            print(f"\nTo install:")
            print(f"  pip install chatterbox-tts")
            raise

        # Validate audio prompt path
        if audio_prompt_path is None:
            raise ValueError(
                "Chatterbox backend requires an audio reference file for voice cloning.\n"
                "Please provide --audio-reference with a 5-10 second voice sample.\n"
                "Example: --audio-reference path/to/voice_sample.mp3"
            )
        if not os.path.exists(audio_prompt_path):
            raise FileNotFoundError(f"Audio prompt file not found: {audio_prompt_path}")

        print(f"  Loading Chatterbox model (device={device})...")
        self.model = ChatterboxTTS.from_pretrained(device=device)
        self.audio_prompt_path = audio_prompt_path
        self.exaggeration = exaggeration
        self.speed = speed
        self.sample_rate = self.model.sr
        print(f"  ✓ Model loaded (sample_rate={self.sample_rate}, speed={speed}x)")

    def generate_chunk(self, dialogues: List[Tuple[str, str]], chunk_num: int, total_chunks: int) -> bytes:
        """Generate audio using Chatterbox local TTS - one line at a time, then combine"""
        import torchaudio as ta
        import re
        from pydub import AudioSegment

        print(f"  [Chunk {chunk_num}/{total_chunks}] Generating audio with Chatterbox...")
        print(f"    Segments: {len(dialogues)}")
        print(f"    Audio prompt: {os.path.basename(self.audio_prompt_path)}")

        # Generate each dialogue line separately
        temp_audio_files = []

        for i, (speaker, text) in enumerate(dialogues, 1):
            # Extract pause instructions before removing tags
            pauses = []
            pause_pattern = r'\[pause(?:-(\d+(?:\.\d+)?))?\]'

            for match in re.finditer(pause_pattern, text):
                duration = float(match.group(1)) if match.group(1) else 1.0  # Default 1 second
                pauses.append(duration)

            # Remove ALL emotion tags [anything]
            clean_text = re.sub(r'\[.*?\]', '', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            if not clean_text and not pauses:  # Skip if empty after removing tags and no pauses
                continue

            if clean_text:
                print(f"    [{i}/{len(dialogues)}] {speaker}: {clean_text[:60]}{'...' if len(clean_text) > 60 else ''}")

                # Generate audio for this line
                wav = self.model.generate(
                    clean_text,
                    audio_prompt_path=self.audio_prompt_path,
                    exaggeration=self.exaggeration
                )

                # Save to temp file
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_wav.close()
                ta.save(temp_wav.name, wav, self.sample_rate)

                # Adjust speed if needed
                if self.speed != 1.0:
                    segment = AudioSegment.from_wav(temp_wav.name)
                    # Change speed without changing pitch
                    segment = segment._spawn(segment.raw_data, overrides={
                        "frame_rate": int(segment.frame_rate * self.speed)
                    }).set_frame_rate(self.sample_rate)
                    segment.export(temp_wav.name, format="wav")

                temp_audio_files.append(temp_wav.name)

                duration = len(wav[0]) / self.sample_rate / self.speed
                print(f"        ✓ Generated {duration:.1f}s")

            # Add pause segments if specified
            for pause_duration in pauses:
                print(f"        [Adding {pause_duration}s pause]")
                silence_segment = AudioSegment.silent(duration=int(pause_duration * 1000))
                temp_pause = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_pause.close()
                silence_segment.export(temp_pause.name, format="wav")
                temp_audio_files.append(temp_pause.name)

        # Combine all audio files
        print(f"    Combining {len(temp_audio_files)} audio segments...")
        combined = AudioSegment.empty()

        for audio_file in temp_audio_files:
            segment = AudioSegment.from_wav(audio_file)
            combined += segment

        # Export combined audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            combined_path = f.name

        combined.export(combined_path, format="wav")

        try:
            # Read combined audio as bytes
            with open(combined_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()

            print(f"    ✓ Combined audio: {len(audio_bytes):,} bytes ({len(combined)/1000:.1f}s)")
            return audio_bytes

        finally:
            # Clean up all temp files
            for temp_file in temp_audio_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            if os.path.exists(combined_path):
                os.unlink(combined_path)

    @property
    def output_format(self) -> str:
        return "wav"


def create_backend(audio_type: str, **kwargs) -> AudioBackend:
    """
    Factory function to create audio backend

    Args:
        audio_type: 'elevenlabs' or 'chatterbox'
        **kwargs: Backend-specific arguments

    Returns:
        AudioBackend instance
    """
    if audio_type == 'elevenlabs':
        return ElevenLabsBackend(
            voice_mapping=kwargs['voice_mapping'],
            api_key=kwargs['api_key']
        )
    elif audio_type == 'chatterbox':
        return ChatterboxBackend(
            audio_prompt_path=kwargs['audio_prompt_path'],
            device=kwargs.get('device', 'cpu'),
            exaggeration=kwargs.get('exaggeration', 0.7),
            speed=kwargs.get('speed', 1.0)
        )
    else:
        raise ValueError(f"Unknown audio backend: {audio_type}")
