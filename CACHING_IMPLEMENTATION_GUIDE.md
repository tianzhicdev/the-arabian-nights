# Caching & Status Implementation Guide

## Overview

This guide explains how to implement intelligent caching and status reporting in the video generation pipeline to avoid re-running expensive operations when inputs haven't changed.

## Architecture

### 1. Cache Manager (`cache_manager.py`)

**Purpose**: Track inputs, parameters, and outputs using content-based hashing

**Key Features**:
- Content hashing of input files (text, art reference, audio reference)
- Parameter hashing (narration style, mode, quality settings)
- Output tracking with file hashes
- Cost tracking per stage
- Manifest persistence (`cache_manifest.json`)

**Usage**:
```python
from cache_manager import CacheManager

cache = CacheManager(output_dir)

# Register inputs
cache.register_input_file('text_file', args.text)
cache.register_input_file('art_reference', args.art_reference)

# Check if stage can be skipped
stage_params = {'narration_style': args.narration_style, 'length': args.length}
if not cache.has_params_changed('scene_generation', stage_params):
    if cache.check_stage_cache('scene_generation', [scenes_file]):
        print("✓ Using cached scenes")
        return load_cached_scenes()

# Mark stage progress
cache.mark_stage_start('scene_generation', stage_params)
# ... do work ...
cache.mark_stage_complete('scene_generation', [scenes_file], cost=0.02)
```

### 2. Status Display (`status_display.py`)

**Purpose**: Provide rich visual feedback on pipeline status

**Key Features**:
- Color-coded status indicators
- Cost and time estimates
- Cache hit/miss reporting
- Progress tracking
- Warnings and recommendations

**Usage**:
```python
from status_display import StatusDisplay, StageInfo, estimate_stage_cost

status = StatusDisplay(use_colors=True)

# Add stages
status.add_stage(StageInfo(
    name='scene_generation',
    display_name='1. Scene Generation',
    status='pending',
    time_estimate=10.0,
    cost_estimate=0.02
))

# Print status dashboard
status.print_header(output_dir, title="The Call of Cthulhu")
status.print_input_changes(input_changes)
status.print_stage_summary(verbose=True)
```

## Implementation Steps

### Step 1: Add Cache Manager to Pipeline

Modify `pipeline_manager.py`:

```python
from cache_manager import CacheManager
from status_display import StatusDisplay, StageInfo, estimate_stage_cost, estimate_stage_time

class PipelineManager:
    def __init__(self, args, output_dir):
        self.args = args
        self.output_dir = Path(output_dir)

        # NEW: Initialize cache and status
        self.cache = CacheManager(self.output_dir)
        self.status = StatusDisplay(use_colors=True)

        # Register all inputs at startup
        self._register_inputs()
        self._build_status_dashboard()
```

### Step 2: Register Inputs

```python
def _register_inputs(self):
    """Register all input files with cache manager."""
    self.cache.register_input_file('text_file', self.args.text)
    self.cache.register_input_file('scenes_file', self.args.scenes)
    self.cache.register_input_file('art_reference', self.args.art_reference)
    self.cache.register_input_file('audio_reference', self.args.audio_reference)
    self.cache.register_input_file('static_background', self.args.static_background)
```

### Step 3: Add Smart Caching to Each Stage

Example for Scene Generation:

```python
def generate_scenes(self):
    """Generate scenes from text with caching."""
    stage_name = 'scene_generation'

    # Define stage parameters (everything that affects output)
    stage_params = {
        'text_file': self.args.text,
        'length': self.args.length,
        'art_style': self.args.art_style or "default",
        'narration_style': self.args.narration_style
    }

    # Check cache
    scenes_file = self.output_dir / 'scenes.json'

    # Check if inputs/params changed
    text_changed = self.cache.has_input_changed('text_file', self.args.text)
    params_changed = self.cache.has_params_changed(stage_name, stage_params)

    if not text_changed and not params_changed:
        if self.cache.check_stage_cache(stage_name, [str(scenes_file)]):
            print("─" * 80)
            print("STAGE 1: Scene Generation")
            print("─" * 80)
            print("✓ Using cached scenes (inputs unchanged)")
            print()

            with open(scenes_file, 'r') as f:
                return json.load(f)

    # If we're here, we need to regenerate
    print("─" * 80)
    print("STAGE 1: Scene Generation")
    print("─" * 80)

    if text_changed:
        print("⚠ Text file changed, regenerating scenes")
    if params_changed:
        print("⚠ Parameters changed, regenerating scenes")
    print()

    # Mark stage start
    self.cache.mark_stage_start(stage_name, stage_params)

    try:
        # Do the actual work
        scenes_data = self._do_scene_generation()

        # Mark complete with cost
        self.cache.mark_stage_complete(
            stage_name,
            [str(scenes_file)],
            cost=0.02,
            metadata={'scene_count': len(scenes_data['scenes'])}
        )

        return scenes_data

    except Exception as e:
        self.cache.mark_stage_failed(stage_name, str(e))
        raise
```

### Step 4: Add Status Dashboard

Add to the beginning of `run()`:

```python
def run(self):
    """Execute the full pipeline with caching and status display."""

    # Build status dashboard
    self._show_status_dashboard()

    # Ask for confirmation if expensive ops are needed
    if self._has_expensive_work():
        if not self._confirm_proceed():
            print("Pipeline aborted by user")
            return

    # Run pipeline stages...
```

### Step 5: Build Status Dashboard

```python
def _build_status_dashboard(self):
    """Build and display status dashboard."""
    scene_count = self._estimate_scene_count()

    # Add all stages
    stages = [
        StageInfo('scene_generation', '1. Scene Generation',
                 'pending', 10, 0.02),
        StageInfo('audio_generation', '3. Audio Generation',
                 'pending',
                 estimate_stage_time('audio_generation', scene_count,
                                   self.args.mode, self.args.audio_workers),
                 0.0),
        StageInfo('image_generation', '4. Image Generation',
                 'pending',
                 estimate_stage_time('image_generation', scene_count, self.args.mode),
                 estimate_stage_cost('image_generation', scene_count, self.args.mode)),
        # ... add other stages
    ]

    for stage in stages:
        self.status.add_stage(stage)

def _show_status_dashboard(self):
    """Show pre-run status dashboard."""
    self.status.print_header(str(self.output_dir),
                            title=self._get_title())

    # Check input changes
    input_changes = {
        'text_file': {
            'changed': self.cache.has_input_changed('text_file', self.args.text),
            'path': self.args.text,
            'old_hash': self.cache.manifest['inputs'].get('text_file', {}).get('hash'),
            'new_hash': self.cache._hash_file(self.args.text) if self.args.text else None
        },
        # ... check other inputs
    }

    self.status.print_input_changes(input_changes)
    self.status.print_stage_summary(verbose=True)

    # Generate warnings
    warnings = []
    if self._estimate_total_cost() > 10.0:
        warnings.append(f"High cost operation: ~${self._estimate_total_cost():.2f}")
    if self._estimate_total_time() > 600:
        warnings.append(f"Long operation: ~{self._estimate_total_time()/60:.0f} minutes")

    self.status.print_warnings(warnings)
    self.status.print_footer('continue')
```

## Cache Invalidation Strategies

### Automatic Invalidation

The cache automatically invalidates when:
1. Input file hash changes
2. Parameter hash changes
3. Output file is missing or corrupted

### Manual Invalidation

Force regeneration with command-line flags:

```bash
# Regenerate specific stage
python generate_video.py --invalidate-stage audio_generation ...

# Clear all cache
python generate_video.py --clear-cache ...

# Regenerate specific scene
python generate_video.py --rerun-scene scene_003 ...
```

Implementation:

```python
# Add to argument parser
parser.add_argument('--invalidate-stage', type=str,
                   choices=['scene', 'audio', 'image', 'video', 'assembly'],
                   help='Force regeneration of specific stage')
parser.add_argument('--clear-cache', action='store_true',
                   help='Clear all cache and regenerate everything')

# In pipeline:
if args.invalidate_stage:
    self.cache.invalidate_stage(args.invalidate_stage, "Manual invalidation")

if args.clear_cache:
    self.cache.manifest = self.cache._create_empty_manifest()
    self.cache._save_manifest()
```

## Manifest File Structure

The `cache_manifest.json` file stores:

```json
{
  "version": "1.0",
  "created_at": "2026-01-28T15:30:00",
  "updated_at": "2026-01-28T15:45:00",
  "inputs": {
    "text_file": {
      "path": "resources/stories/gutenberg/01_the_call_of_cthulhu.txt",
      "hash": "a3f5b2c8d1e9",
      "updated_at": "2026-01-28T15:30:00"
    },
    "art_reference": {
      "path": "resources/styles/vg_converted.jpg",
      "hash": "9c2d1e4f6a8b",
      "updated_at": "2026-01-28T15:30:00"
    }
  },
  "stages": {
    "scene_generation": {
      "status": "completed",
      "params": {
        "text_file": "...",
        "length": 120,
        "art_style": "...",
        "narration_style": "..."
      },
      "param_hash": "7d3a8f9c2e1b",
      "started_at": "2026-01-28T15:30:05",
      "completed_at": "2026-01-28T15:30:15",
      "output_files": ["output/scenes.json"],
      "output_hashes": {
        "output/scenes.json": "5e2f8a9c1d3b"
      },
      "cost": 0.02,
      "metadata": {
        "scene_count": 2
      }
    }
  },
  "costs": {
    "total": 0.42,
    "by_stage": {
      "scene_generation": 0.02,
      "image_generation": 0.40
    }
  }
}
```

## Cost Estimation Table

| Operation | Model | Cost per Unit | Notes |
|-----------|-------|---------------|-------|
| Scene Generation | Claude Sonnet 4.5 | $0.02/request | One request per file |
| Audio Generation | Chatterbox (local) | $0.00 | Free, ~20s/scene on CPU |
| Image Generation | GPT-Image-1.5 | $0.10-0.30/image | Depends on quality setting |
| Video (Slides) | FFmpeg | $0.00 | Free, ~2s/scene |
| Video (Sora) | Sora 2 | $10-20/video | Very expensive! |
| Assembly | FFmpeg | $0.00 | Free, ~5s total |

## Example Output

```
================================================================================
PIPELINE STATUS: output/gutenberg/01_call_of_cthulhu
Title: The Call of Cthulhu
================================================================================

Input Changes:
  ✓ text_file           unchanged (hash: a3f5b2c8)
  ✓ art_reference       unchanged (hash: 9c2d1e4f)
  ✗ narration_style     CHANGED (7d3a8f → 2e1b5c9a)

Stage Status:
  [✓] 1. Scene Generation           -       $0.02   CACHED
  [✓] 2. Test Trimming              -        -      CACHED
  [⟳] 3. Audio Generation          40s       -      RUNNING
  [✓] 4. Image Generation           -       $0.40   CACHED
  [⊗] 5. Video Generation          4s        -      PENDING
  [⊗] 6. Assembly                  5s        -      PENDING

Estimated Total Time: 49s (0:00:49)
Estimated Total Cost: $0.00
Cache Hits: 3/6 stages

Warnings:
  ⚠  Narration style changed - will regenerate audio for 2 scenes

================================================================================
Ready to proceed? Pipeline will skip cached stages.
================================================================================
```

## Benefits

1. **Cost Savings**: Skip expensive API calls when inputs unchanged
2. **Time Savings**: Reuse cached results (e.g., 40s audio generation → 0s)
3. **Transparency**: See exactly what will run and why
4. **Safety**: Review costs before expensive operations
5. **Debugging**: Track which inputs caused regeneration
6. **Incremental Builds**: Change one parameter, only rebuild affected stages

## Next Steps

1. Integrate `CacheManager` into `PipelineManager.__init__()`
2. Add caching logic to each stage method
3. Add status dashboard to `run()` method
4. Add command-line flags for cache control
5. Test with real workflows
6. Document cache behavior in user guide

## Testing

Test scenarios:
1. ✅ Run pipeline twice with same inputs → all cached
2. ✅ Change text file → regenerate scenes + downstream
3. ✅ Change narration style → regenerate audio only
4. ✅ Change art reference → regenerate images + videos
5. ✅ Delete output file → automatically regenerate
6. ✅ Manual invalidation with `--invalidate-stage`
7. ✅ Cost estimation accuracy
8. ✅ Time estimation accuracy
