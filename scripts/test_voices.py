#!/usr/bin/env python3
"""
Generate test audio samples using all available voices for the first 2 scenes
"""

import sys
import json
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from audio_generator import ParallelAudioGenerator

def main():
    # Load Animal Farm E2 scenes
    scenes_file = Path(__file__).parent.parent / 'resources/stories/gutenberg/animal_farm_e2.json'

    with open(scenes_file, 'r') as f:
        data = json.load(f)

    # Get first 2 scenes
    test_scenes = data['scenes'][:2]

    # Get all available voices
    voices_dir = Path(__file__).parent.parent / 'resources/voices'
    voices = sorted(voices_dir.glob('*.mp3'))

    print(f"Found {len(voices)} voice files")
    print(f"Testing with first {len(test_scenes)} scenes\n")

    # Create output directory
    output_base = Path(__file__).parent.parent / 'output/voice_tests'
    output_base.mkdir(parents=True, exist_ok=True)

    # Generate audio for each voice
    for voice_path in voices:
        voice_name = voice_path.stem
        print(f"Generating audio with voice: {voice_name}")

        # Create voice-specific output directory
        audio_dir = output_base / voice_name
        audio_dir.mkdir(exist_ok=True)

        # Initialize audio generator
        generator = ParallelAudioGenerator(
            audio_prompt_path=str(voice_path),
            device='cpu',
            speed=1.0,
            max_workers=1  # Sequential for testing
        )

        # Generate audio for test scenes
        durations = generator.generate_all_scenes(
            scenes=test_scenes,
            audio_dir=audio_dir,
            checkpoint_mgr=None
        )

        print(f"  ✓ Generated {len(durations)} audio files")
        for scene_id, duration in durations.items():
            print(f"    {scene_id}: {duration:.2f}s")
        print()

    print("=" * 80)
    print("✓ Voice test generation complete!")
    print(f"Output directory: {output_base}")
    print("=" * 80)

if __name__ == '__main__':
    main()
