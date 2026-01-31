# Caching & Status Solution Summary

## 🎯 Problem

Your video generation pipeline has expensive operations that shouldn't re-run if inputs haven't changed:

1. **Scene Generation**: OpenRouter API calls (~$0.02, 10s)
2. **Audio Generation**: Chatterbox inference (~20s per scene, CPU-bound)
3. **Image Generation**: GPT-Image API (~$0.15 per image, 8s)
4. **Video Generation (Sora)**: Extremely expensive (~$15 per video, 90s)

Running the same command twice would waste time and money regenerating identical outputs.

## ✅ Solution Implemented

### Three New Modules

#### 1. `cache_manager.py` - Smart Caching System

**Key Features**:
- Content-based hashing of inputs (text files, references)
- Parameter tracking (narration style, mode, quality)
- Stage completion tracking with cost accounting
- Automatic invalidation when inputs change
- Manifest persistence in `cache_manifest.json`

**Usage**:
```python
cache = CacheManager(output_dir)

# Check if stage can be skipped
if cache.check_stage_cache('scene_generation', [scenes_file]):
    print("✓ Using cached scenes")
    return load_cached_scenes()

# Otherwise run and mark complete
cache.mark_stage_complete('scene_generation', [scenes_file], cost=0.02)
```

#### 2. `status_display.py` - Visual Status Dashboard

**Key Features**:
- Color-coded status indicators (✓ cached, ⟳ running, ⊗ pending, ✗ failed)
- Input change detection with hash comparison
- Cost and time estimates per stage
- Cache hit/miss reporting
- Warnings and recommendations

**Sample Output**:
```
Input Changes:
  ✓ text_file            unchanged (hash: 18930ff2)
  ✓ art_reference        unchanged (hash: f9cc5c65)
  ✗ narration_style      CHANGED (7d3a8f → 2e1b5c9a)

Stage Status:
  [✓] 1. Scene Generation                -       $0.02   CACHED
  [✓] 3. Audio Generation               40s        -     RUNNING
  [✓] 4. Image Generation                -       $0.40   CACHED
  [⊗] 5. Video Generation                4s        -     PENDING

Estimated Total Time: 44s
Estimated Total Cost: $0.00
Cache Hits: 3/5 stages

Warnings:
  ⚠  Narration style changed - will regenerate audio

Recommendations:
  💡 Using 3 cached stages - saving $0.42
```

#### 3. `cached_pipeline_manager.py` - Integration Example

Shows how to integrate caching into your existing `PipelineManager`:

- Input registration on startup
- Cache checking before each stage
- Status dashboard before execution
- Cost/time warnings for expensive operations

## 📊 Cost Estimates

| Stage | Model/Tool | Cost | Time | Cacheable |
|-------|------------|------|------|-----------|
| Scene Generation | Claude Sonnet 4.5 | $0.02 | 10s | ✅ |
| Audio (2 scenes) | Chatterbox | Free | 40s | ✅ |
| Images (2 scenes) | GPT-Image-1.5 | $0.30 | 16s | ✅ |
| Video Slides (2 scenes) | FFmpeg | Free | 4s | ⚠️ Cheap |
| Video Sora (2 scenes) | Sora 2 | $30+ | 180s | ✅ |
| Assembly | FFmpeg | Free | 5s | ⚠️ Cheap |

**Total Savings with Cache**: Up to $30.32 per re-run (for Sora mode)

## 🚀 How Caching Works

### 1. Input Hashing

Each input file is hashed using SHA256:
```
text_file:          18930ff2... (first 12 chars)
art_reference:      f9cc5c65...
audio_reference:    4b0264d9...
```

### 2. Parameter Hashing

Stage parameters are serialized and hashed:
```json
{
  "length": 120,
  "art_style": "watercolor",
  "narration_style": "deep voice"
}
→ hash: 221e4207...
```

### 3. Change Detection

Before each stage:
1. Check if input files have changed (hash comparison)
2. Check if parameters have changed (hash comparison)
3. Check if output files exist
4. If all unchanged → SKIP (use cached)
5. If any changed → RUN (regenerate)

### 4. Cascade Invalidation

When an input changes, downstream stages are automatically invalidated:

```
Text file changed
  → Scene generation re-runs
    → Audio regenerates (scenes changed)
      → Video regenerates (audio changed)
        → Assembly re-runs (video changed)
```

But if only narration style changes:
```
Narration style changed
  ✓ Scenes unchanged (cached)
    → Audio regenerates (parameter changed)
      ✓ Images unchanged (cached)
        → Video regenerates (audio changed)
          → Assembly re-runs (video changed)
```

## 📁 Manifest File Structure

`cache_manifest.json` stores all state:

```json
{
  "version": "1.0",
  "created_at": "2026-01-28T15:30:00",
  "inputs": {
    "text_file": {
      "path": "resources/stories/01_story.txt",
      "hash": "18930ff2d5a3",
      "updated_at": "2026-01-28T15:30:00"
    }
  },
  "stages": {
    "scene_generation": {
      "status": "completed",
      "params": {"length": 120, "narration_style": "deep voice"},
      "param_hash": "221e4207c8f9",
      "output_files": ["output/scenes.json"],
      "output_hashes": {"output/scenes.json": "5e2f8a9c1d3b"},
      "cost": 0.02,
      "completed_at": "2026-01-28T15:30:15"
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

## 🔄 Integration Steps

### Step 1: Import Modules

```python
from cache_manager import CacheManager
from status_display import StatusDisplay, StageInfo
```

### Step 2: Initialize in Pipeline

```python
class PipelineManager:
    def __init__(self, args, output_dir):
        self.cache = CacheManager(output_dir)
        self.status = StatusDisplay(use_colors=True)
        self._register_inputs()
```

### Step 3: Add Caching to Stage

```python
def generate_scenes(self):
    stage_name = 'scene_generation'
    stage_params = {
        'text_file': self.args.text,
        'length': self.args.length,
        'narration_style': self.args.narration_style
    }

    # Check cache
    scenes_file = self.output_dir / 'scenes.json'
    if self.cache.check_stage_cache(stage_name, [str(scenes_file)]):
        if not self.cache.has_params_changed(stage_name, stage_params):
            print("✓ Using cached scenes")
            with open(scenes_file) as f:
                return json.load(f)

    # Run stage
    self.cache.mark_stage_start(stage_name, stage_params)
    scenes_data = self._do_scene_generation()
    self.cache.mark_stage_complete(stage_name, [str(scenes_file)], cost=0.02)

    return scenes_data
```

### Step 4: Show Status Before Run

```python
def run(self):
    # Show dashboard
    self._show_status_dashboard()

    # Execute stages...
```

## 🎛️ Command-Line Control

### Proposed Flags

```bash
# Force regeneration of specific stage
python generate_video.py --invalidate-stage audio_generation ...

# Clear all cache
python generate_video.py --clear-cache ...

# Show cache status without running
python generate_video.py --status-only ...

# Bypass cache check (always regenerate)
python generate_video.py --no-cache ...
```

## 📈 Expected Benefits

### Time Savings

**Scenario 1: No changes**
- Before: 75s (scene 10s + audio 40s + images 16s + video 4s + assembly 5s)
- After: 9s (video 4s + assembly 5s) - everything else cached
- **Savings: 88% faster**

**Scenario 2: Changed narration style only**
- Before: 75s (regenerate everything)
- After: 49s (audio 40s + video 4s + assembly 5s) - scenes/images cached
- **Savings: 35% faster**

### Cost Savings

**With Sora (expensive mode)**:
- First run: $30.32
- Cached re-run: $0.00
- **Savings: $30.32 per iteration**

**With Slides (cheap mode)**:
- First run: $0.32
- Cached re-run: $0.00
- **Savings: $0.32 per iteration**

### Development Workflow

```bash
# Initial run - generate everything
python generate_video.py ... --test
# Cost: $0.17, Time: 75s

# Tweak narration style
python generate_video.py ... --test --narration-style "faster pacing"
# Cost: $0.00, Time: 49s (scenes/images cached)

# Tweak art style
python generate_video.py ... --test --art-style "dark gothic"
# Cost: $0.15, Time: 30s (scenes/audio cached, images regenerate)

# Final full run
python generate_video.py ...  # remove --test
# Uses cached scenes/audio, generates full episode
```

## 🐛 Edge Cases Handled

1. **Missing output files**: Automatically regenerate even if manifest says complete
2. **Corrupted outputs**: Hash mismatch triggers regeneration
3. **Manual file deletion**: Detected by existence check
4. **Parameter changes**: Invalidates stage even if input files unchanged
5. **Downstream dependencies**: Changes cascade to dependent stages

## 📝 Implementation Checklist

- [x] Create `cache_manager.py` with content hashing
- [x] Create `status_display.py` with visual reporting
- [x] Create `cached_pipeline_manager.py` example
- [x] Write comprehensive implementation guide
- [ ] Integrate into existing `pipeline_manager.py`
- [ ] Add command-line flags (`--invalidate-stage`, `--clear-cache`, etc.)
- [ ] Add cost estimation to status dashboard
- [ ] Test with real workflows
- [ ] Update user documentation

## 🚦 Next Steps

### Option 1: Full Integration (Recommended)

Modify existing `pipeline_manager.py` to add caching to all stages.

**Effort**: 2-3 hours
**Benefit**: Complete caching system with status dashboard

### Option 2: Incremental Adoption

Add caching to most expensive stages first (image generation, video generation).

**Effort**: 1 hour
**Benefit**: Immediate cost savings on expensive operations

### Option 3: Manual Testing

Use `cached_pipeline_manager.py` as a parallel implementation for testing.

**Effort**: 30 minutes
**Benefit**: Validate approach before full integration

## 🎓 Example Workflow

```bash
# First run
$ python generate_video.py \\
    --text resources/stories/gutenberg/01_story.txt \\
    --mode slides \\
    --art-reference resources/styles/vg_converted.jpg \\
    --narration-style "deep gravelly voice" \\
    --audio-reference resources/voices/sam-deep.mp3 \\
    --output-dir output/story1 \\
    --test

# Output shows:
# - All stages pending
# - Estimated cost: $0.17, time: 75s
# - Runs all stages
# - Saves to cache_manifest.json

# Second run (no changes)
$ python generate_video.py [same args]

# Output shows:
# - All stages cached ✓
# - Estimated cost: $0.00, time: 9s
# - Skips expensive operations
# - Only runs assembly

# Third run (changed narration)
$ python generate_video.py [same args] \\
    --narration-style "faster pacing"

# Output shows:
# - Scenes cached ✓
# - Audio regenerating (param changed)
# - Images cached ✓
# - Estimated cost: $0.00, time: 49s
```

---

**Ready to integrate?** See `CACHING_IMPLEMENTATION_GUIDE.md` for detailed step-by-step instructions.
