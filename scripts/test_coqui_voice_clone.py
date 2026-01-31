#!/usr/bin/env python3
"""Test Coqui TTS XTTS v2 voice cloning with reference audio"""

import os
import time
from TTS.api import TTS

# Test text from Rip Van Winkle
TEXT = """If you've ever traveled up the Hudson River in New York, you've probably noticed the Catskill Mountains rising up to the west. They're the kind of mountains that seem almost magical—their colors shift with every change in weather, every hour of the day."""

# Voice references to test
VOICE_REFERENCES = {
    "maurice-meditate": "resources/voices/maurice-meditate.mp3",
    "sam-deep": "resources/voices/sam-deep.mp3",
    "bill-calm": "resources/voices/bill_calm.mp3",
}

OUTPUT_DIR = "tts_tests/coqui_cloned"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 80)
print("🎙️  Coqui TTS XTTS v2 - Voice Cloning Test")
print("=" * 80)
print()

# Initialize XTTS v2
print("📦 Loading XTTS v2 model...")
print("   (First run will download ~1.8GB model)")
start = time.time()
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
load_time = time.time() - start
print(f"✓ Model loaded in {load_time:.1f}s\n")

for name, ref_audio in VOICE_REFERENCES.items():
    print("-" * 80)
    print(f"Testing voice: {name}")
    print(f"Reference: {ref_audio}")
    print("-" * 80)

    if not os.path.exists(ref_audio):
        print(f"❌ Reference audio not found: {ref_audio}\n")
        continue

    output_file = f"{OUTPUT_DIR}/{name}_cloned.wav"

    print("🎙️  Generating speech with cloned voice...")
    start = time.time()

    try:
        tts.tts_to_file(
            text=TEXT,
            file_path=output_file,
            speaker_wav=ref_audio,
            language="en"
        )

        gen_time = time.time() - start
        file_size = os.path.getsize(output_file) / 1024  # KB

        print(f"✓ Generated in {gen_time:.1f}s")
        print(f"📁 Saved: {output_file}")
        print(f"📊 Size: {file_size:.1f} KB")
        print()

    except Exception as e:
        print(f"❌ Error: {e}\n")

print("=" * 80)
print("✅ Voice cloning test complete!")
print(f"\n📁 All samples saved to: {OUTPUT_DIR}/")
print()
print("HOW TO CUSTOMIZE:")
print("-" * 80)
print("1. Voice Cloning:")
print("   - Provide ANY MP3/WAV file (6+ seconds)")
print("   - XTTS v2 will clone that voice")
print("   - Use parameter: speaker_wav='path/to/voice.mp3'")
print()
print("2. Language:")
print("   - Supports 16+ languages")
print("   - Use parameter: language='en' (or 'es', 'fr', 'de', etc.)")
print()
print("3. Speed & Prosody:")
print("   - Controlled by reference audio's pace")
print("   - Naturally adapts to the cloned voice")
print()
print("4. Quality:")
print("   - Better reference audio = better cloning")
print("   - Clear, mono, 6-30 seconds ideal")
print("=" * 80)
