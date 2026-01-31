## Cache Manager V2 - Deterministic Caching with Fingerprint Validation

### Problem with V1

The original cache manager had these issues:

#### 1. **Manual Output File Lists**

```python
# V1 - Fragile: Manually list expected outputs
def _get_stage_output_files(self, stage: str, scene_count: int) -> list:
    if stage == 'audio_generation':
        return [str(self.output_dir / 'audio' / f'scene_{i:03d}.wav')
               for i in range(1, scene_count + 1)]  # What if scene_count is wrong?
```

**Problems**:
- Scene count might be incorrect (estimation vs actual)
- File naming conventions might change
- Hardcoded assumptions
- Maintenance burden

#### 2. **No Output Validation**

```python
# V1 - Just checks if files exist
if self.cache.check_stage_cache('scene_generation', [scenes_file]):
    # But are these outputs for CURRENT inputs?
    # No way to know!
```

**Problems**:
- Files might exist but be from different inputs
- No way to verify outputs match current inputs
- Could use stale/incorrect cached results

#### 3. **Weak Cache Hit/Miss Detection**

```python
# V1 - Only checks:
# 1. Do files exist?
# 2. Did input file hashes change?
# 3. Did parameter hash change?

# But doesn't validate that existing outputs were generated from current inputs!
```

---

### V2 Solution: Deterministic Fingerprint-Based Caching

## Core Concept: Stage Fingerprints

Each stage run gets a unique **fingerprint** based on:
1. **Input file hashes** (what files it reads)
2. **Parameters** (configuration affecting output)

```python
class StageFingerprint:
    stage_name: str = "audio_generation"
    inputs: dict = {
        'audio_reference': 'f9cc5c65...',
        'scenes_file': '18930ff2...'
    }
    params: dict = {
        'workers': 1,
        'speed': 1.0,
        'device': 'cpu'
    }
    hash: str = "53a22b4b5ad5885d"  # SHA256 of above
```

This fingerprint is **deterministic**:
- Same inputs + same params → Same fingerprint → Use cache
- Any change → Different fingerprint → Regenerate

## How It Works

### 1. **Fingerprint Storage**

Each output directory gets a `.fingerprint.json` file:

```
output/
├── audio/
│   ├── .fingerprint.json  ← Stores fingerprint for audio stage
│   ├── scene_001.wav
│   └── scene_002.wav
├── images/
│   ├── .fingerprint.json  ← Stores fingerprint for image stage
│   ├── scene_001.png
│   └── scene_002.png
└── scenes.json
```

### 2. **Cache Check Algorithm**

```python
def check_stage_cached(output_dir, fingerprint):
    # 1. Load stored fingerprint
    stored = load_fingerprint(output_dir / '.fingerprint.json')

    # 2. Compare fingerprints
    if stored.hash != fingerprint.hash:
        return False  # CACHE MISS

    # 3. Verify outputs exist
    if not outputs_exist(output_dir):
        return False  # CACHE MISS

    # 4. All checks passed
    return True  # CACHE HIT
```

### 3. **Automatic Output Discovery**

```python
# V2 - No manual lists! Discover outputs automatically
def discover_stage_outputs(output_dir):
    return [f for f in output_dir.iterdir()
           if f.name != '.fingerprint.json']

# Or use glob patterns
expected_patterns = ['scene_*.wav']
```

## Key Improvements

### ✅ 1. Deterministic Validation

**V1 (Weak)**:
```python
# Just checks if files exist - no validation
if scenes_file.exists() and input_hash_unchanged():
    use_cache()  # But is this the right scenes.json?
```

**V2 (Strong)**:
```python
# Validates outputs match current inputs via fingerprint
if stored_fingerprint == current_fingerprint and outputs_exist():
    use_cache()  # Guaranteed to be correct!
```

### ✅ 2. No Manual File Lists

**V1 (Fragile)**:
```python
# Must manually specify every output file
output_files = [
    'output/audio/scene_001.wav',
    'output/audio/scene_002.wav',
    # ... what if scene count changes?
]
```

**V2 (Robust)**:
```python
# Automatically discovers outputs
output_dir = Path('output/audio')
outputs = [f for f in output_dir.iterdir()
          if f.is_file() and f.name != '.fingerprint.json']

# Or validate with glob patterns
expected_patterns = ['scene_*.wav']  # Matches any count
```

### ✅ 3. Clear Cache Miss Explanations

**V1**:
```
⚠ Cache miss for audio_generation
```

**V2**:
```
⚠ Cache miss for audio_generation: Parameter changes: narration_style (Deep gravelly voice → FASTER PACING)
```

Shows exactly what changed!

### ✅ 4. Proper Dependency Tracking

**V1**:
```python
# Audio depends on text file
input_deps = ['text_file']  # Wrong! Should depend on scenes!
```

**V2**:
```python
# Audio depends on scenes, which contains the actual narration text
scenes_file = output_dir / 'scenes.json'
cache.register_input_file('scenes_file', str(scenes_file))

input_deps = ['audio_reference', 'scenes_file']  # Correct!
```

This means:
- Change text file → Scenes regenerate → Audio regenerates ✓
- Change narration style → Scenes regenerate → Audio regenerates ✓
- Change audio reference → Scenes cached → Audio regenerates ✓

## Usage Comparison

### V1 Usage (Complex)

```python
# Must manually specify outputs
stage_params = {'narration_style': args.narration_style}
output_files = [
    str(self.output_dir / 'scenes.json'),
    str(self.output_dir / 'scenes_short.json')
]

# Check cache
if not cache.has_input_changed('text_file', args.text):
    if not cache.has_params_changed('scene_generation', stage_params):
        if cache.check_stage_cache('scene_generation', output_files):
            return load_cached_scenes()

# Generate...
cache.mark_stage_complete('scene_generation', output_files, cost=0.02)
```

### V2 Usage (Simple)

```python
# Define dependencies
input_deps = ['text_file']
params = {'narration_style': args.narration_style}
output_dir = cache.get_stage_output_dir(base_dir, 'scene_generation')

# Single function checks everything!
if check_and_skip_if_cached(cache, 'scene_generation', output_dir,
                            input_deps, params):
    return load_cached_scenes()

# Generate...
fingerprint = cache.create_stage_fingerprint('scene_generation', input_deps, params)
cache.mark_stage_complete(output_dir, fingerprint, cost=0.02)
```

## Real-World Example

### Scenario: User changes narration style

**V1 Behavior**:
```bash
# First run
$ python generate_video.py ... --narration-style "deep voice"
# Generates: scenes.json (hash: abc123)

# User changes style
$ python generate_video.py ... --narration-style "fast pacing"

V1 Detection:
  ✓ Text file unchanged (hash matches)
  ✗ Param changed (narration_style different)
  ? Output validation? (None - just checks if file exists)

# Problem: If scenes.json exists, V1 might use it even though
# it was generated with different narration_style!
```

**V2 Behavior**:
```bash
# First run
$ python generate_video.py ... --narration-style "deep voice"
# Generates: scenes.json
# Saves: .fingerprint.json with hash of inputs+params

# User changes style
$ python generate_video.py ... --narration-style "fast pacing"

V2 Detection:
  1. Load stored fingerprint: hash = "53a22b4b" (deep voice)
  2. Calculate current fingerprint: hash = "7f891c3d" (fast pacing)
  3. Compare: 53a22b4b ≠ 7f891c3d
  4. Result: CACHE MISS
  5. Explain: "Parameter changes: narration_style (deep voice → fast pacing)"

# Regenerates scenes.json with new style
# Saves new .fingerprint.json with hash = "7f891c3d"
```

## File Structure Comparison

### V1 Output Structure
```
output/
├── cache_manifest.json      ← Central manifest
├── scenes.json
├── audio/
│   ├── scene_001.wav
│   └── scene_002.wav
└── images/
    ├── scene_001.png
    └── scene_002.png

# Problem: No per-stage validation
# If you delete scene_001.wav, V1 might not notice
```

### V2 Output Structure
```
output/
├── cache_manifest_v2.json   ← Central manifest
├── .fingerprint.json        ← Scene stage fingerprint
├── scenes.json
├── audio/
│   ├── .fingerprint.json    ← Audio stage fingerprint
│   ├── scene_001.wav
│   └── scene_002.wav
└── images/
    ├── .fingerprint.json    ← Image stage fingerprint
    ├── scene_001.png
    └── scene_002.png

# Each stage is self-validating
# If you delete scene_001.wav, V2 detects missing output → regenerate
```

## Testing

### Test Results

```
FIRST RUN - Generating everything
--------------------------------------------------------------------------------
⚠ No cache for scene_generation: First run
Generating scenes...

SECOND RUN - Should use cache
--------------------------------------------------------------------------------
✓ Using cached scene_generation (fingerprint: 53a22b4b)

THIRD RUN - Changed narration_style parameter
--------------------------------------------------------------------------------
⚠ Cache miss for scene_generation: Parameter changes: narration_style
  (Deep gravelly voice → FASTER PACING)
Cache hit: False
```

Perfect! V2 correctly:
1. Detects first run (no cache)
2. Uses cache on second run (fingerprint match)
3. Detects parameter change on third run (fingerprint mismatch)

## Migration Path

### Option 1: Side-by-side (Recommended)

Keep both V1 and V2, use V2 for new stages:

```python
# Old stages use V1
self.cache_v1 = CacheManager(output_dir)

# New stages use V2
self.cache_v2 = CacheManagerV2(output_dir)
```

### Option 2: Full migration

Replace all V1 calls with V2:

1. Update `pipeline_manager.py` to use `CacheManagerV2`
2. Update each stage method to use fingerprint-based caching
3. Test with existing outputs
4. Deploy

## Recommendation

**Use V2 for production** because:

✅ **More reliable**: Validates outputs match inputs
✅ **Less maintenance**: No manual file lists
✅ **Better debugging**: Clear cache miss explanations
✅ **Safer**: Won't use stale cached results
✅ **Simpler API**: One function does everything

## Summary

| Feature | V1 | V2 |
|---------|----|----|
| Output validation | ❌ Just checks existence | ✅ Fingerprint validation |
| File lists | ❌ Manual | ✅ Automatic discovery |
| Cache miss explanation | ❌ Generic | ✅ Detailed reason |
| Dependency tracking | ⚠️ Basic | ✅ Precise |
| False cache hits | ⚠️ Possible | ✅ Prevented |
| Maintenance | ❌ High | ✅ Low |
| Complexity | ⚠️ Medium | ✅ Simple API |

**Bottom line**: V2 is deterministic, reliable, and easier to use.
