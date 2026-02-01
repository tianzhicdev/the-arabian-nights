"""
Cached Pipeline Manager - Pipeline with intelligent caching

This is an example implementation showing how to integrate
cache_manager and status_display into the existing pipeline.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

from src.utils.cache_manager import CacheManager
from src.utils.status_display import StatusDisplay, StageInfo, estimate_stage_cost, estimate_stage_time


class CachedPipelineManager:
    """Pipeline manager with intelligent caching."""

    def __init__(self, args, output_dir):
        """Initialize cached pipeline manager."""
        self.args = args
        self.output_dir = Path(output_dir)

        # Initialize cache and status
        self.cache = CacheManager(self.output_dir)
        self.status = StatusDisplay(use_colors=True)

        # Register inputs
        self._register_inputs()

    def _register_inputs(self):
        """Register all input files with cache manager."""
        self.cache.register_input_file('text_file', self.args.text)
        self.cache.register_input_file('scenes_file', self.args.scenes)
        self.cache.register_input_file('art_reference', self.args.art_reference)
        self.cache.register_input_file('audio_reference', self.args.audio_reference)
        self.cache.register_input_file('static_background', self.args.static_background)

    def _estimate_scene_count(self) -> int:
        """Estimate number of scenes."""
        if self.args.scenes:
            try:
                with open(self.args.scenes, 'r') as f:
                    data = json.load(f)
                    return len(data.get('scenes', []))
            except:
                pass

        # Estimate based on text length
        if self.args.text:
            try:
                with open(self.args.text, 'r') as f:
                    text = f.read()
                    # Rough estimate: 100 words per minute, 1 scene per minute
                    word_count = len(text.split())
                    minutes = word_count / 100
                    return max(1, int(minutes))
            except:
                pass

        # Default estimate
        return 5

    def _build_status_dashboard(self):
        """Build status dashboard with all stages."""
        scene_count = self._estimate_scene_count()

        # Test mode reduces scene count
        if self.args.test:
            scene_count = min(3, scene_count)

        stages = [
            StageInfo(
                name='scene_generation',
                display_name='1. Scene Generation',
                status=self.cache.get_stage_status('scene_generation') or 'pending',
                time_estimate=10.0,
                cost_estimate=0.02
            ),
            StageInfo(
                name='test_trimming',
                display_name='2. Test Mode Trimming',
                status='skipped' if not self.args.test else 'pending',
                time_estimate=0.5 if self.args.test else 0,
                cost_estimate=0.0
            ),
            StageInfo(
                name='audio_generation',
                display_name='3. Audio Generation',
                status=self.cache.get_stage_status('audio_generation') or 'pending',
                time_estimate=estimate_stage_time('audio_generation', scene_count,
                                                 self.args.mode, self.args.audio_workers),
                cost_estimate=0.0
            ),
            StageInfo(
                name='image_generation',
                display_name='4. Image Generation',
                status=self.cache.get_stage_status('image_generation') or 'pending',
                time_estimate=estimate_stage_time('image_generation', scene_count, self.args.mode)
                             if self.args.art_reference else 0,
                cost_estimate=estimate_stage_cost('image_generation', scene_count, self.args.mode)
                             if self.args.art_reference else 0
            ),
            StageInfo(
                name='video_generation',
                display_name='5. Video Generation',
                status=self.cache.get_stage_status('video_generation') or 'pending',
                time_estimate=estimate_stage_time('video_generation', scene_count, self.args.mode),
                cost_estimate=estimate_stage_cost('video_generation', scene_count, self.args.mode)
            ),
            StageInfo(
                name='assembly',
                display_name='6. Assembly',
                status=self.cache.get_stage_status('assembly') or 'pending',
                time_estimate=5.0,
                cost_estimate=0.0
            )
        ]

        # Update status based on cache checks
        for stage_info in stages:
            # Skip if already marked as skipped
            if stage_info.status == 'skipped':
                continue

            # Check if stage is cached
            output_files = self._get_stage_output_files(stage_info.name, scene_count)
            if self.cache.check_stage_cache(stage_info.name, output_files):
                stage_info.status = 'cached'
                stage_info.cache_reason = "Output exists and inputs unchanged"

        # Add to status display
        for stage in stages:
            self.status.add_stage(stage)

    def _get_stage_output_files(self, stage: str, scene_count: int) -> list:
        """Get expected output files for a stage."""
        if stage == 'scene_generation':
            return [str(self.output_dir / 'scenes.json')]
        elif stage == 'test_trimming':
            return [str(self.output_dir / 'scenes_short.json')]
        elif stage == 'audio_generation':
            return [str(self.output_dir / 'audio' / f'scene_{i:03d}.wav')
                   for i in range(1, scene_count + 1)]
        elif stage == 'image_generation':
            return [str(self.output_dir / 'images' / f'scene_{i:03d}.png')
                   for i in range(1, scene_count + 1)]
        elif stage == 'video_generation':
            suffix = self.args.mode  # 'static', 'slides', or 'video'
            return [str(self.output_dir / 'video' / f'scene_{i:03d}_{suffix}.mp4')
                   for i in range(1, scene_count + 1)]
        elif stage == 'assembly':
            # Assembly output depends on episode title, which we don't know yet
            # Return empty list - we'll skip caching for assembly
            return []
        return []

    def _get_input_changes(self) -> dict:
        """Get dictionary of input changes."""
        changes = {}

        inputs = {
            'text_file': self.args.text,
            'scenes_file': self.args.scenes,
            'art_reference': self.args.art_reference,
            'audio_reference': self.args.audio_reference,
            'static_background': self.args.static_background
        }

        for name, path in inputs.items():
            if path is None:
                continue

            old_info = self.cache.manifest['inputs'].get(name, {})
            old_hash = old_info.get('hash')
            new_hash = self.cache._hash_file(path) if path else None

            changes[name] = {
                'changed': old_hash != new_hash,
                'old_hash': old_hash,
                'new_hash': new_hash,
                'path': path
            }

        # Check parameter changes for key stages
        if self.args.text:
            scene_params = {
                'length': self.args.length,
                'art_style': self.args.art_style or "default",
                'narration_style': self.args.narration_style
            }
            changes['scene_parameters'] = {
                'changed': self.cache.has_params_changed('scene_generation', scene_params),
                'old_hash': self.cache.manifest.get('stages', {}).get('scene_generation', {}).get('param_hash'),
                'new_hash': self.cache._hash_params(scene_params),
                'path': 'N/A'
            }

        return changes

    def _show_status_dashboard(self):
        """Show pre-run status dashboard."""
        # Build dashboard
        self._build_status_dashboard()

        # Get title if available
        title = None
        if self.args.scenes:
            try:
                with open(self.args.scenes, 'r') as f:
                    data = json.load(f)
                    title = data.get('episode', {}).get('title')
            except:
                pass

        # Print header
        self.status.print_header(str(self.output_dir), title=title)

        # Print input changes
        input_changes = self._get_input_changes()
        self.status.print_input_changes(input_changes)

        # Print stage summary
        self.status.print_stage_summary(verbose=True)

        # Generate warnings
        warnings = []
        total_cost = sum(s.cost_estimate for s in self.status.stages
                        if s.status not in ['cached', 'skipped'])
        total_time = sum(s.time_estimate for s in self.status.stages
                        if s.status not in ['cached', 'skipped'])

        if total_cost > 10.0:
            warnings.append(f"High cost operation: ~${total_cost:.2f}")
        if total_cost > 50.0:
            warnings.append(f"VERY HIGH COST! Consider using --mode slides instead of --mode video")
        if total_time > 600:
            warnings.append(f"Long operation: ~{total_time/60:.0f} minutes")

        # Check for changes that will trigger regeneration
        any_changed = any(info.get('changed', False) for info in input_changes.values())
        if any_changed:
            changed_inputs = [name for name, info in input_changes.items()
                            if info.get('changed', False)]
            warnings.append(f"Input changes detected: {', '.join(changed_inputs)}")

        self.status.print_warnings(warnings)

        # Recommendations
        recommendations = []
        cached_count = sum(1 for s in self.status.stages if s.status == 'cached')
        if cached_count > 0:
            recommendations.append(f"Using {cached_count} cached stages - saving ${self.cache.get_total_cost():.2f}")

        if self.args.mode == 'video' and not self.args.test:
            recommendations.append("Consider using --test flag for quick iteration (3 scenes only)")

        self.status.print_recommendations(recommendations)
        self.status.print_footer('continue')

    def run(self):
        """Execute the full pipeline with caching."""
        # Show status dashboard
        print()
        self._show_status_dashboard()

        # Continue with normal pipeline execution
        # (This would call the original PipelineManager methods with caching logic)
        print("Pipeline would execute here...")
        print("(Integration with existing PipelineManager needed)")
        print()


# Example usage showing how to create the manager
if __name__ == '__main__':
    import argparse

    # Simplified args for demonstration
    class Args:
        def __init__(self):
            self.text = 'resources/stories/gutenberg/01_the_call_of_cthulhu.txt'
            self.scenes = None
            self.art_reference = 'resources/styles/vg_converted.jpg'
            self.audio_reference = 'resources/voices/sam-deep.mp3'
            self.static_background = None
            self.narration_style = "Deep gravelly baritone"
            self.art_style = None
            self.mode = 'slides'
            self.length = 120
            self.test = True
            self.audio_workers = 1

    args = Args()
    output_dir = 'output/gutenberg/01_call_of_cthulhu'

    # Create cached pipeline
    pipeline = CachedPipelineManager(args, output_dir)
    pipeline.run()
