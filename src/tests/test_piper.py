#!/usr/bin/env python3
"""Quick test of Piper TTS"""

import wave
import time
from piper import PiperVoice

# Test text
text = "If you've ever traveled up the Hudson River in New York, you've probably noticed the Catskill Mountains rising up to the west. They're the kind of mountains that seem almost magical."

print("🎯 Testing Piper TTS")
print(f"Text: {text[:100]}...")
print()

# Use a male narrator voice - we'll download it on first run
voice_model = "en_US-lessac-medium"

try:
    print(f"Loading voice model: {voice_model}")
    start_time = time.time()

    # Download and load the voice
    voice = PiperVoice.load(voice_model, use_cuda=False)

    load_time = time.time() - start_time
    print(f"✓ Model loaded in {load_time:.2f}s")

    # Generate audio
    print("Generating audio...")
    start_gen = time.time()

    # Synthesize to WAV
    output_file = "tts_tests/piper_male_narrator.wav"

    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setframerate(voice.config.sample_rate)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setnchannels(1)  # Mono

        for audio_bytes in voice.synthesize_stream_raw(text):
            wav_file.writeframes(audio_bytes)

    gen_time = time.time() - start_gen
    print(f"✓ Audio generated in {gen_time:.2f}s")
    print(f"✓ Saved to: {output_file}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
