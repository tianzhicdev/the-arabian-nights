# Quick Start: Integrate Cache Manager V2

## TL;DR

Your concern was correct: V1 cache detection wasn't deterministic enough.

**V2 fixes this by**:
- ✅ Storing fingerprints with outputs (`.fingerprint.json`)
- ✅ Validating outputs match current inputs
- ✅ Auto-discovering outputs (no manual file lists)
- ✅ Explaining cache misses clearly

## 5-Minute Integration

### Step 1: Import V2

```python
from cache_manager_v2 import CacheManagerV2, check_and_skip_if_cached
```

### Step 2: Initialize in Pipeline

```python
class PipelineManager:
    def __init__(self, args, output_dir):
        self.args = args
        self.output_dir = Path(output_dir)
        self.cache = CacheManagerV2(self.output_dir)

        # Register ALL inputs upfront
        self.cache.register_input_file('text_file', self.args.text)
        self.cache.register_input_file('art_reference', self.args.art_reference)
        self.cache.register_input_file('audio_reference', self.args.audio_reference)
```

### Step 3: Add to Each Stage (Template)

```python
def generate_STAGE(self):
    """Your stage method with caching."""
    stage_name = 'STAGE_NAME'

    # 1. Define what this stage depends on
    input_deps = ['text_file', ...]  # Input files this stage reads
    params = {
        'param1': self.args.param1,
        'param2': self.args.param2,
        # ... all parameters affecting output
    }

    # 2. Get output directory
    output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)

    # 3. Check cache (ONE LINE!)
    if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                input_deps, params):
        # Cache hit - load and return results
        return self._load_cached_results(output_dir)

    # 4. Cache miss - do the work
    print(f"Generating {stage_name}...")
    results = self._do_actual_work()

    # 5. Save outputs to output_dir
    self._save_results(output_dir, results)

    # 6. Mark complete (saves fingerprint)
    fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
    self.cache.mark_stage_complete(output_dir, fingerprint, cost=0.XX,
                                  metadata={'count': len(results)})

    return results
```

## Real Examples

### Scene Generation

```python
def generate_scenes(self):
    stage_name = 'scene_generation'

    # Dependencies: Just text file
    input_deps = ['text_file']
    params = {
        'length': self.args.length,
        'art_style': self.args.art_style or 'default',
        'narration_style': self.args.narration_style
    }

    output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)

    # Check cache
    if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                input_deps, params):
        scenes_file = output_dir / 'scenes.json'
        with open(scenes_file, 'r') as f:
            return json.load(f)

    # Generate
    print("Generating scenes...")
    scenes_data = self._do_scene_generation()

    # Save
    scenes_file = output_dir / 'scenes.json'
    with open(scenes_file, 'w') as f:
        json.dump(scenes_data, f, indent=2)

    # Mark complete
    fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
    self.cache.mark_stage_complete(output_dir, fingerprint, cost=0.02,
                                  metadata={'scene_count': len(scenes_data['scenes'])})

    return scenes_data
```

### Audio Generation

```python
def generate_audio(self, scenes_data):
    stage_name = 'audio_generation'

    # IMPORTANT: Register scenes as input (not text_file!)
    scenes_file = self.output_dir / 'scenes.json'
    self.cache.register_input_file('scenes_file', str(scenes_file))

    # Dependencies: Audio reference + scenes
    input_deps = ['audio_reference', 'scenes_file']
    params = {
        'workers': self.args.audio_workers,
        'speed': 1.0
    }

    output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)

    # Check cache with expected output pattern
    expected_patterns = ['scene_*.wav']
    if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                input_deps, params, expected_patterns):
        print(f"✓ Using cached audio")
        return

    # Generate
    print(f"Generating audio for {len(scenes_data['scenes'])} scenes...")
    from audio_generator import ParallelAudioGenerator

    generator = ParallelAudioGenerator(
        audio_prompt_path=self.args.audio_reference,
        max_workers=self.args.audio_workers
    )

    durations = generator.generate_all_scenes(
        scenes=scenes_data['scenes'],
        audio_dir=output_dir
    )

    # Mark complete
    fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
    self.cache.mark_stage_complete(output_dir, fingerprint, cost=0.0,
                                  metadata={'scene_count': len(durations)})
```

### Image Generation

```python
def generate_images(self, scenes_data):
    stage_name = 'image_generation'

    # Register scenes as input
    scenes_file = self.output_dir / 'scenes.json'
    self.cache.register_input_file('scenes_file', str(scenes_file))

    # Dependencies: Art reference + scenes
    input_deps = ['art_reference', 'scenes_file']
    params = {
        'model': 'gpt-4o',
        'quality': self.args.image_quality
    }

    output_dir = self.cache.get_stage_output_dir(self.output_dir, stage_name)
    expected_patterns = ['scene_*.png']

    # Check cache
    if check_and_skip_if_cached(self.cache, stage_name, output_dir,
                                input_deps, params, expected_patterns):
        print(f"✓ Using cached images")
        return

    # Generate
    print(f"Generating images for {len(scenes_data['scenes'])} scenes...")
    from openai_responses_image_client import OpenAIResponsesImageClient

    client = OpenAIResponsesImageClient()
    total_cost = 0.0

    for scene in scenes_data['scenes']:
        scene_id = f"scene_{scene['scene_id']:03d}"
        b64_data = client.generate_with_style_reference(
            prompt=scene['video_description'],
            style_reference_path=str(self.args.art_reference),
            model='gpt-4o'
        )

        image_path = output_dir / f"{scene_id}.png"
        client.save_base64_image(b64_data, str(image_path))
        total_cost += 0.15

    # Mark complete
    fingerprint = self.cache.create_stage_fingerprint(stage_name, input_deps, params)
    self.cache.mark_stage_complete(output_dir, fingerprint, cost=total_cost,
                                  metadata={'scene_count': len(scenes_data['scenes'])})
```

## How Cache Detection Works

### First Run
```
$ python generate_video.py --text story.txt --narration-style "deep voice"

Scene Generation:
  → No .fingerprint.json found
  → Generate scenes
  → Save to output/scenes.json
  → Save .fingerprint.json (hash: abc123)

Audio Generation:
  → No .fingerprint.json found
  → Generate audio
  → Save to output/audio/scene_*.wav
  → Save output/audio/.fingerprint.json (hash: def456)
```

### Second Run (Same Inputs)
```
$ python generate_video.py --text story.txt --narration-style "deep voice"

Scene Generation:
  → Load .fingerprint.json (hash: abc123)
  → Calculate current fingerprint (hash: abc123)
  → Match! ✓ Use cached scenes

Audio Generation:
  → Load output/audio/.fingerprint.json (hash: def456)
  → Calculate current fingerprint (hash: def456)
  → Match! ✓ Use cached audio
```

### Third Run (Changed Parameter)
```
$ python generate_video.py --text story.txt --narration-style "FAST PACING"

Scene Generation:
  → Load .fingerprint.json (hash: abc123)
  → Calculate current fingerprint (hash: xyz789)  ← Different!
  → Mismatch! ✗ Regenerate
  → Explain: "Parameter changes: narration_style (deep voice → FAST PACING)"
  → Save new .fingerprint.json (hash: xyz789)

Audio Generation:
  → scenes.json changed (abc123 → xyz789)
  → Regenerate audio with new scenes
```

## Output Structure

```
output/
├── cache_manifest_v2.json       ← Overall cache state
├── .fingerprint.json            ← Scene generation fingerprint
├── scenes.json                  ← Scene outputs
├── audio/
│   ├── .fingerprint.json        ← Audio generation fingerprint
│   ├── scene_001.wav
│   └── scene_002.wav
└── images/
    ├── .fingerprint.json        ← Image generation fingerprint
    ├── scene_001.png
    └── scene_002.png
```

Each `.fingerprint.json`:
```json
{
  "stage_name": "audio_generation",
  "hash": "def456abc789",
  "inputs": {
    "audio_reference": "f9cc5c65...",
    "scenes_file": "18930ff2..."
  },
  "params": {
    "workers": 1,
    "speed": 1.0
  }
}
```

## Key Points

### ✅ DO:

1. **Register intermediate files as inputs**
   ```python
   # Audio depends on scenes, not text
   scenes_file = output_dir / 'scenes.json'
   cache.register_input_file('scenes_file', str(scenes_file))
   ```

2. **Include ALL parameters that affect output**
   ```python
   params = {
       'workers': self.args.audio_workers,
       'speed': 1.0,
       'device': 'cpu'
   }
   ```

3. **Use expected_patterns for validation**
   ```python
   expected_patterns = ['scene_*.wav', '*.png']
   ```

### ❌ DON'T:

1. **Don't forget to register inputs**
   ```python
   # BAD: Forgot to register scenes_file
   input_deps = ['scenes_file']  # Will be 'unknown'!
   ```

2. **Don't use text_file for downstream stages**
   ```python
   # BAD: Audio depends on scenes, not text
   input_deps = ['text_file']

   # GOOD: Audio depends on scenes
   input_deps = ['scenes_file']
   ```

3. **Don't omit parameters**
   ```python
   # BAD: Missing 'quality' parameter
   params = {'model': 'gpt-4o'}

   # GOOD: Include everything
   params = {'model': 'gpt-4o', 'quality': args.image_quality}
   ```

## Testing

### Test Scenario 1: No Changes
```bash
python generate_video.py --test ...
python generate_video.py --test ...  # Same args

Expected:
  ✓ All stages cached
  ✓ Total time: ~5s (just assembly)
  ✓ Total cost: $0.00
```

### Test Scenario 2: Changed Narration Style
```bash
python generate_video.py --test --narration-style "deep voice"
python generate_video.py --test --narration-style "fast pacing"

Expected:
  ✗ Scenes regenerate (param changed)
  ✗ Audio regenerates (scenes changed)
  ✓ Images cached (art reference unchanged)
  ✗ Video regenerates (audio changed)
```

### Test Scenario 3: Changed Art Reference
```bash
python generate_video.py --test --art-reference style1.jpg
python generate_video.py --test --art-reference style2.jpg

Expected:
  ✓ Scenes cached (text unchanged)
  ✓ Audio cached (scenes unchanged)
  ✗ Images regenerate (art reference changed)
  ✗ Video regenerates (images changed)
```

## Debugging

### Check Fingerprints

```bash
# See all fingerprints
find output -name '.fingerprint.json' -exec cat {} \;

# See specific stage
cat output/audio/.fingerprint.json | jq .
```

### Force Regeneration

```bash
# Delete fingerprint to force regeneration
rm output/audio/.fingerprint.json

# Or delete entire cache
rm output/**/.fingerprint.json
```

### Cache Statistics

```python
from cache_manager_v2 import CacheManagerV2

cache = CacheManagerV2(Path('output'))
summary = cache.get_cache_summary()

print(f"Total cost: ${summary['total_cost']:.2f}")
for stage, info in summary['stages'].items():
    print(f"  {stage}: {info['status']} (fp: {info['fingerprint']})")
```

## Next Steps

1. ✅ Test with `example_cached_stage.py`
2. ✅ Integrate into one stage (e.g., image generation)
3. ✅ Verify cache hit/miss works correctly
4. ✅ Roll out to other stages
5. ✅ Update documentation

---

**Questions?** See `CACHING_V2_IMPROVEMENTS.md` for detailed comparison with V1.
