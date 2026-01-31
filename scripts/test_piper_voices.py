#!/usr/bin/env python3
"""Test different Piper voices to find deeper/more meditative options"""

import wave
import time
from piper import PiperVoice

# Short test text
text = "If you've ever traveled up the Hudson River in New York, you've probably noticed the Catskill Mountains rising up to the west."

voices_to_test = [
    ("en_US-lessac-medium", "Current voice - male narrator"),
    ("en_US-ryan-low", "Ryan voice (low quality, potentially deeper)"),
]

print("🎙️  Testing Piper Voices for Depth/Meditation Quality\n")
print("=" * 70)

for voice_name, description in voices_to_test:
    print(f"\n📢 Testing: {voice_name}")
    print(f"   Description: {description}")

    try:
        model_path = f"tts_tests/piper_models/{voice_name}.onnx"

        # Load voice
        start = time.time()
        voice = PiperVoice.load(model_path, use_cuda=False)
        load_time = time.time() - start

        # Generate audio
        start = time.time()
        audio_chunks = []
        for chunk in voice.synthesize(text):
            audio_chunks.append(chunk.audio_int16_bytes)
        gen_time = time.time() - start

        # Save to file
        output_file = f"tts_tests/piper_models/tts_samples/{voice_name}.wav"
        audio_data = b''.join(audio_chunks)

        with wave.open(output_file, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(voice.config.sample_rate)
            wav.writeframes(audio_data)

        print(f"   ✓ Generated in {gen_time:.2f}s (load: {load_time:.2f}s)")
        print(f"   📁 Saved to: {output_file}")
        print(f"   🎵 Sample rate: {voice.config.sample_rate} Hz")

    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("\n✅ Voice comparison complete!")
print(f"\nAll samples saved to: tts_tests/piper_models/tts_samples/")
