# Resumable Batch Processing Guide

## Your Question

> "So if I start running for a bunch of txt input, and then I go to subway with no internet for a few hours; then I go back home the process can resume?"

## Answer: YES! ✅

Your batch processing is **fully resumable** after any interruption.

## How It Works

### Three Levels of Resumability

#### 1. **Stage-Level Caching** (V2 Fingerprints)

Each stage within a story saves `.fingerprint.json` when complete:

```
output/gutenberg/01_call_of_cthulhu/
├── .fingerprint.json              ← Scenes complete
├── scenes.json
├── audio/
│   ├── .fingerprint.json          ← Audio complete
│   ├── scene_001.wav
│   └── scene_002.wav
├── images/
│   ├── .fingerprint.json          ← Images complete
│   ├── scene_001.png
│   └── scene_002.png
└── video/
    └── scene_001_slides.mp4
```

If interrupted during image generation:
- ✅ Scenes cached (fingerprint exists)
- ✅ Audio cached (fingerprint exists)
- ❌ Images incomplete (no fingerprint)
- Resume → Regenerate only images

#### 2. **Story-Level Completion** (Fast Check)

Batch manager checks for final video file:

```python
# Quick check: Is story done?
if final_video_exists(output_dir):
    skip_story()  # Done!
```

If Story 3 finished completely, it's skipped instantly (< 1 second).

#### 3. **Batch-Level Progress** (Resume Tracking)

Saves `batch_progress_gutenberg_stories.json`:

```json
{
  "started_at": "2026-01-28T15:00:00",
  "jobs": {
    "01_call_of_cthulhu": {
      "status": "completed",
      "completed_at": "2026-01-28T15:03:45"
    },
    "02_tell_tale_heart": {
      "status": "completed",
      "completed_at": "2026-01-28T15:07:20"
    },
    "03_cask_amontillado": {
      "status": "running",
      "started_at": "2026-01-28T15:07:25"
    }
  },
  "stats": {
    "total": 20,
    "completed": 2,
    "failed": 0,
    "skipped": 0
  }
}
```

On resume, skips stories 1-2 instantly, continues from story 3.

## Real-World Example: Your Subway Scenario

### Initial Run - Before Subway

```bash
$ ./run_batch_resumable.sh run_gutenberg_videos.sh

[1/20] 01_call_of_cthulhu
  Generating scenes...
  Generating audio...
  Generating images...
  Generating videos...
  ✓ Completed

[2/20] 02_tell_tale_heart
  Generating scenes...
  Generating audio...
  Generating images...
  Generating videos...
  ✓ Completed

[3/20] 03_cask_amontillado
  Generating scenes...
  Generating audio...
  Generating images... (50% done)

  [You lose internet / battery dies / CTRL+C]
```

**Progress saved:**
- Story 1: ✓ Complete (all stages)
- Story 2: ✓ Complete (all stages)
- Story 3: Partial
  - ✓ Scenes complete (.fingerprint.json saved)
  - ✓ Audio complete (.fingerprint.json saved)
  - ❌ Images incomplete (no .fingerprint.json)
  - ❌ Video not started
- Stories 4-20: Not started

### Resume - After Subway

```bash
$ ./run_batch_resumable.sh run_gutenberg_videos.sh

📥 RESUMING BATCH (found 2 completed jobs)
   Progress file: batch_progress_gutenberg_stories.json

[1/20] 01_call_of_cthulhu
  ✓ Already completed (from previous run)

[2/20] 02_tell_tale_heart
  ✓ Already completed (from previous run)

[3/20] 03_cask_amontillado
  Stage 1: Scene Generation
    ✓ Using cached (fingerprint match)
  Stage 2: Audio Generation
    ✓ Using cached (fingerprint match)
  Stage 3: Image Generation
    ⟳ Generating... (no cache, regenerating)
  Stage 4: Video Generation
    ⟳ Generating...
  Stage 5: Assembly
    ⟳ Running...
  ✓ Completed

[4/20] 04_gift_magi
  ⟳ Generating...
  ✓ Completed

[5/20] 05_yellow_wallpaper
  ⟳ Generating...

  ... continues through all 20 stories
```

**Result:**
- Stories 1-2: Skipped instantly (< 1 second each)
- Story 3: Only regenerated incomplete stages
- Stories 4-20: Processed normally

## Handling Different Interruption Types

### 1. **Network Loss** (Your Subway Case)

```bash
[3/20] 03_cask_amontillado
  Generating images...
  ⚠️ API Error: Connection timeout
  ⚠️ Retryable error detected. Waiting 2s before retry...
  ⚠️ API Error: Connection timeout
  ⚠️ Retryable error detected. Waiting 4s before retry...
  ⚠️ API Error: Connection timeout
  ✗ Failed: 03_cask_amontillado (max retries exhausted)

[4/20] 04_gift_magi
  Continues with next story...
```

**Later at home:**

```bash
$ ./run_batch_resumable.sh run_gutenberg_videos.sh

[3/20] 03_cask_amontillado
  Status: failed
  ⟳ Retrying...
  ✓ Completed (network restored)
```

Failed stories are automatically retried on resume.

### 2. **CTRL+C (Graceful Shutdown)**

```bash
[5/20] 05_yellow_wallpaper
  Generating audio...

  ^C  [You press CTRL+C]

⚠️  Interrupt received! Finishing current job and stopping...
    (Press CTRL+C again to force quit)

  ✓ Completed (job finished gracefully)

⚠️  Stopping after job 5/20
   Resume by running this script again

BATCH PROGRESS
═══════════════════════════════════════════════════════════════
Total Jobs: 20
Completed:  5/20 (25.0%)
Skipped:    0/20 (cached)
Failed:     0/20
═══════════════════════════════════════════════════════════════

Progress saved to: batch_progress_gutenberg_stories.json
To resume if interrupted, just run this script again!
```

### 3. **Power Loss / Kill -9 (Hard Interrupt)**

```bash
[7/20] 07_owl_creek_bridge
  Generating images...

  [Computer crashes / Battery dies]
```

**On restart:**

Story 7 will have partial completion:
- ✅ Stages with `.fingerprint.json` → Skip
- ❌ Interrupted stage (no `.fingerprint.json`) → Regenerate

No corruption, just regenerates incomplete stage.

### 4. **API Rate Limits**

```bash
[10/20] 10_dunwich_horror
  Generating images...
  ⚠️ API Error: 429 Rate limit exceeded
  ⚠️ Retryable error detected. Waiting 2s before retry...

  ⚠️ API Error: 429 Rate limit exceeded
  ⚠️ Retryable error detected. Waiting 4s before retry...

  ⚠️ API Error: 429 Rate limit exceeded
  ⚠️ Retryable error detected. Waiting 8s before retry...

  ✓ Success! (rate limit cleared)
```

**Automatic retry with exponential backoff:**
- Attempt 1: Immediate
- Attempt 2: Wait 2s
- Attempt 3: Wait 4s
- Attempt 4: Wait 8s

## Usage

### Start Batch Processing

```bash
./run_batch_resumable.sh run_gutenberg_videos.sh
```

### Resume After Interruption

```bash
# Same command! It automatically resumes
./run_batch_resumable.sh run_gutenberg_videos.sh
```

### Start Fresh (Clear Progress)

```bash
# Remove progress file
rm batch_progress_gutenberg_stories.json

# Run from beginning
./run_batch_resumable.sh run_gutenberg_videos.sh
```

### Check Progress

```bash
# View progress file
cat batch_progress_gutenberg_stories.json | jq .

# Quick summary
cat batch_progress_gutenberg_stories.json | jq '.stats'
```

## Features

### ✅ Automatic Resume

- No manual tracking needed
- Just run the same command again
- Skips completed stories instantly
- Continues from where it left off

### ✅ Error Handling

- **Retryable errors** (429, timeout, connection): Retry 3x with backoff
- **Non-retryable errors** (400, auth): Fail immediately, log error
- **Partial completion**: Regenerate only incomplete stages

### ✅ Graceful Shutdown

- Press CTRL+C: Finishes current job, then stops
- Saves progress before exit
- No corruption or partial states

### ✅ Progress Tracking

```
[7/20] 07_owl_creek_bridge
   Progress: 7/20 jobs
   Processed: 5, Skipped: 2
   Est. remaining: 32.5 minutes
```

Real-time estimates based on actual completion times.

### ✅ Cost Tracking

```json
{
  "jobs": {
    "01_call_of_cthulhu": {
      "cost": 0.42,
      "completed_at": "..."
    }
  }
}
```

Track costs per story for budgeting.

## File Structure

### Before Running

```
project/
├── run_gutenberg_videos.sh          ← Your batch script
├── run_batch_resumable.sh           ← Wrapper (run this!)
└── scripts/
    └── batch_manager.py              ← Batch logic
```

### During/After Running

```
project/
├── batch_progress_gutenberg_stories.json  ← Progress state
├── output/
│   └── gutenberg/
│       ├── 01_call_of_cthulhu/           ← Story 1 outputs
│       │   ├── .fingerprint.json          ← Stage fingerprints
│       │   ├── audio/.fingerprint.json
│       │   ├── images/.fingerprint.json
│       │   └── *_slides.mp4               ← Final video
│       ├── 02_tell_tale_heart/           ← Story 2 outputs
│       └── ...
```

## Advanced Usage

### Parallel Processing (Experimental)

```bash
# Process stories 1-10 on machine A
./run_batch_resumable.sh run_gutenberg_videos.sh --jobs 1-10

# Process stories 11-20 on machine B
./run_batch_resumable.sh run_gutenberg_videos.sh --jobs 11-20
```

Currently not implemented, but possible to add.

### Custom Retry Logic

Edit `batch_manager.py`:

```python
# Increase max retries
success = self.run_job_with_retry(job, max_retries=5)  # Default: 3

# Add more retryable error codes
retryable_errors = [
    '429',
    '503',
    '500',
    'your_custom_error'  # Add here
]
```

### Progress Webhooks (Future)

Could add webhook notifications:

```python
def on_job_complete(self, job_id):
    # Send notification
    requests.post('https://your-webhook.com', json={
        'event': 'job_complete',
        'job_id': job_id,
        'progress': self.progress.state['stats']
    })
```

## Comparison: Old vs New

### Old Approach (Basic Script)

```bash
#!/bin/bash

python generate_video.py --text 01.txt ...
python generate_video.py --text 02.txt ...
python generate_video.py --text 03.txt ...
# ...
```

**Problems:**
- ❌ No resume capability (starts from beginning)
- ❌ No error handling (crashes on API error)
- ❌ No progress tracking
- ❌ CTRL+C might corrupt current job
- ❌ Re-checks completed stories (slow)

### New Approach (Batch Manager)

```bash
./run_batch_resumable.sh run_gutenberg_videos.sh
```

**Benefits:**
- ✅ Full resume capability
- ✅ Automatic retry on errors
- ✅ Progress tracking with estimates
- ✅ Graceful shutdown
- ✅ Instant skip of completed stories

## Time Savings: Resume Example

### Without Resumability

```
Run 1 (interrupted after 3 stories): 45 minutes
Run 2 (start from beginning):
  - Story 1: 15 min (unnecessary!)
  - Story 2: 15 min (unnecessary!)
  - Story 3: 15 min (unnecessary!)
  - Stories 4-20: 255 min
  Total: 300 minutes (5 hours)
```

**Wasted time: 45 minutes** re-doing stories 1-3

### With Resumability

```
Run 1 (interrupted after 3 stories): 45 minutes
Run 2 (resume):
  - Stories 1-3: < 3 seconds (skipped!)
  - Stories 4-20: 255 min
  Total: 255 minutes (4.25 hours)
```

**Saved time: 45 minutes!**

For 20 stories with 3 interruptions: **Saves 2+ hours**

## Summary

### Your Subway Scenario

```
1. Start batch at home before leaving
   ✓ Stories 1-7 complete

2. Go to subway (lose internet)
   ✗ Story 8 fails (network error)
   ⊗ Stories 9-20 pending

3. Come home, run same command
   ✓ Stories 1-7 skipped (instant)
   ⟳ Story 8 retries (network restored)
   ⟳ Stories 9-20 process normally
```

**Result: Fully resumable! Zero manual intervention needed!**

### Quick Reference

```bash
# Start batch
./run_batch_resumable.sh run_gutenberg_videos.sh

# Resume (same command)
./run_batch_resumable.sh run_gutenberg_videos.sh

# Check progress
cat batch_progress_gutenberg_stories.json | jq .stats

# Start fresh
rm batch_progress_*.json
./run_batch_resumable.sh run_gutenberg_videos.sh
```

### Key Files

- `run_batch_resumable.sh` - Main entry point (run this!)
- `scripts/batch_manager.py` - Batch logic
- `batch_progress_*.json` - Progress state (auto-saved)
- Output directories - Stage fingerprints (auto-saved)

---

**Bottom line:** Yes, you can absolutely start a batch, lose internet, and resume later! The system handles it automatically with zero manual intervention. 🎉
