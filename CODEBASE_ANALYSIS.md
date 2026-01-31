# The Arabian Nights Video Generation Pipeline - Complete Codebase Analysis

**Date:** January 27, 2026  
**Project Location:** `/Users/biubiu/projects/the-arabian-nights`  
**Current Status:** Video generation pipeline with parallel processing and checkpointing

---

## EXECUTIVE SUMMARY

The codebase implements an **end-to-end video generation pipeline** that converts text into structured audiovisual content. It has:

- **4 major processing stages**: Scene generation → Audio → Video → Assembly
- **Parallel processing** for audio (4-8x speedup) and video (5-10x speedup)
- **Robust checkpoint/resume system** for handling interruptions
- **Multiple API client integrations**: OpenAI (Sora), OpenRouter (Claude), ElevenLabs
- **Audio backend abstraction** supporting both Chatterbox TTS and ElevenLabs
- **Exponential backoff retry logic** for transient failures
- **CLI-driven workflow** with extensive argument support

**Estimated full pipeline timing for 50 scenes:**
- Sequential: ~227 minutes (3.8 hours)
- With optimizations: ~50 minutes (4.5x faster)

---

## 1. EXISTING PIPELINE COMPONENTS

### 1.1 Main Orchestration Script
**File:** `scripts/generate_video_end_to_end.py` (569 lines)

**Purpose:** Entry point orchestrating all 4 stages of the pipeline

**Key Features:**
- 4-stage pipeline (Scene → Audio → Video → Assembly)
- Checkpoint management for resume capability
- Single scene rerun (`--rerun-scene`) for targeted regeneration
- Detailed final reporting and metadata tracking
- Parallel audio and video generation support

**CLI Arguments:**
```bash
python3 scripts/generate_video_end_to_end.py \
  --content <file>                  # Text source (mutually exclusive with --scenes)
  --scenes <file>                   # Pre-generated scenes JSON
  --audio-reference <file>          # Voice cloning reference
  --art-style "<description>"       # Visual style for Sora
  --narrator-style "<description>"  # Audio narration style
  --length "5m"                     # Target video length (5m, 30s, etc)
  --episode-title "<title>"         # Optional (auto-generated if not provided)
  --device [cpu|cuda]               # Device for audio (default: cpu)
  --speed <float>                   # Audio speed multiplier (default: 1.0)
  --sora-model [sora-2|sora-2-pro]  # Sora model (default: sora-2)
  --scene-model <model>             # LLM for scenes (default: claude-sonnet-4.5)
  --audio-workers <int>             # Parallel audio workers (default: 4)
  --video-concurrent <int>          # Max concurrent video API calls (default: 5)
  --max-retries <int>               # API retry limit (default: 5)
  --rerun-scene <id>                # Regenerate single scene
```

**Output Structure:**
```
output/{slug}/
├── scenes.json              # Structured scene data
├── metadata.json            # Pipeline metadata & timing
├── checkpoint.json          # Resume state
├── scene_report.txt         # Scene-by-scene breakdown
├── raw_audio/
│   ├── scene_001.wav
│   ├── scene_002.wav
│   └── ...
├── raw_videos/
│   ├── scene_001_part_1_8s.mp4
│   ├── scene_001_final.mp4
│   └── ...
├── scene_videos/
│   ├── scene_001.mp4        # Combined A/V per scene
│   ├── scene_002.mp4
│   └── ...
└── {slug}_final_video.mp4   # Final concatenated video
```

---

### 1.2 Scene Generation
**File:** `scripts/scene_generator.py` (275 lines)

**Purpose:** Convert raw text into structured video scenes using LLM

**Key Method:** `generate_scenes_from_text()`

**Input:**
- Raw text content
- Art style description (e.g., "19th century Russian realism")
- Narrator style (e.g., "deliberate, intimate, building dread")
- Target length in minutes
- Optional episode title

**Output JSON Structure:**
```json
{
  "episode": {
    "title": "Crime and Punishment - Part 1",
    "context": "19th century St. Petersburg, 1866",
    "art_style": "...",
    "narrator_style": "..."
  },
  "scenes": [
    {
      "scene_id": 1,
      "sentences": ["First sentence.", "Second sentence."],
      "pause_after": 0.8,
      "video_description": "Detailed visual description for Sora",
      "camera_style": "slow dolly forward, wide establishing shot"
    }
  ]
}
```

**Features:**
- Uses OpenRouter API (Claude Sonnet 4.5 by default)
- Character consistency guidelines (built-in for Anansi stories)
- Automatic JSON extraction from LLM response
- Validation of scene structure
- Scene duration estimation (~3-5 seconds per scene)

**Model:** `anthropic/claude-sonnet-4.5` (via OpenRouter)

---

### 1.3 Audio Generation
**File:** `scripts/audio_generator.py` (288 lines)

**Purpose:** Generate audio narration for scenes using TTS

**Two Classes:**

#### `SceneAudioGenerator` (Sequential)
```python
def generate_scene_audio(scene: Dict, output_path: Path) -> float:
    """Generate audio for single scene, return duration"""
```

#### `ParallelAudioGenerator` (ProcessPoolExecutor)
```python
def generate_all_scenes(
    scenes: List[Dict],
    audio_dir: Path,
    checkpoint_mgr=None
) -> Dict[int, float]:
    """Generate audio for all scenes in parallel, return duration map"""
```

**Key Features:**
- Uses `ChatterboxBackend` for voice cloning (Chatterbox is local TTS)
- ProcessPoolExecutor with configurable workers (default: 4, max: 8)
- Checkpoint integration for resume capability
- Dynamic duration measurement using ffprobe
- Worker function pickling for multiprocessing
- Pause support: `[pause-0.5]` tokens embedded in narration

**Parallel Configuration:**
- Default: 4 workers
- Max workers: `min(cpu_count(), 8)`
- Configurable via `--audio-workers` CLI arg

**Audio Format:** WAV @ audio backend's native sample rate

---

### 1.4 Video Generation
**File:** `scripts/video_generator.py` (400+ lines)

**Purpose:** Generate videos using Sora API with parallel + rate limiting

**Two Classes:**

#### `SceneVideoGenerator` (Sequential single-scene)
```python
def generate_scene_videos(
    scene: Dict,
    duration: float,
    episode_context: str,
    art_style: str,
    output_dir: Path
) -> List[Path]:
    """Generate video chunk(s) for scene"""
```

#### `ParallelVideoGenerator` (Async + Semaphore)
```python
async def generate_all_scenes(
    scenes: List[Dict],
    episode_context: str,
    art_style: str,
    video_dir: Path,
    assembler,
    checkpoint_mgr=None
) -> List[Path]:
    """Generate videos in parallel with rate limiting"""
```

**Key Features:**
- **Sora API integration** (sora-2, sora-2-pro models)
- **Async/await architecture** with `asyncio.Semaphore` for rate limiting
- **Nested parallelism**: Multiple scenes + chunks within scenes
- **Smart chunk sizing**: Sora supports 4s, 8s, 12s durations
- **Moderation block handling**: Automatic prompt simplification on blocks
- **Checkpoint integration** for per-scene tracking
- **aiohttp** for async video downloading
- **Trim-to-exact-duration** using FFmpeg after video generation

**Video Chunk Strategy:**
- Duration ≤ 4s → 1 × 4s video
- Duration ≤ 8s → 1 × 8s video (trim to exact)
- Duration ≤ 12s → 1 × 12s video (trim to exact)
- Duration > 12s → Multiple chunks (12s + 12s + 4s, etc)

**Rate Limiting:**
- Default max concurrent: 5
- Semaphore-based rate limiting
- Configurable via `--video-concurrent` CLI arg

**Prompt Building:**
```python
"{video_description}. Camera: {camera_style}. Style: {art_style}. Context: {episode_context}"
```

**Output Format:** MP4 (H.264 video, AAC audio), 1280x720

---

### 1.5 Video Assembly
**File:** `scripts/video_assembler.py` (153 lines)

**Purpose:** Post-processing for trimming, concatenation, and audio merging

**Key Methods:**
- `trim_video()` - Precise trimming to exact duration using libx264 re-encoding
- `_speed_adjust_video()` - Fallback speed adjustment for duration mismatches
- `concatenate_videos()` - FFmpeg concat demuxer for multiple video files
- `add_audio_to_video()` - Merge audio track with video

**Features:**
- Frame-accurate trimming with re-encoding
- Duration validation with 50ms tolerance
- FFmpeg concat demuxer (faster than re-encoding)
- Copy codec for audio merging (no re-encoding)
- Temporary file handling with cleanup

---

### 1.6 Checkpoint Manager
**File:** `scripts/checkpoint_manager.py` (330 lines)

**Purpose:** Track pipeline progress across stages for resume capability

**Checkpoint Structure:**
```json
{
  "version": "1.0",
  "slug": "crime-and-punishment-episode-1",
  "created_at": "2026-01-27T20:00:00Z",
  "last_updated": "2026-01-27T20:45:23Z",
  "stage": "video_generation",
  "completed_stages": ["scene_generation", "audio_generation"],
  "scenes_data": { /* full scenes JSON */ },
  
  "audio_generation": {
    "completed_scenes": [1, 2, 3, 5, 7],
    "failed_scenes": [4],
    "in_progress": [],
    "total": 50
  },
  
  "video_generation": {
    "completed_scenes": [1, 2],
    "failed_scenes": [3],
    "in_progress": [4],
    "retry_count": {"3": 2, "4": 1},
    "total": 50
  },
  
  "files": {
    "audio": {},
    "video": {}
  }
}
```

**Key Methods:**
- `load_or_create()` - Load existing or create new
- `mark_scene_completed()` - Track completion
- `mark_scene_failed()` - Track failures
- `get_pending_scenes()` - Get scenes needing work
- `should_retry()` - Check retry eligibility
- `initialize_stage()` - Setup stage metadata
- `mark_stage_completed()` - Complete entire stage
- `get_progress_summary()` - Human-readable status

**Features:**
- Atomic writes using temp file + rename
- Per-scene and per-stage tracking
- Retry count tracking
- Stage progression management
- Auto-save after each update

---

### 1.7 Retry Utilities
**File:** `scripts/retry_utils.py` (299 lines)

**Purpose:** Exponential backoff retry with jitter for transient failures

**Two Implementations:**

#### Decorator
```python
@exponential_backoff_retry(
    max_retries=5,
    base_delay=2.0,
    max_delay=300.0,
    retryable_exceptions=(requests.exceptions.HTTPError,)
)
def my_api_call():
    pass
```

#### Functional
```python
result = retry_with_backoff(
    func,
    *args,
    max_retries=5,
    base_delay=2.0,
    **kwargs
)
```

**Backoff Formula:**
```
delay = min(base_delay × (exponential_base ^ attempt), max_delay)
jittered = delay × (0.5 + random() × 0.5)
```

**Default Delays:**
- Attempt 1: ~2s (1-2s with jitter)
- Attempt 2: ~4s (2-4s with jitter)
- Attempt 3: ~8s (4-8s with jitter)
- Attempt 4: ~16s (8-16s with jitter)
- Attempt 5: ~32s (16-32s with jitter)

**Features:**
- Jitter to prevent thundering herd
- Configurable exception types
- Optional logging callback
- RetryConfig class for reusable configuration

---

### 1.8 Utility Modules

#### Slug Utils (`scripts/slug_utils.py`)
- `generate_slug()` - URL-safe slugs from text
- `sanitize_filename()` - Filesystem-safe filenames
- `create_output_filename()` - Slug-based output naming

#### OpenAI Client (`scripts/openai_client.py`)
- Sora video generation with polling
- DALL-E image generation (unused currently)
- Video reference image support
- Async polling for video status

#### OpenRouter Client (`scripts/openrouter_client.py`)
- Claude LLM API integration
- Token estimation
- Cost calculation utilities
- Image generation support

#### Audio Backend (`scripts/audio_backend.py`)
- Abstract base class for TTS backends
- ElevenLabsBackend implementation (API-based)
- ChatterboxBackend implementation (local)

---

## 2. CURRENT CAPABILITIES & FEATURES

### 2.1 What Works Well

| Capability | Status | Details |
|---|---|---|
| Scene Generation from Text | ✅ Fully Implemented | LLM-based with character consistency |
| Audio Generation | ✅ Fully Implemented | Parallel TTS (Chatterbox) with 4 workers |
| Video Generation | ✅ Fully Implemented | Sora API with async/parallel, rate limiting |
| Assembly | ✅ Fully Implemented | FFmpeg-based trimming and concatenation |
| Checkpointing | ✅ Fully Implemented | Per-scene and per-stage tracking |
| Resume from Checkpoint | ✅ Fully Implemented | Auto-detects incomplete work |
| Single Scene Rerun | ✅ Fully Implemented | `--rerun-scene` for targeted regeneration |
| Metadata Tracking | ✅ Fully Implemented | scenes.json, metadata.json, reports |
| Retry Logic | ✅ Fully Implemented | Exponential backoff for API failures |
| Progress Reporting | ✅ Partially Implemented | Basic reporting, no progress bars yet |

### 2.2 Audio Generation Flow

```
Scene JSON (with sentences, pause_after)
  ↓
ChatterboxBackend.generate_chunk()
  ├─ Build dialogue tuples: [('Narrator', 'text'), ...]
  ├─ Add pause tokens: [pause-0.5], etc
  ├─ Generate audio bytes
  └─ Save as WAV
  ↓
Measure duration with ffprobe
  ↓
Output: scene_NNN.wav + duration
```

**Parallel Execution:**
```
Scenes [1, 2, 3, 4, 5, 6, 7, 8, ...]
  ↓
ProcessPoolExecutor (4 workers)
  ├─ Worker 1: Scenes 1, 5, 9, ...
  ├─ Worker 2: Scenes 2, 6, 10, ...
  ├─ Worker 3: Scenes 3, 7, 11, ...
  └─ Worker 4: Scenes 4, 8, 12, ...
  ↓
Results aggregated → Duration map
```

### 2.3 Video Generation Flow

```
Scene + Actual Duration
  ↓
Determine video chunks (4s/8s/12s)
  ↓
Async parallel generation (semaphore-limited):
  ├─ Generate prompt from scene description
  ├─ Submit to Sora API (async)
  ├─ Poll for completion (async)
  ├─ Download video (async with aiohttp)
  └─ Collect results
  ↓
Concatenate chunks if needed (sync FFmpeg)
  ↓
Trim to exact duration (sync FFmpeg)
  ↓
Output: scene_NNN_final.mp4
```

**Rate Limiting:**
```
5 concurrent API calls max (semaphore)
Additional scenes queue behind limit
```

### 2.4 Parameter Passing

**Methods:**
1. **CLI Arguments** - Primary: `--content`, `--scenes`, `--audio-reference`, etc.
2. **Environment Variables** - API keys: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, etc.
3. **Configuration Files** - `podcasts_config.json` for podcast-specific settings
4. **JSON Input** - Pre-generated `scenes.json` for skipping scene generation

**Example Full Command:**
```bash
python3 scripts/generate_video_end_to_end.py \
  --content Anansi.txt \
  --audio-reference resources/voices/sample.mp3 \
  --art-style "watercolor storybook illustration, soft edges, warm earth tones" \
  --narrator-style "warm, curious, childlike wonder" \
  --length 5m \
  --episode-title "Anansi and the Pot of Wisdom" \
  --audio-workers 4 \
  --video-concurrent 5 \
  --max-retries 5
```

---

## 3. METADATA & OUTPUT STRUCTURE

### 3.1 Output Files Generated

```
output/{slug}/
├── scenes.json
│   └── Complete scene definitions with descriptions
├── metadata.json
│   ├── Parameters used
│   ├── Episode info (title, context, scenes count)
│   ├── Output info (duration, final video path)
│   └── Timing breakdown (scene_gen, audio, video, assembly, total)
├── checkpoint.json
│   └── Resume state (completed scenes, failed, retry counts)
├── scene_report.txt
│   └── Human-readable per-scene breakdown with sync checks
├── raw_audio/
│   ├── scene_001.wav
│   ├── scene_002.wav
│   └── scene_NNN.wav
├── raw_videos/
│   ├── scene_001_part_1_8s.mp4
│   ├── scene_001_final.mp4
│   ├── scene_002_part_1_12s.mp4
│   ├── scene_002_part_2_4s.mp4
│   ├── scene_002_concat.mp4
│   ├── scene_002_final.mp4
│   └── ...
├── scene_videos/
│   ├── scene_001.mp4  (audio + video combined)
│   ├── scene_002.mp4
│   └── scene_NNN.mp4
└── {slug}_final_video.mp4  (complete concatenated video)
```

### 3.2 Sample Metadata JSON
```json
{
  "slug": "anansi-and-the-pot-of-wisdom",
  "created_at": "2026-01-27T20:15:30.123456",
  "parameters": {
    "content_file": "Anansi.txt",
    "audio_reference": "resources/voices/maurice-meditate.mp3",
    "art_style": "watercolor storybook illustration",
    "narrator_style": "warm, curious, childlike wonder",
    "target_length": "5m",
    "device": "cpu",
    "speed": 1.0,
    "sora_model": "sora-2",
    "scene_model": "anthropic/claude-sonnet-4.5",
    "rerun_scene": null
  },
  "episode": {
    "title": "Anansi and the Pot of Wisdom",
    "context": "West African folk tale about a clever spider",
    "scenes_count": 12
  },
  "output": {
    "total_duration": 287.4,
    "final_video": "anansi-and-the-pot-of-wisdom_final_video.mp4"
  },
  "timing": {
    "scene_generation": 45.2,
    "audio_generation": 1245.8,
    "video_generation": 3456.7,
    "final_assembly": 28.3,
    "total": 4776.0
  }
}
```

---

## 4. EXISTING PATTERNS & CONVENTIONS

### 4.1 API Client Pattern

All API clients follow similar structure:

```python
class APIClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('API_KEY_ENV_VAR')
        self.base_url = "https://api.example.com/v1"
    
    def make_request(self, params):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(url, headers=headers, json=params)
        return response.json()
```

### 4.2 Stage Pattern

Each stage follows:
1. Print header with `"=" * 80`
2. Log inputs and configuration
3. Execute work (sequential or parallel)
4. Update checkpoint on completion
5. Print timing summary

### 4.3 Parallel Processing Pattern

**Audio (Process-based):**
```python
with ProcessPoolExecutor(max_workers=N) as executor:
    futures = {executor.submit(worker, scene, path): scene_id for ...}
    for future in as_completed(futures):
        result = future.result()
        checkpoint_mgr.mark_scene_completed('audio_generation', scene_id)
```

**Video (Async-based):**
```python
semaphore = Semaphore(max_concurrent)
tasks = [_generate_scene_async(scene) for scene in scenes]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4.4 Error Handling Pattern

```python
try:
    # Work
    result = api_call()
    checkpoint.mark_completed()
except Exception as e:
    checkpoint.mark_failed()
    raise
```

### 4.5 Path Handling

- Always use `Path` from `pathlib`
- Create parent directories: `path.mkdir(parents=True, exist_ok=True)`
- Use absolute paths in checkpoints
- Slug-based output directory naming

---

## 5. ARCHITECTURE WEAKNESSES & MISSING FEATURES

### 5.1 What Needs Refactoring

| Issue | Severity | Impact | Solution |
|---|---|---|---|
| No true async for audio | Medium | Slower than optimal | Replace ProcessPoolExecutor with async |
| Mixed sync/async video code | Medium | Hard to reason about | Fully async video pipeline |
| No comprehensive logging | Medium | Debugging difficult | Add logging module |
| Tight coupling of stages | Medium | Hard to test individually | Dependency injection |
| Inconsistent error handling | Medium | Some errors swallowed | Uniform error strategy |
| No rate limit tracking | Low | Can exceed API limits | Add rate limit manager |
| Checkpoint data duplication | Low | Large file sizes | Extract scenes to separate file |
| No config file support | Low | Long CLI args | YAML config file loading |

### 5.2 What's Missing

| Feature | Requested | Current Status | Complexity |
|---|---|---|---|
| Static background/podcast mode | Mentioned in OPTIMIZATION_IMPLEMENTATION_PLAN.md | ❌ NOT IMPLEMENTED | High |
| Video quality presets | Not mentioned | ❌ NOT IMPLEMENTED | Low |
| Batch processing multiple files | Not mentioned | ❌ NOT IMPLEMENTED | Medium |
| Cloud storage integration | Not mentioned | ❌ NOT IMPLEMENTED | Medium |
| Web API/Server | Not mentioned | ❌ NOT IMPLEMENTED | High |
| Advanced resume options | Partially | ✅ Basic checkpointing works | Low |
| Live progress dashboard | Not mentioned | ❌ NOT IMPLEMENTED | High |
| Cost tracking | Mentioned in PIPELINE_ARCHITECTURE.md | ❌ NOT IMPLEMENTED | Low |

### 5.3 Static Background/Podcast Mode

**Current state:** NOT IMPLEMENTED

**What it would do:**
- Generate static background images instead of videos
- Create a podcast-style audio file
- Generate minimal metadata

**Integration points needed:**
- Scene → static image generation (DALL-E or Flux instead of Sora)
- Video → skip, only generate audio
- Assembly → create audio-only file with metadata

---

## 6. CHECKPOINT & RESUME MECHANISMS

### 6.1 How Resume Works

**Scenario:** User runs full pipeline, it fails on scene 25 of 50

**Step 1:** Load checkpoint
```python
checkpoint_mgr = CheckpointManager(output_dir)
checkpoint = checkpoint_mgr.load_or_create(slug)
# Finds existing checkpoint.json, loads it
```

**Step 2:** Check stage status
```python
if 'audio_generation' in checkpoint['completed_stages']:
    print("✓ Skipping audio generation (already completed)")
else:
    pending = checkpoint.get_pending_scenes('audio_generation')
    print(f"Resuming audio generation: {len(pending)} scenes remaining")
```

**Step 3:** Resume from last incomplete
```python
for scene_id in pending_scenes:
    generate_audio(scene_id)
    checkpoint_mgr.mark_scene_completed(checkpoint, 'audio_generation', scene_id)
```

**Step 4:** Continue to next stage when complete

### 6.2 Checkpoint Guarantees

- **Atomic writes** using temp file + rename
- **No data loss** on crash (worst case: one partially written file)
- **Idempotent** operations (re-running same scene won't duplicate work)
- **Per-scene tracking** (can regenerate individual scenes)

---

## 7. TESTING & CONFIGURATION FILES

### 7.1 Configuration Files

**podcasts_config.json** - Podcast-specific settings
```json
{
  "podcasts": [
    {
      "id": "crime_punishment",
      "topic": "Crime and Punishment",
      "title": "Crime and Punishment - Audio Drama",
      "episodes": [...],
      "status": {...}
    }
  ]
}
```

### 7.2 Test Files

**Sample JSON Files:**
- `test_episode.json` - Sample scenes structure
- `crime-punishment-scenes.json` - Full episode
- `short_test_scenes.json` - Minimal test case

**Sample Text Files:**
- `Anansi.txt` - Anansi folk tale
- `Strega_Nona.txt` - Strega Nona story
- `short_test.txt` - Minimal text for quick testing

### 7.3 Test Scripts

**In scripts directory:**
- `test_short_pipeline.py` - End-to-end test
- `test_style_reference.py` - Style consistency test
- `test_two_phase_pipeline.py` - Multi-phase test

---

## 8. FLOW DIAGRAMS

### 8.1 Main Pipeline Flow

```
┌─────────────────────────────────────────────────────┐
│ Input: Text File + Parameters                       │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ STAGE 0: Scene Generation (LLM)                     │
│ • Parse text → structured scenes                    │
│ • Add visual descriptions & camera direction        │
│ • Output: scenes.json (N scenes)                    │
└──────────────────┬──────────────────────────────────┘
                   ↓
        [Checkpoint: scene_generation]
                   ↓
┌─────────────────────────────────────────────────────┐
│ STAGE 1: Audio Generation (Parallel TTS)            │
│ • 4 worker processes (configurable)                 │
│ • Each scene → WAV file + duration                  │
│ • Output: raw_audio/scene_*.wav                     │
└──────────────────┬──────────────────────────────────┘
                   ↓
        [Checkpoint: audio_generation per scene]
                   ↓
┌─────────────────────────────────────────────────────┐
│ STAGE 2: Video Generation (Async + Rate Limited)    │
│ • Determine chunk sizes (4s/8s/12s)                 │
│ • Generate with Sora API (5 concurrent limit)       │
│ • Trim to exact audio duration                      │
│ • Output: raw_videos/scene_*_final.mp4              │
└──────────────────┬──────────────────────────────────┘
                   ↓
        [Checkpoint: video_generation per scene]
                   ↓
┌─────────────────────────────────────────────────────┐
│ STAGE 3: Final Assembly (FFmpeg)                    │
│ • Merge audio + video per scene                     │
│ • Concatenate all scenes                            │
│ • Output: {slug}_final_video.mp4                    │
└──────────────────┬──────────────────────────────────┘
                   ↓
        [Checkpoint: assembly DONE]
                   ↓
┌─────────────────────────────────────────────────────┐
│ Output: Final Video + Metadata Files                │
└─────────────────────────────────────────────────────┘
```

### 8.2 Parallel Audio Pipeline

```
Scenes [1..N]
    ↓
ProcessPoolExecutor (4 workers)
    ├─ Worker 1 → Scene 1, 5, 9, 13, ...
    ├─ Worker 2 → Scene 2, 6, 10, 14, ...
    ├─ Worker 3 → Scene 3, 7, 11, 15, ...
    └─ Worker 4 → Scene 4, 8, 12, 16, ...
    ↓
[Each worker]
    Chatterbox TTS → WAV
    ffprobe duration
    Save to disk
    Checkpoint update
    ↓
Results aggregated
```

### 8.3 Parallel Video Pipeline

```
Scenes [1..N]
    ↓
asyncio.gather() with rate limiting (Semaphore(5))
    ├─ Scene 1: [12s chunk] → Sora → Download → Trim
    ├─ Scene 2: [8s chunk] → Sora → Download → Trim
    ├─ Scene 3: [12s chunk, 4s chunk] → Sora → Download → Concat → Trim
    ├─ Scene 4: [8s chunk] → Sora → Download → Trim
    ├─ Scene 5: [waiting for slot...]
    └─ ...
    ↓
[Per scene completion]
    Checkpoint update
    FFmpeg concat/trim
    ↓
Results aggregated
```

---

## 9. INTEGRATION POINTS

### 9.1 External APIs

| API | Purpose | Client | Rate Limit | Cost |
|---|---|---|---|---|
| OpenRouter (Claude) | Scene generation | `openrouter_client.py` | ~10 req/min | ~$0.05 per generation |
| OpenAI Sora | Video generation | `openai_client.py` | Unknown | High (depends on duration) |
| ElevenLabs TTS | Audio (alt) | `audio_backend.py` | 500k chars/month | Depends on plan |

### 9.2 Local Tools

| Tool | Purpose | Version | Required |
|---|---|---|---|
| Chatterbox | Audio TTS | Local | ✅ Yes (for audio) |
| FFmpeg | Video processing | 5.x+ | ✅ Yes (trim, concat) |
| ffprobe | Duration measurement | 5.x+ | ✅ Yes (duration) |

---

## 10. RECOMMENDED REFACTORING ROADMAP

### Phase 1: Architecture Improvements (Week 1)

1. **Create configuration system**
   - YAML config file support
   - Environment-based config selection
   - CLI args override config

2. **Improve logging**
   - Replace print() with logging module
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - File + console output

3. **Add dependency injection**
   - Pass dependencies instead of creating in functions
   - Easier testing and mocking

### Phase 2: Core Refactoring (Week 2)

1. **Unify parallel patterns**
   - Use async for both audio and video
   - Remove ProcessPoolExecutor for audio
   - Consistent error handling

2. **Decouple pipeline stages**
   - Create abstract Stage base class
   - Each stage implements same interface
   - Easier to test, extend, customize

3. **Improve type hints**
   - Full type hints throughout
   - dataclasses for config/data structures
   - mypy compliance

### Phase 3: New Features (Week 3)

1. **Static background mode**
   - Skip video generation
   - Generate static images instead
   - Create audio-only output option

2. **Batch processing**
   - Multiple input files
   - Parallel file processing
   - Aggregate results

3. **Cost tracking**
   - Track API calls per stage
   - Calculate estimated costs
   - Display cost breakdown

---

## 11. SUMMARY TABLE

| Aspect | Status | Quality | Refactor Priority |
|---|---|---|---|
| Scene generation | ✅ Working | Good | Low |
| Audio generation | ✅ Working | Good | Medium (async) |
| Video generation | ✅ Working | Fair | Medium (async) |
| Assembly | ✅ Working | Good | Low |
| Checkpointing | ✅ Working | Good | Low |
| Resume capability | ✅ Working | Good | Low |
| Error handling | ⚠️ Partial | Fair | High |
| Logging | ⚠️ Minimal | Poor | High |
| Testing | ⚠️ Basic | Fair | Medium |
| Documentation | ⚠️ Minimal | Fair | Medium |
| Config system | ❌ Missing | - | High |
| Static mode | ❌ Missing | - | High |

---

## 12. KEY METRICS & PERFORMANCE

### 12.1 Timing Breakdown (50 scenes, estimated)

| Stage | Sequential | With Optimization | Speedup |
|---|---|---|---|
| Scene Generation | 1 min | 1 min | 1x |
| Audio Generation | 75 min | 19 min | 4x |
| Video Generation | 150 min | 30 min | 5x |
| Assembly | 1 min | 1 min | 1x |
| **Total** | **227 min** | **50 min** | **4.5x** |

### 12.2 Resource Usage

- **CPU:** 4 cores (audio workers) + 1 core (main thread) + aiohttp threads
- **Memory:** ~2-4 GB (depends on video chunk sizes)
- **Disk:** ~50-100 GB for 50-scene generation (temporary)
- **Network:** Heavy during video generation (6-12 concurrent downloads)

---

## CONCLUSION

The codebase is **well-structured and functional** with:
- ✅ Working 4-stage pipeline
- ✅ Parallel processing (4-5x speedup)
- ✅ Robust checkpoint/resume
- ✅ Multiple API integrations
- ✅ Decent error handling

**Ready for refactoring** because:
- Core functionality is stable
- Architecture is clear but improvable
- Multiple optimization opportunities exist
- New features can be added cleanly

**Focus refactoring on:**
1. Configuration system (eliminate CLI arg soup)
2. Async unification (consistent patterns)
3. Logging (replace print calls)
4. Static mode (new major feature)
5. Testing improvements
