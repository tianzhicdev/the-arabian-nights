# Pipeline Optimization Implementation Plan

## Goals
1. ✅ Parallelize audio generation (4x speedup)
2. ✅ Parallelize video generation (5-10x speedup)
3. ✅ Add checkpointing system for resume capability
4. ✅ Add exponential retry for transient API failures
5. ✅ Make system interruptible and resumable

---

## Part 1: Checkpointing System

### Design

```python
# Checkpoint structure
checkpoint = {
    "version": "1.0",
    "slug": "anansi-and-the-pot-of-wisdom",
    "created_at": "2026-01-27T20:00:00Z",
    "last_updated": "2026-01-27T20:45:23Z",

    "stage": "video_generation",  # Current stage
    "completed_stages": ["scene_generation", "audio_generation"],

    "scenes_data": { ... },  # Full scenes JSON

    "audio_generation": {
        "completed_scenes": [1, 2, 3, 5, 7],
        "failed_scenes": [],
        "in_progress": [],
        "total": 45
    },

    "video_generation": {
        "completed_scenes": [1, 2],
        "failed_scenes": [4],  # Scene 4 had 500 error
        "in_progress": [3],
        "retry_count": {"4": 2},  # Scene 4 failed 2 times
        "total": 45
    },

    "files": {
        "audio": {
            "1": "output/anansi/raw_audio/scene_001.wav",
            "2": "output/anansi/raw_audio/scene_002.wav",
            ...
        },
        "video": {
            "1": "output/anansi/raw_videos/scene_001_final.mp4",
            ...
        }
    }
}
```

### Implementation

**New file: `scripts/checkpoint_manager.py`**

```python
class CheckpointManager:
    """Manage pipeline checkpoints for resume capability"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.checkpoint_path = output_dir / 'checkpoint.json'

    def load_or_create(self) -> Dict:
        """Load existing checkpoint or create new one"""
        if self.checkpoint_path.exists():
            print(f"✓ Found existing checkpoint, resuming...")
            with open(self.checkpoint_path) as f:
                return json.load(f)
        return self._create_new()

    def save(self, checkpoint: Dict):
        """Save checkpoint atomically"""
        # Write to temp file first, then atomic rename
        temp_path = self.checkpoint_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        temp_path.replace(self.checkpoint_path)

    def mark_scene_completed(self, stage: str, scene_id: int):
        """Mark a scene as completed for a stage"""

    def mark_scene_failed(self, stage: str, scene_id: int):
        """Mark a scene as failed"""

    def get_pending_scenes(self, stage: str) -> List[int]:
        """Get list of scenes that need processing"""

    def should_retry(self, stage: str, scene_id: int, max_retries=3) -> bool:
        """Check if we should retry a failed scene"""
```

### Usage in main pipeline

```python
def main():
    # Initialize checkpoint
    checkpoint_mgr = CheckpointManager(output_dir)
    checkpoint = checkpoint_mgr.load_or_create()

    # Stage 0: Scene Generation
    if checkpoint['stage'] == 'scene_generation':
        scenes_data = generate_scenes(...)
        checkpoint['scenes_data'] = scenes_data
        checkpoint['stage'] = 'audio_generation'
        checkpoint_mgr.save(checkpoint)
    else:
        print("✓ Skipping scene generation (already completed)")
        scenes_data = checkpoint['scenes_data']

    # Stage 1: Audio Generation
    if checkpoint['stage'] == 'audio_generation':
        pending = checkpoint_mgr.get_pending_scenes('audio_generation')
        print(f"Audio: {len(pending)} scenes remaining")

        for scene_id in pending:
            try:
                generate_audio(scene_id, ...)
                checkpoint_mgr.mark_scene_completed('audio_generation', scene_id)
            except Exception as e:
                checkpoint_mgr.mark_scene_failed('audio_generation', scene_id)
                raise

        checkpoint['stage'] = 'video_generation'
        checkpoint_mgr.save(checkpoint)

    # ... similar for video generation
```

---

## Part 2: Exponential Retry with Backoff

### Design

```python
class RetryConfig:
    max_retries: int = 5
    base_delay: float = 2.0  # Start with 2 seconds
    max_delay: float = 300.0  # Cap at 5 minutes
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to avoid thundering herd
```

### Implementation

**Add to `scripts/retry_utils.py`**

```python
import time
import random
from functools import wraps
from typing import Callable, Type, Tuple

def exponential_backoff_retry(
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 300.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_callback: Callable = None
):
    """
    Decorator for exponential backoff retry.

    Delay calculation: min(base_delay * (exponential_base ^ attempt), max_delay)
    With jitter: delay * (0.5 + random.random())

    Example delays with base=2, exponential_base=2:
    - Attempt 1: 2s
    - Attempt 2: 4s
    - Attempt 3: 8s
    - Attempt 4: 16s
    - Attempt 5: 32s
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        if log_callback:
                            log_callback(f"❌ Failed after {max_retries} retries: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter (randomness)
                    jittered_delay = delay * (0.5 + random.random())

                    if log_callback:
                        log_callback(
                            f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}\n"
                            f"   Retrying in {jittered_delay:.1f}s..."
                        )

                    time.sleep(jittered_delay)

            raise last_exception

        return wrapper
    return decorator
```

### Usage

```python
# In openai_client.py
from retry_utils import exponential_backoff_retry

class OpenAIClient:

    @exponential_backoff_retry(
        max_retries=5,
        base_delay=2.0,
        max_delay=300.0,
        retryable_exceptions=(
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ),
        log_callback=print
    )
    def generate_video(self, prompt: str, ...):
        """Generate video with automatic retry on transient failures"""
        # Submit video generation
        job_id = self._submit_video_job(...)

        # Poll for completion (with retry on 500 errors)
        video_url = self._poll_video_status(job_id)

        return video_url

    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def _poll_video_status(self, job_id: str) -> str:
        """Poll video status, retry on 500 errors"""
        while True:
            response = requests.get(f"{self.base_url}/videos/{job_id}", ...)
            response.raise_for_status()  # Will retry on 500

            data = response.json()
            status = data.get('status')

            if status == 'completed':
                return data['url']
            elif status == 'failed':
                raise Exception(f"Video generation failed: {data.get('error')}")

            time.sleep(5)  # Poll every 5 seconds
```

---

## Part 3: Parallel Audio Generation

### Implementation

**Update `scripts/audio_generator.py`**

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

class ParallelAudioGenerator:
    """Parallel audio generation using process pool"""

    def __init__(self, audio_prompt_path: str, device: str = 'cpu',
                 speed: float = 1.0, max_workers: int = None):
        self.audio_prompt_path = audio_prompt_path
        self.device = device
        self.speed = speed
        self.max_workers = max_workers or min(cpu_count(), 8)

    def generate_all_scenes(
        self,
        scenes: List[Dict],
        audio_dir: Path,
        checkpoint_mgr: CheckpointManager
    ) -> Dict[int, float]:
        """
        Generate audio for all scenes in parallel.

        Returns:
            Dict mapping scene_id -> duration
        """
        pending_scenes = checkpoint_mgr.get_pending_scenes('audio_generation')

        if not pending_scenes:
            print("✓ All audio already generated")
            return self._load_existing_durations(scenes, audio_dir)

        print(f"\nGenerating audio for {len(pending_scenes)} scenes...")
        print(f"  Workers: {self.max_workers}")

        durations = {}

        # Create work items
        work_items = [
            (scene, audio_dir / f"scene_{scene['scene_id']:03d}.wav")
            for scene in scenes
            if scene['scene_id'] in pending_scenes
        ]

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(
                    self._generate_single_scene_worker,
                    scene,
                    output_path,
                    self.audio_prompt_path,
                    self.device,
                    self.speed
                ): scene['scene_id']
                for scene, output_path in work_items
            }

            # Progress bar
            from tqdm import tqdm
            with tqdm(total=len(futures), desc="Audio Generation") as pbar:
                for future in as_completed(futures):
                    scene_id = futures[future]

                    try:
                        duration = future.result()
                        durations[scene_id] = duration
                        checkpoint_mgr.mark_scene_completed('audio_generation', scene_id)
                        pbar.update(1)

                    except Exception as e:
                        print(f"\n❌ Scene {scene_id} failed: {e}")
                        checkpoint_mgr.mark_scene_failed('audio_generation', scene_id)
                        pbar.update(1)
                        raise

        return durations

    @staticmethod
    def _generate_single_scene_worker(
        scene: Dict,
        output_path: Path,
        audio_prompt_path: str,
        device: str,
        speed: float
    ) -> float:
        """Worker function for parallel execution"""
        # Import inside worker to avoid pickling issues
        from audio_backend import ChatterboxBackend
        import subprocess
        import json

        backend = ChatterboxBackend(
            audio_prompt_path=audio_prompt_path,
            device=device,
            exaggeration=0.7,
            speed=speed
        )

        # Generate audio
        dialogues = []
        for sentence in scene['sentences']:
            dialogues.append(('Narrator', sentence))

        if scene.get('pause_after', 0) > 0:
            dialogues.append(('Narrator', f"[pause-{scene['pause_after']}]"))

        audio_bytes = backend.generate_chunk(dialogues, 1, 1)

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        # Measure duration
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', str(output_path)],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])

        return duration
```

---

## Part 4: Parallel Video Generation with Rate Limiting

### Implementation

**Update `scripts/video_generator.py`**

```python
import asyncio
import aiohttp
from asyncio import Semaphore
from typing import List, Dict

class ParallelVideoGenerator:
    """Async video generation with rate limiting"""

    def __init__(self, openai_client: OpenAIClient, model: str = 'sora-2',
                 max_concurrent: int = 5):
        self.client = openai_client
        self.model = model
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)

    async def generate_all_scenes(
        self,
        scenes: List[Dict],
        episode_context: str,
        art_style: str,
        video_dir: Path,
        checkpoint_mgr: CheckpointManager
    ):
        """Generate videos for all scenes in parallel with rate limiting"""

        pending_scenes = checkpoint_mgr.get_pending_scenes('video_generation')

        if not pending_scenes:
            print("✓ All videos already generated")
            return

        print(f"\nGenerating videos for {len(pending_scenes)} scenes...")
        print(f"  Max concurrent: {self.max_concurrent}")

        # Filter to pending scenes
        work_scenes = [s for s in scenes if s['scene_id'] in pending_scenes]

        # Create tasks
        tasks = [
            self._generate_single_scene_async(
                scene, episode_context, art_style, video_dir, checkpoint_mgr
            )
            for scene in work_scenes
        ]

        # Run with progress bar
        from tqdm.asyncio import tqdm_asyncio
        results = await tqdm_asyncio.gather(*tasks, desc="Video Generation")

        return results

    async def _generate_single_scene_async(
        self,
        scene: Dict,
        episode_context: str,
        art_style: str,
        video_dir: Path,
        checkpoint_mgr: CheckpointManager
    ):
        """Generate video for a single scene with rate limiting"""

        async with self.semaphore:  # Rate limiting
            scene_id = scene['scene_id']
            duration = scene['actual_duration']

            try:
                # Determine chunks
                chunks = self.determine_video_chunks(duration)

                print(f"\nScene {scene_id} ({duration:.2f}s):")
                print(f"  Strategy: {' + '.join(f'{c}s' for c in chunks)}")

                # Generate chunks in parallel (within scene)
                chunk_tasks = [
                    self._generate_chunk_async(
                        scene, chunk_duration, i, len(chunks),
                        episode_context, art_style, video_dir
                    )
                    for i, chunk_duration in enumerate(chunks, 1)
                ]

                raw_videos = await asyncio.gather(*chunk_tasks)

                # Concatenate if needed
                if len(raw_videos) > 1:
                    # Use sync FFmpeg
                    concat_path = video_dir / f"scene_{scene_id:03d}_concat.mp4"
                    self._concatenate_sync(raw_videos, concat_path)
                    video_to_trim = concat_path
                else:
                    video_to_trim = raw_videos[0]

                # Trim
                trimmed_path = video_dir / f"scene_{scene_id:03d}_final.mp4"
                self._trim_sync(video_to_trim, duration, trimmed_path)

                checkpoint_mgr.mark_scene_completed('video_generation', scene_id)
                print(f"  ✓ Scene {scene_id} completed")

                return trimmed_path

            except Exception as e:
                print(f"\n❌ Scene {scene_id} failed: {e}")
                checkpoint_mgr.mark_scene_failed('video_generation', scene_id)
                raise

    async def _generate_chunk_async(
        self, scene: Dict, chunk_duration: int, chunk_num: int, total_chunks: int,
        episode_context: str, art_style: str, video_dir: Path
    ) -> Path:
        """Generate a single video chunk asynchronously"""

        print(f"  [{chunk_num}/{total_chunks}] Generating {chunk_duration}s...")

        # Build prompt
        prompt = self._build_video_prompt(scene, episode_context, art_style)

        # Use retry decorator from client
        video_url = await asyncio.to_thread(
            self.client.generate_video,
            prompt=prompt,
            model=self.model,
            seconds=chunk_duration,
            size="1280x720"
        )

        # Download
        video_path = video_dir / f"scene_{scene['scene_id']:03d}_part_{chunk_num}_{chunk_duration}s.mp4"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                video_url,
                headers={"Authorization": f"Bearer {self.client.api_key}"}
            ) as response:
                response.raise_for_status()
                with open(video_path, 'wb') as f:
                    f.write(await response.read())

        print(f"  ✓ [{chunk_num}/{total_chunks}] Saved {video_path.name}")
        return video_path
```

---

## Part 5: Updated Main Pipeline

**Update `scripts/generate_video_end_to_end.py`**

```python
import asyncio
from checkpoint_manager import CheckpointManager
from audio_generator import ParallelAudioGenerator
from video_generator import ParallelVideoGenerator

def main():
    # ... arg parsing ...

    # Initialize checkpoint
    checkpoint_mgr = CheckpointManager(output_dir)
    checkpoint = checkpoint_mgr.load_or_create()

    # Stage 0: Scene Generation
    if 'scene_generation' not in checkpoint['completed_stages']:
        print("\n" + "=" * 80)
        print("STAGE 0: Scene Generation")
        print("=" * 80)

        scene_gen = SceneGenerator(model=args.scene_model)
        scenes_data = scene_gen.generate_scenes_from_text(...)

        checkpoint['scenes_data'] = scenes_data
        checkpoint['completed_stages'].append('scene_generation')
        checkpoint_mgr.save(checkpoint)
    else:
        print("✓ Skipping Stage 0 (already completed)")
        scenes_data = checkpoint['scenes_data']

    # Stage 1: Audio Generation (Parallel)
    if 'audio_generation' not in checkpoint['completed_stages']:
        print("\n" + "=" * 80)
        print("STAGE 1: Audio Generation (Parallel)")
        print("=" * 80)

        audio_gen = ParallelAudioGenerator(
            args.audio_reference,
            device=args.device,
            speed=args.speed,
            max_workers=4  # Configurable
        )

        durations = audio_gen.generate_all_scenes(
            scenes_data['scenes'],
            audio_dir,
            checkpoint_mgr
        )

        # Update scenes with durations
        for scene in scenes_data['scenes']:
            scene['actual_duration'] = durations[scene['scene_id']]

        checkpoint['completed_stages'].append('audio_generation')
        checkpoint_mgr.save(checkpoint)

    # Stage 2: Video Generation (Parallel + Async)
    if 'video_generation' not in checkpoint['completed_stages']:
        print("\n" + "=" * 80)
        print("STAGE 2: Video Generation (Parallel)")
        print("=" * 80)

        video_gen = ParallelVideoGenerator(
            openai_client,
            model=args.sora_model,
            max_concurrent=5  # Configurable
        )

        # Run async generation
        asyncio.run(
            video_gen.generate_all_scenes(
                scenes_data['scenes'],
                episode['context'],
                episode['art_style'],
                video_dir,
                checkpoint_mgr
            )
        )

        checkpoint['completed_stages'].append('video_generation')
        checkpoint_mgr.save(checkpoint)

    # Stage 3: Assembly (unchanged)
    # ...
```

---

## Testing Plan

### Test 1: Checkpoint Resume
1. Start generation with 10 scenes
2. Kill process after 5 scenes audio completed
3. Restart - should resume from scene 6
4. Verify no duplicate work

### Test 2: Retry on Failure
1. Mock API to return 500 error
2. Verify exponential backoff (2s, 4s, 8s, 16s, 32s)
3. Verify success after 3 retries
4. Verify failure after 5 retries

### Test 3: Parallel Performance
1. Generate 20 scenes
2. Sequential: measure time
3. Parallel (4 workers): measure time
4. Verify ~4x speedup
5. Verify all outputs correct

### Test 4: Rate Limiting
1. Set max_concurrent=3
2. Monitor active connections
3. Verify never exceeds 3
4. Verify all videos generated

---

## Implementation Order

1. **Day 1: Checkpoint System**
   - Create `checkpoint_manager.py`
   - Integrate into main pipeline
   - Test resume capability

2. **Day 2: Retry Logic**
   - Create `retry_utils.py`
   - Add to OpenAI client
   - Test with mock failures

3. **Day 3: Parallel Audio**
   - Update `audio_generator.py`
   - Add ProcessPoolExecutor
   - Test with 20 scenes

4. **Day 4: Parallel Video**
   - Update `video_generator.py`
   - Add asyncio + rate limiting
   - Test with 10 scenes

5. **Day 5: Integration & Testing**
   - Update main pipeline
   - End-to-end testing
   - Performance benchmarking

---

## Configuration Options

Add to CLI:

```bash
python3 scripts/generate_video_end_to_end.py \
  --content source.txt \
  --audio-reference voice.mp3 \
  --art-style "..." \
  --narrator-style "..." \
  --length 5m \
  --audio-workers 4 \           # NEW
  --video-concurrent 5 \         # NEW
  --max-retries 5 \              # NEW
  --resume                       # NEW (auto-detect checkpoint)
```

---

## Success Criteria

- ✅ Pipeline survives Ctrl+C and resumes
- ✅ API 500 errors are retried automatically
- ✅ 50-scene generation: 227min → 50min
- ✅ No duplicate work on resume
- ✅ All files tracked in checkpoint
- ✅ Progress bars show accurate ETAs
