#!/usr/bin/env python3
"""
Quick test script for Coqui TTS with voice cloning.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

import torch
import numpy as np
import scipy.io.wavfile as wav

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_voice_cloning(voice_ref: Path, output_path: Path, text: str):
    """Generate audio using XTTS-v2 voice cloning."""

    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    print(f"Loading XTTS-v2 model...")
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
        audio_path=[str(voice_ref)]
    )
    print(f"Voice conditioning loaded!")

    # XTTS settings optimized for storytelling
    settings = {
        "temperature": 0.65,
        "repetition_penalty": 2.0,
        "top_p": 0.85,
    }

    print(f"Generating audio for: '{text}'")
    out = model.inference(
        text,
        "en",
        gpt_cond_latent,
        speaker_embedding,
        **settings
    )

    # Save as WAV then convert to MP3
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = Path(tmp.name)

    wav.write(str(wav_path), 24000, out["wav"])

    # Convert to MP3
    subprocess.run([
        'ffmpeg', '-y', '-i', str(wav_path),
        '-codec:a', 'libmp3lame', '-qscale:a', '2',
        str(output_path)
    ], capture_output=True)
    wav_path.unlink()

    print(f"Saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


def main():
    project_root = Path(__file__).parent.parent.parent
    voice_ref = project_root / "resources/voices/msong.mp3"
    output_dir = project_root / "output/test_audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "test_msong_voice.mp3"

    test_text = "Hello! This is a test of the voice cloning system. The quick brown fox jumps over the lazy dog."

    test_voice_cloning(voice_ref, output_path, test_text)

    print("\nDone! Play the output file to hear the result.")


if __name__ == '__main__':
    main()
