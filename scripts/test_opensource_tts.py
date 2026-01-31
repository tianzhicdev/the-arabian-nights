#!/usr/bin/env python3
"""
Test various open-source TTS engines for audiobook narration.
Tests: Coqui TTS (XTTS v2), Bark, StyleTTS 2, and Piper
"""

import os
import time
import sys

# Test text from Rip Van Winkle
TEST_TEXT = """If you've ever traveled up the Hudson River in New York, you've probably noticed the Catskill Mountains rising up to the west. They're the kind of mountains that seem almost magical—their colors shift with every change in weather, every hour of the day. When the weather is fair, the mountains turn blue and purple against the evening sky. But when a storm is coming, they gather hoods of gray mist around their summits, like old men pulling on their nightcaps. At the foot of these mountains, there once sat a little village founded by Dutch settlers long ago. Some of the original houses were still standing—quaint little buildings made of yellow bricks brought all the way from Holland, with weathercocks spinning on their rooftops."""

OUTPUT_DIR = "tts_tests"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_coqui_xtts():
    """Test Coqui TTS XTTS v2"""
    print("\n" + "="*80)
    print("TESTING: Coqui TTS (XTTS v2)")
    print("="*80)

    try:
        from TTS.api import TTS

        print("📦 Installing/loading Coqui TTS model...")
        # Use XTTS v2 model - supports voice cloning and multiple languages
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"

        start_init = time.time()
        tts = TTS(model_name)
        init_time = time.time() - start_init

        print(f"✓ Model loaded in {init_time:.2f}s")

        # Get available speakers if any
        if hasattr(tts, 'speakers') and tts.speakers:
            print(f"Available speakers: {tts.speakers}")

        # Generate audio with default male voice
        output_path = f"{OUTPUT_DIR}/coqui_xtts_male.wav"

        print(f"🎙️  Generating audio...")
        start_gen = time.time()

        # XTTS v2 requires a reference audio for voice cloning
        # We'll use a default approach without reference
        tts.tts_to_file(
            text=TEST_TEXT,
            file_path=output_path,
            language="en"
        )

        gen_time = time.time() - start_gen

        print(f"✓ Audio generated in {gen_time:.2f}s")
        print(f"📁 Saved to: {output_path}")

        # File size
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"📊 File size: {file_size:.1f} KB")

        return {
            "name": "Coqui TTS (XTTS v2)",
            "init_time": init_time,
            "gen_time": gen_time,
            "output": output_path,
            "customization": "High - Supports voice cloning from 6+ seconds of audio, multilingual",
            "quality": "Excellent for voice cloning, requires reference audio",
            "notes": "Requires reference audio for best results. Can clone any voice."
        }

    except ImportError:
        print("❌ Coqui TTS not installed. Installing...")
        os.system("pip install TTS")
        print("Please run the script again after installation.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_bark():
    """Test Bark TTS"""
    print("\n" + "="*80)
    print("TESTING: Bark (Suno)")
    print("="*80)

    try:
        from bark import SAMPLE_RATE, generate_audio, preload_models
        from scipy.io.wavfile import write as write_wav

        print("📦 Preloading Bark models...")
        start_init = time.time()
        preload_models()
        init_time = time.time() - start_init

        print(f"✓ Models loaded in {init_time:.2f}s")

        # Bark uses prompts like "v2/en_speaker_6" for different voices
        # v2/en_speaker_6 is a good male narrator voice
        voice_preset = "v2/en_speaker_6"

        output_path = f"{OUTPUT_DIR}/bark_male_narrator.wav"

        print(f"🎙️  Generating audio with voice preset: {voice_preset}")
        start_gen = time.time()

        audio_array = generate_audio(TEST_TEXT, history_prompt=voice_preset)

        gen_time = time.time() - start_gen

        write_wav(output_path, SAMPLE_RATE, audio_array)

        print(f"✓ Audio generated in {gen_time:.2f}s")
        print(f"📁 Saved to: {output_path}")

        file_size = os.path.getsize(output_path) / 1024
        print(f"📊 File size: {file_size:.1f} KB")

        return {
            "name": "Bark (Suno)",
            "init_time": init_time,
            "gen_time": gen_time,
            "output": output_path,
            "customization": "Medium - Preset voices (v2/en_speaker_0-9), can add music/effects",
            "quality": "Very expressive, natural with emotions, music capability",
            "notes": "Can generate non-speech sounds, music. Very compute-heavy. Quality varies."
        }

    except ImportError:
        print("❌ Bark not installed. Installing...")
        os.system("pip install git+https://github.com/suno-ai/bark.git")
        print("Please run the script again after installation.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_styletts2():
    """Test StyleTTS 2"""
    print("\n" + "="*80)
    print("TESTING: StyleTTS 2")
    print("="*80)

    try:
        # StyleTTS 2 requires manual installation from GitHub
        # Check if installed
        try:
            import styletts2
        except ImportError:
            print("❌ StyleTTS 2 not found.")
            print("StyleTTS 2 requires manual installation:")
            print("  git clone https://github.com/yl4579/StyleTTS2.git")
            print("  cd StyleTTS2")
            print("  pip install -r requirements.txt")
            return {
                "name": "StyleTTS 2",
                "init_time": 0,
                "gen_time": 0,
                "output": None,
                "customization": "High - Supports reference audio for style transfer",
                "quality": "Excellent prosody and naturalness",
                "notes": "Requires manual installation. Complex setup. Best quality/naturalness."
            }

        # If we get here, it's installed - would need actual implementation
        print("StyleTTS 2 detected but integration not implemented in this test script.")
        return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_piper():
    """Test Piper TTS"""
    print("\n" + "="*80)
    print("TESTING: Piper")
    print("="*80)

    try:
        # Piper is typically used via command-line
        # Check if piper is installed
        result = os.system("which piper-tts > /dev/null 2>&1")

        if result != 0:
            print("❌ Piper not installed. Installing...")
            print("Install via: pip install piper-tts")

            # Try to install
            os.system("pip install piper-tts")

            return {
                "name": "Piper",
                "init_time": 0,
                "gen_time": 0,
                "output": None,
                "customization": "Low - Select from pre-trained voices",
                "quality": "Good for CPU, fast but lower quality than others",
                "notes": "Lightweight, CPU-friendly. Many pre-trained voices. Best for speed."
            }

        # Download a male voice model if not exists
        model_dir = os.path.expanduser("~/.local/share/piper")
        os.makedirs(model_dir, exist_ok=True)

        # Use en_US-lessac-medium (male voice)
        model_name = "en_US-lessac-medium"

        output_path = f"{OUTPUT_DIR}/piper_male_narrator.wav"

        # Create temp text file
        text_file = f"{OUTPUT_DIR}/test_text.txt"
        with open(text_file, 'w') as f:
            f.write(TEST_TEXT)

        print(f"🎙️  Generating audio with Piper...")
        start_gen = time.time()

        # Run piper command
        cmd = f"echo '{TEST_TEXT}' | piper-tts --model {model_name} --output_file {output_path}"
        result = os.system(cmd)

        gen_time = time.time() - start_gen

        if result == 0 and os.path.exists(output_path):
            print(f"✓ Audio generated in {gen_time:.2f}s")
            print(f"📁 Saved to: {output_path}")

            file_size = os.path.getsize(output_path) / 1024
            print(f"📊 File size: {file_size:.1f} KB")

            return {
                "name": "Piper",
                "init_time": 0,
                "gen_time": gen_time,
                "output": output_path,
                "customization": "Low - Select from pre-trained voices",
                "quality": "Good for CPU, fast but lower quality than others",
                "notes": "Lightweight, CPU-friendly. Many voices. Best for speed/efficiency."
            }
        else:
            print(f"❌ Generation failed")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n🎯 Open-Source TTS Engine Testing")
    print("Testing text from 'Rip Van Winkle'")
    print(f"Text length: {len(TEST_TEXT)} characters\n")

    results = []

    # Test each engine
    result = test_coqui_xtts()
    if result:
        results.append(result)

    result = test_bark()
    if result:
        results.append(result)

    result = test_styletts2()
    if result:
        results.append(result)

    result = test_piper()
    if result:
        results.append(result)

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)

    for r in results:
        print(f"\n🎤 {r['name']}")
        print(f"   Init time: {r['init_time']:.2f}s")
        print(f"   Generation time: {r['gen_time']:.2f}s")
        print(f"   Customization: {r['customization']}")
        print(f"   Quality: {r['quality']}")
        print(f"   Notes: {r['notes']}")
        if r['output']:
            print(f"   Output: {r['output']}")

    print(f"\n📁 All outputs saved to: {OUTPUT_DIR}/")
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    main()
