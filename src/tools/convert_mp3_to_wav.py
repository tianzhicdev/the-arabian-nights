#!/usr/bin/env python3
"""Convert MP3 files to WAV format for pipeline compatibility."""

import subprocess
from pathlib import Path

audio_dir = Path("experiments/animal_farm_e2/audio")

mp3_files = sorted(audio_dir.glob("*.mp3"))
print(f"Found {len(mp3_files)} MP3 files to convert")

for i, mp3_file in enumerate(mp3_files, 1):
    wav_file = mp3_file.with_suffix(".wav")
    print(f"[{i}/{len(mp3_files)}] Converting {mp3_file.name}...")

    cmd = [
        'ffmpeg', '-i', str(mp3_file),
        '-ar', '24000',  # Sample rate 24kHz
        '-ac', '1',      # Mono
        str(wav_file), '-y'
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0:
        print(f"  ✓ Created {wav_file.name}")
    else:
        print(f"  ✗ Failed: {result.stderr.decode()[:100]}")

print(f"\n✓ Conversion complete")
wav_files = list(audio_dir.glob("*.wav"))
print(f"Total WAV files: {len(wav_files)}")
