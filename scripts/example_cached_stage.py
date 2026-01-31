"""
Example: How to use CacheManagerV2 in your pipeline

This shows the improved, deterministic approach to caching.
"""

import json
from pathlib import Path
from cache_manager_v2 import CacheManagerV2, check_and_skip_if_cached


class PipelineWithCaching:
    """Example pipeline with V2 caching."""

    def __init__(self, args, output_dir):
        self.args = args
        self.output_dir = Path(output_dir)
        self.cache = CacheManagerV2(self.output_dir)

        # Register ALL input files upfront
        self._register_inputs()

    def _register_inputs(self):
        """Register all input files with cache."""
        self.cache.register_input_file('text_file', self.args.text)
        self.cache.register_input_file('art_reference', self.args.art_reference)
        self.cache.register_input_file('audio_reference', self.args.audio_reference)
        # ... register other inputs

    def generate_scenes(self):
        """
        Scene generation with caching - V2 approach.

        Key improvements:
        1. No manual output file lists
        2. Fingerprint stored in output directory
        3. Automatic cache validation
        """
        stage_name = 'scene_generation'

        # Define what this stage depends on
        input_deps = ['text_file']  # Only depends on text file
        params = {
            'length': self.args.length,
            'art_style': self.args.art_style or 'default',
            'narration_style': self.args.narration_style
        }

        # Get output directory
        output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)

        # CHECK CACHE - This is the key improvement!
        # We don't need to specify output files - they're discovered automatically
        if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                    input_deps, params):
            # Cache hit - load and return cached scenes
            scenes_file = output_dir / 'scenes.json'
            with open(scenes_file, 'r') as f:
                return json.load(f)

        # CACHE MISS - Generate scenes
        print(f"Generating scenes...")

        # Do actual generation
        scenes_data = self._do_scene_generation()

        # Save output
        scenes_file = output_dir / 'scenes.json'
        with open(scenes_file, 'w') as f:
            json.dump(scenes_data, f, indent=2)

        # MARK COMPLETE - This saves the fingerprint
        fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
        self.cache.mark_stage_complete(output_dir, fingerprint, cost=0.02,
                                      metadata={'scene_count': len(scenes_data['scenes'])})

        return scenes_data

    def generate_audio(self, scenes_data):
        """
        Audio generation with caching - V2 approach.

        This stage depends on:
        - Audio reference file (voice clone)
        - Scenes data (which itself depends on text file)
        """
        stage_name = 'audio_generation'

        # THIS IS THE KEY: We now track dependencies properly
        # Audio depends on audio_reference AND the scenes
        # We hash the scenes file, not just text file
        scenes_file = self.output_dir / 'scenes.json'
        self.cache.register_input_file('scenes_file', str(scenes_file))

        input_deps = ['audio_reference', 'scenes_file']  # Both dependencies
        params = {
            'workers': self.args.audio_workers,
            'speed': 1.0,
            'device': 'cpu'
        }

        output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)

        # Expected output patterns (for validation)
        expected_patterns = ['scene_*.wav']  # All wav files

        # Check cache
        if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                    input_deps, params, expected_patterns):
            print(f"✓ Using cached audio for {len(scenes_data['scenes'])} scenes")
            return

        # Generate audio
        print(f"Generating audio for {len(scenes_data['scenes'])} scenes...")

        from audio_generator import ParallelAudioGenerator
        generator = ParallelAudioGenerator(
            audio_prompt_path=self.args.audio_reference,
            device='cpu',
            speed=1.0,
            max_workers=self.args.audio_workers
        )

        durations = generator.generate_all_scenes(
            scenes=scenes_data['scenes'],
            audio_dir=output_dir,
            checkpoint_mgr=None
        )

        # Mark complete
        fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
        self.cache.mark_stage_complete(output_dir, fingerprint, cost=0.0,
                                      metadata={'scene_count': len(durations)})

    def generate_images(self, scenes_data):
        """
        Image generation with caching.

        Depends on:
        - Art reference (style transfer source)
        - Scenes data (image prompts)
        """
        stage_name = 'image_generation'

        # Register scenes as input
        scenes_file = self.output_dir / 'scenes.json'
        self.cache.register_input_file('scenes_file', str(scenes_file))

        input_deps = ['art_reference', 'scenes_file']
        params = {
            'model': 'gpt-4o',
            'size': '1536x1024',
            'quality': self.args.image_quality
        }

        output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)
        expected_patterns = ['scene_*.png']  # All png files

        # Check cache
        if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                    input_deps, params, expected_patterns):
            print(f"✓ Using cached images for {len(scenes_data['scenes'])} scenes")
            return

        # Generate images
        print(f"Generating images for {len(scenes_data['scenes'])} scenes...")

        from openai_responses_image_client import OpenAIResponsesImageClient
        client = OpenAIResponsesImageClient()

        total_cost = 0.0
        for i, scene in enumerate(scenes_data['scenes'], 1):
            scene_id = f"scene_{scene['scene_id']:03d}"
            print(f"  [{i}/{len(scenes_data['scenes'])}] {scene_id}...", end=' ', flush=True)

            b64_data = client.generate_with_style_reference(
                prompt=scene['video_description'],
                style_reference_path=str(self.args.art_reference),
                model='gpt-4o',
                size="1536x1024"
            )

            image_path = output_dir / f"{scene_id}.png"
            client.save_base64_image(b64_data, str(image_path))

            total_cost += 0.15  # Approximate cost per image
            print("✓")

        # Mark complete
        fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
        self.cache.mark_stage_complete(output_dir, fingerprint, cost=total_cost,
                                      metadata={'scene_count': len(scenes_data['scenes'])})

    def _do_scene_generation(self):
        """Placeholder for actual scene generation."""
        return {
            'episode': {'title': 'Test', 'context': '...'},
            'scenes': [
                {'scene_id': 1, 'narration': 'Test scene 1', 'video_description': '...'},
                {'scene_id': 2, 'narration': 'Test scene 2', 'video_description': '...'}
            ]
        }


def main():
    """Demonstrate V2 caching."""
    print("=" * 80)
    print("CACHE MANAGER V2 - Deterministic Caching Demo")
    print("=" * 80)
    print()

    # Setup
    class Args:
        text = '../resources/stories/gutenberg/01_the_call_of_cthulhu.txt'
        art_reference = '../resources/styles/vg_converted.jpg'
        audio_reference = '../resources/voices/sam-deep.mp3'
        narration_style = "Deep gravelly voice"
        art_style = None
        length = 120
        audio_workers = 1
        image_quality = 'medium'
        mode = 'slides'

    args = Args()
    output_dir = Path('../output/cache_demo')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create pipeline
    pipeline = PipelineWithCaching(args, output_dir)

    # First run - will generate
    print("FIRST RUN - Generating everything")
    print("-" * 80)
    scenes_data = pipeline.generate_scenes()
    print()

    # Second run - should use cache
    print("\nSECOND RUN - Should use cache")
    print("-" * 80)
    scenes_data = pipeline.generate_scenes()
    print()

    # Show cache summary
    print("\nCACHE SUMMARY")
    print("-" * 80)
    summary = pipeline.cache.get_cache_summary()
    print(f"Total cost: ${summary['total_cost']:.2f}")
    for stage, info in summary['stages'].items():
        status = info['status']
        cost = info['cost']
        fp = info['fingerprint']
        print(f"  {stage:30s} {status:10s} ${cost:.2f}  fp:{fp}")
    print()

    # Show fingerprint files
    print("\nFINGERPRINT FILES")
    print("-" * 80)
    for fp_file in output_dir.rglob('.fingerprint.json'):
        with open(fp_file, 'r') as f:
            data = json.load(f)
        print(f"  {fp_file.relative_to(output_dir)}")
        print(f"    Fingerprint: {data['hash']}")
        print(f"    Inputs: {', '.join(data['inputs'].keys())}")
        print(f"    Params: {', '.join(data['params'].keys())}")
        print()


if __name__ == '__main__':
    main()
