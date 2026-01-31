# Video Generation Pipeline Architecture

## Current Architecture (Sequential)

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: Text File (Anansi.txt, Crime & Punishment, etc.)        │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 0: Scene Generation (LLM)                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Claude Sonnet 4.5 via OpenRouter                           │ │
│ │ • Convert text → structured JSON                           │ │
│ │ • Generate episode title, context                          │ │
│ │ • Create video descriptions per scene                      │ │
│ │ • Estimate ~3-5s per scene for target length              │ │
│ │ TIME: 30-60 seconds (single API call)                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
                    scenes.json (N scenes)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Audio Generation (Chatterbox TTS)      ⚠️ BOTTLENECK   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ FOR EACH SCENE (SEQUENTIAL):                                │ │
│ │   Scene 1 → Chatterbox → scene_001.wav → measure duration  │ │
│ │   Scene 2 → Chatterbox → scene_002.wav → measure duration  │ │
│ │   Scene 3 → Chatterbox → scene_003.wav → measure duration  │ │
│ │   ...                                                        │ │
│ │   Scene N → Chatterbox → scene_NNN.wav → measure duration  │ │
│ │                                                              │ │
│ │ TIME PER SCENE: ~60-120 seconds (CPU-intensive)             │ │
│ │ TOTAL TIME: N × 90s  (e.g., 50 scenes = 75 minutes!)       │ │
│ │                                                              │ │
│ │ ⚠️ PARALLELIZATION OPPORTUNITY: Can run 4-8 in parallel     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Combine all: scene_001.wav + scene_002.wav + ... → combined.wav│
└────────────────────────────┬────────────────────────────────────┘
                             ↓
         Audio files + Scenes with actual_duration
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Video Generation (Sora API)            🔥 BOTTLENECK   │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ FOR EACH SCENE (SEQUENTIAL):                                │ │
│ │                                                              │ │
│ │   Scene 1 (8.2s):                                           │ │
│ │     → Sora API (8s video)      [~120s]                      │ │
│ │     → Download                 [~10s]                       │ │
│ │     → Trim to 8.2s            [~2s]                         │ │
│ │                                                              │ │
│ │   Scene 2 (15.1s):                                          │ │
│ │     → Sora API (12s chunk 1)   [~120s]                      │ │
│ │     → Sora API (4s chunk 2)    [~120s]  ⚠️ SEQUENTIAL!      │ │
│ │     → Download both            [~20s]                       │ │
│ │     → Concatenate              [~3s]                        │ │
│ │     → Trim to 15.1s           [~2s]                         │ │
│ │                                                              │ │
│ │   ... (repeat for all scenes)                               │ │
│ │                                                              │ │
│ │ TIME PER SCENE: 120-300 seconds (API wait + processing)     │ │
│ │ TOTAL TIME: N × 180s  (e.g., 50 scenes = 150 minutes!)     │ │
│ │                                                              │ │
│ │ 🔥 PARALLELIZATION OPPORTUNITY:                              │ │
│ │   - Generate videos for multiple scenes in parallel         │ │
│ │   - Within scene: generate chunks in parallel               │ │
│ │   - Respect Sora API rate limits (probably 5-10/min)        │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
              Trimmed video files per scene
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Final Assembly (FFmpeg)                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. Concatenate all videos → video_only.mp4   [~10s]        │ │
│ │ 2. Merge with audio → final_video.mp4        [~5s]         │ │
│ │ TIME: 15-30 seconds                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: final_video.mp4 + metadata.json                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parallel Architecture (Optimized)

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: Text File                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 0: Scene Generation (LLM)                                 │
│ TIME: 30-60s (unchanged)                                        │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
                    scenes.json (N scenes)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Audio Generation (Parallel)          ⚡ PARALLELIZED   │
│ ┌──────────────┬──────────────┬──────────────┬────────────────┐ │
│ │ Worker 1     │ Worker 2     │ Worker 3     │ Worker 4       │ │
│ │ Scene 1→wav  │ Scene 2→wav  │ Scene 3→wav  │ Scene 4→wav    │ │
│ │ Scene 5→wav  │ Scene 6→wav  │ Scene 7→wav  │ Scene 8→wav    │ │
│ │ ...          │ ...          │ ...          │ ...            │ │
│ └──────────────┴──────────────┴──────────────┴────────────────┘ │
│                                                                  │
│ TIME: N ÷ num_workers × 90s                                     │
│ SPEEDUP: 4x with 4 workers (75min → 19min for 50 scenes)       │
│                                                                  │
│ Combine: scene_*.wav → combined.wav (parallel write possible)   │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Video Generation (Parallel + Rate Limited)  ⚡🔥        │
│ ┌──────────────┬──────────────┬──────────────┬────────────────┐ │
│ │ API Worker 1 │ API Worker 2 │ API Worker 3 │ API Worker 4   │ │
│ │ Scene 1      │ Scene 2      │ Scene 3      │ Scene 4        │ │
│ │   Chunk 1→   │   Chunk 1→   │   Chunk 1→   │   Chunk 1→     │ │
│ │   Chunk 2→   │   (single)   │   Chunk 2→   │   (single)     │ │
│ │ Scene 5      │ Scene 6      │ Scene 7      │ Scene 8        │ │
│ │ ...          │ ...          │ ...          │ ...            │ │
│ └──────────────┴──────────────┴──────────────┴────────────────┘ │
│         ↑                                                        │
│         └── Rate Limiter: max 5-10 concurrent API calls         │
│                                                                  │
│ NESTED PARALLELISM: Chunks within scene also parallel           │
│                                                                  │
│ TIME: N ÷ concurrent_limit × 150s                               │
│ SPEEDUP: 5x with limit=5 (150min → 30min for 50 scenes)        │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Final Assembly (unchanged)                             │
│ TIME: 15-30s                                                    │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
                   final_video.mp4
```

---

## Bottleneck Analysis

### Current Performance (50 scenes):

| Stage              | Time      | Bottleneck Type | Parallelizable? |
|--------------------|-----------|-----------------|-----------------|
| Scene Generation   | 1 min     | API (single)    | ❌ No           |
| Audio Generation   | 75 min    | CPU             | ✅ YES (4-8x)   |
| Video Generation   | 150 min   | API (rate)      | ✅ YES (5-10x)  |
| Final Assembly     | 0.5 min   | FFmpeg          | ❌ No (fast)    |
| **TOTAL**          | **227 min** | **(~3.8 hrs)** |                 |

### Optimized Performance (50 scenes):

| Stage              | Time      | Speedup        |
|--------------------|-----------|----------------|
| Scene Generation   | 1 min     | 1x (unchanged) |
| Audio Generation   | 19 min    | 4x (parallel)  |
| Video Generation   | 30 min    | 5x (parallel)  |
| Final Assembly     | 0.5 min   | 1x (unchanged) |
| **TOTAL**          | **50 min** | **4.5x faster**|

---

## Optimization Recommendations

### 1. **Audio Parallelization** (HIGH IMPACT)

**Current:**
```python
for scene in scenes:
    audio_gen.generate_scene_audio(scene, audio_path)  # Sequential
```

**Optimized:**
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(generate_audio_worker, scene, audio_path)
        for scene in scenes
    ]
    for future in as_completed(futures):
        duration = future.result()
```

**Complexity:** Medium
**Speedup:** 4x (CPU cores)
**Risk:** Low (Chatterbox is thread-safe)

---

### 2. **Video Parallelization** (CRITICAL IMPACT)

**Current:**
```python
for scene in scenes:
    raw_videos = video_gen.generate_scene_videos(scene, ...)  # Sequential
```

**Optimized:**
```python
import asyncio
from aiohttp import ClientSession

async def generate_all_videos(scenes):
    semaphore = asyncio.Semaphore(5)  # Rate limit: 5 concurrent

    async with ClientSession() as session:
        tasks = [
            generate_video_async(session, semaphore, scene)
            for scene in scenes
        ]
        return await asyncio.gather(*tasks)
```

**Complexity:** High (async refactor)
**Speedup:** 5-10x (API rate limit)
**Risk:** Medium (API rate limits, need error handling)

---

### 3. **Within-Scene Chunk Parallelization** (MODERATE IMPACT)

For scenes requiring multiple video chunks (e.g., 15s scene = 12s + 4s):

**Current:**
```python
for chunk_duration in [12, 4]:
    video_url = sora_api.generate(prompt, seconds=chunk_duration)  # Sequential
```

**Optimized:**
```python
async with asyncio.TaskGroup() as tg:
    tasks = [
        tg.create_task(sora_api.generate_async(prompt, seconds=d))
        for d in [12, 4]
    ]
video_urls = [task.result() for task in tasks]
```

**Complexity:** Medium
**Speedup:** 2x for multi-chunk scenes
**Risk:** Low (same scene, different durations)

---

### 4. **Simplifications**

#### a) **Skip Unnecessary File Writes**
- Current: Write every intermediate video chunk
- Optimized: Keep in memory, only write finals
- **Savings:** Disk I/O, ~5-10% time

#### b) **Optimize Audio Combining**
```python
# Current: Load all files, concatenate, write
combined = AudioSegment.empty()
for audio_path in scene_audio_paths:
    combined += AudioSegment.from_wav(str(audio_path))

# Optimized: Use FFmpeg concat directly (much faster)
ffmpeg_concat_audio(scene_audio_paths, output_path)
```
**Savings:** ~50% on audio assembly

#### c) **Smart Caching**
- Cache LLM scene generation results
- Resume from checkpoint if pipeline fails
- Skip regeneration if files exist

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Audio parallelization (ProcessPoolExecutor)
2. ✅ FFmpeg audio concat optimization
3. ✅ Add progress bars (tqdm)

### Phase 2: Major Speedup (4-6 hours)
1. ✅ Video generation parallelization (asyncio + aiohttp)
2. ✅ Rate limiting with semaphores
3. ✅ Chunk-level parallelization

### Phase 3: Polish (2-3 hours)
1. ✅ Checkpoint/resume system
2. ✅ Better error handling
3. ✅ Memory optimization

---

## Data Flow Diagram

```
Text
 ↓
Scene Gen (LLM) ────────→ scenes.json
 ↓
┌────────────────────────────────────┐
│  Audio Workers (Parallel)          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │ W1  │ │ W2  │ │ W3  │ │ W4  │  │
│  └─────┘ └─────┘ └─────┘ └─────┘  │
│    ↓       ↓       ↓       ↓       │
│  .wav    .wav    .wav    .wav      │
└────────────────────────────────────┘
 ↓
Combined Audio
 ↓
┌────────────────────────────────────┐
│  Video Workers (Parallel + Rate)   │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │ V1  │ │ V2  │ │ V3  │ │ V4  │  │
│  └─────┘ └─────┘ └─────┘ └─────┘  │
│    ↓       ↓       ↓       ↓       │
│  .mp4    .mp4    .mp4    .mp4      │
│         (rate limited)             │
└────────────────────────────────────┘
 ↓
Concat Videos
 ↓
Merge Audio
 ↓
Final Video
```

---

## Monitoring & Observability

Add to pipeline:
- Progress bars per stage (tqdm)
- ETA calculations
- Cost tracking (API calls × price)
- Resource usage (CPU, memory, disk)
- Checkpoint files for resume

Example output:
```
STAGE 1: Audio Generation
[████████████████████████] 50/50 scenes (19:23 elapsed, 0:00 remaining)

STAGE 2: Video Generation
[████████░░░░░░░░░░░░░░░░] 20/50 scenes (12:45 elapsed, 19:05 remaining)
  Scene 21: Generating chunk 1/2 (8s)...
  Scene 22: Generating chunk 1/1 (12s)...
  Scene 23: Downloading...
  Active API calls: 5/5 (rate limited)
  Cost so far: $12.50
```
