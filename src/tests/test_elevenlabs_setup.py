#!/usr/bin/env python3
"""
Test ElevenLabs parallel generation setup.
Validates the code without making actual API calls.
"""

import json
import sys
from pathlib import Path

def test_import():
    """Test that the module can be imported"""
    try:
        from scripts.elevenlabs_audio_generator import (
            ElevenLabsSceneGenerator,
            ParallelElevenLabsGenerator
        )
        print("✓ Module imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_class_instantiation():
    """Test that classes can be instantiated"""
    try:
        from scripts.elevenlabs_audio_generator import (
            ElevenLabsSceneGenerator,
            ParallelElevenLabsGenerator
        )

        # Test single generator
        generator = ElevenLabsSceneGenerator(
            voice_id="test_voice",
            api_key="test_key",
            model_id="eleven_turbo_v2_5"
        )
        print("✓ ElevenLabsSceneGenerator instantiates correctly")

        # Test parallel generator
        parallel_gen = ParallelElevenLabsGenerator(
            voice_id="test_voice",
            api_key="test_key",
            model_id="eleven_turbo_v2_5",
            max_workers=10
        )
        print("✓ ParallelElevenLabsGenerator instantiates correctly")

        return True
    except Exception as e:
        print(f"✗ Instantiation failed: {e}")
        return False

def test_scenes_json_structure():
    """Verify scenes.json has correct structure"""
    scenes_path = Path("experiments/animal_farm_e2/scenes.json")

    if not scenes_path.exists():
        print(f"✗ Scenes file not found: {scenes_path}")
        return False

    try:
        with open(scenes_path) as f:
            data = json.load(f)

        if 'scenes' not in data:
            print("✗ scenes.json missing 'scenes' key")
            return False

        scenes = data['scenes']
        print(f"✓ Found {len(scenes)} scenes in scenes.json")

        # Check first scene structure
        if scenes:
            scene = scenes[0]
            required_keys = ['scene_id', 'sentences']
            missing = [k for k in required_keys if k not in scene]
            if missing:
                print(f"✗ Scene missing required keys: {missing}")
                return False

            print(f"✓ Scene structure is valid")
            print(f"  - Sample scene {scene['scene_id']}: {len(scene['sentences'])} sentences")

        return True
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading scenes: {e}")
        return False

def test_emotion_tag_detection():
    """Check if any scenes have emotion tags (for future use)"""
    scenes_path = Path("experiments/animal_farm_e2/scenes.json")

    try:
        with open(scenes_path) as f:
            data = json.load(f)

        scenes_with_tags = 0
        for scene in data['scenes']:
            for sentence in scene['sentences']:
                if '[' in sentence and ']' in sentence:
                    scenes_with_tags += 1
                    break

        if scenes_with_tags > 0:
            print(f"✓ Found emotion tags in {scenes_with_tags} scenes")
        else:
            print("ℹ No emotion tags found yet (user will provide updated scenes.json)")

        return True
    except Exception as e:
        print(f"✗ Error checking emotion tags: {e}")
        return False

def test_dependencies():
    """Check for required dependencies"""
    try:
        import requests
        print("✓ requests library available")

        import concurrent.futures
        print("✓ concurrent.futures available")

        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        return False

def main():
    print("="*60)
    print("ElevenLabs Parallel Generation Setup Test")
    print("="*60)
    print()

    tests = [
        ("Import Test", test_import),
        ("Class Instantiation", test_class_instantiation),
        ("Scenes JSON Structure", test_scenes_json_structure),
        ("Emotion Tag Detection", test_emotion_tag_detection),
        ("Dependencies", test_dependencies),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        print("-" * 60)
        results.append(test_func())

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("1. Add ELEVENLABS_API_KEY to .env.secrets")
        print("2. Get a voice ID from ElevenLabs (e.g., 'pNInz6obpgDQGcFmaJgB')")
        print("3. Wait for user to provide scenes.json with emotion tags")
        print("4. Run test generation:")
        print("\n   python scripts/elevenlabs_audio_generator.py \\")
        print("     --scenes experiments/animal_farm_e2/scenes.json \\")
        print("     --output-dir experiments/animal_farm_e2/audio_elevenlabs \\")
        print("     --voice-id <YOUR_VOICE_ID> \\")
        print("     --max-workers 5")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
