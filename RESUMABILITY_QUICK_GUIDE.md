# Resumability - Quick Visual Guide

## Your Question
> "Start batch, go to subway with no internet, come back home - can it resume?"

## Answer: YES! ✅

## How It Works (Visual)

```
┌─────────────────────────────────────────────────────────────────┐
│                    THREE LEVELS OF RESUMABILITY                  │
└─────────────────────────────────────────────────────────────────┘

Level 1: STAGE-LEVEL (Fingerprint Caching)
═══════════════════════════════════════════════════════════════════

Story 3 interrupted during image generation:

  output/03_cask_amontillado/
  ├── .fingerprint.json              ✅ Scenes complete
  ├── scenes.json
  ├── audio/
  │   ├── .fingerprint.json          ✅ Audio complete
  │   └── scene_*.wav
  ├── images/
  │   └── scene_001.png              ❌ Images incomplete (no fingerprint)
  └── video/                         ❌ Video not started

  On resume:
    ✓ Scenes: Skip (fingerprint exists)
    ✓ Audio: Skip (fingerprint exists)
    ⟳ Images: Regenerate (no fingerprint)
    ⟳ Video: Run
    ⟳ Assembly: Run

Level 2: STORY-LEVEL (Final Output Check)
═══════════════════════════════════════════════════════════════════

Story 1 & 2 already complete:

  output/01_call_of_cthulhu/
  └── The_Redirect_slides.mp4        ✅ Final video exists

  output/02_tell_tale_heart/
  └── System_Message_slides.mp4      ✅ Final video exists

  On resume:
    Story 1: Skip instantly (< 1 second)
    Story 2: Skip instantly (< 1 second)

Level 3: BATCH-LEVEL (Progress Tracking)
═══════════════════════════════════════════════════════════════════

batch_progress_gutenberg_stories.json:

  {
    "jobs": {
      "01_call_of_cthulhu": {"status": "completed"},    ✅
      "02_tell_tale_heart": {"status": "completed"},    ✅
      "03_cask_amontillado": {"status": "failed"},      ⚠️
      "04_gift_magi": {"status": "pending"}             ⊗
    },
    "stats": {
      "completed": 2,
      "failed": 1,
      "pending": 17
    }
  }

  On resume:
    Jobs 1-2: Skip (marked complete)
    Job 3: Retry (was failed)
    Jobs 4-20: Run normally
```

## Real Example: Your Subway Scenario

```
TIMELINE
════════════════════════════════════════════════════════════════════

🏠 At Home (15:00) - Start Batch
────────────────────────────────────────────────────────────────────
$ ./run_batch_resumable.sh run_gutenberg_videos.sh

[1/20] 01_call_of_cthulhu
  ⟳ Generating... ✓ Complete (15:03)

[2/20] 02_tell_tale_heart
  ⟳ Generating... ✓ Complete (15:07)

[3/20] 03_cask_amontillado
  ⟳ Scenes... ✓
  ⟳ Audio... ✓
  ⟳ Images... (50% done)


🚇 Enter Subway (15:10) - Lose Internet
────────────────────────────────────────────────────────────────────
[3/20] 03_cask_amontillado
  ⚠️ API Error: Connection timeout
  ⚠️ Retryable error. Waiting 2s...
  ⚠️ API Error: Connection timeout
  ⚠️ Retryable error. Waiting 4s...
  ⚠️ API Error: Connection timeout
  ✗ Failed (max retries)

[4/20] 04_gift_magi
  ⚠️ API Error: Connection timeout
  ✗ Failed

⚠️ Multiple failures detected. Consider checking network.
   Progress saved to: batch_progress_gutenberg_stories.json
   Run again to resume when network is available.


🏠 Back Home (18:00) - Resume
────────────────────────────────────────────────────────────────────
$ ./run_batch_resumable.sh run_gutenberg_videos.sh

📥 RESUMING BATCH (found 2 completed jobs)

[1/20] 01_call_of_cthulhu
  ✓ Already completed (< 1 second)

[2/20] 02_tell_tale_heart
  ✓ Already completed (< 1 second)

[3/20] 03_cask_amontillado
  ✓ Scenes cached (fingerprint match)
  ✓ Audio cached (fingerprint match)
  ⟳ Images regenerating... ✓
  ⟳ Video... ✓
  ⟳ Assembly... ✓
  ✓ Complete (18:05)

[4/20] 04_gift_magi
  ⟳ Generating... ✓ Complete (18:10)

[5/20] 05_yellow_wallpaper
  ⟳ Generating... ✓ Complete (18:15)

  ... continues through all 20 stories

BATCH COMPLETE (21:30)
Total time: 3.5 hours (vs 5 hours if restarted from scratch)
Saved time: 1.5 hours ⏱️
```

## What Gets Saved?

```
BEFORE INTERRUPTION                AFTER INTERRUPTION
═══════════════════════════════════════════════════════════════════

output/                            output/
├── 01_call_of_cthulhu/           ├── 01_call_of_cthulhu/
│   ├── .fingerprint.json ✅      │   ├── .fingerprint.json ✅
│   ├── audio/.fingerprint.json ✅│   ├── audio/.fingerprint.json ✅
│   ├── images/.fingerprint.json ✅│   ├── images/.fingerprint.json ✅
│   └── *_slides.mp4 ✅           │   └── *_slides.mp4 ✅
├── 02_tell_tale_heart/           ├── 02_tell_tale_heart/
│   ├── .fingerprint.json ✅      │   ├── .fingerprint.json ✅
│   ├── audio/.fingerprint.json ✅│   ├── audio/.fingerprint.json ✅
│   ├── images/.fingerprint.json ✅│   ├── images/.fingerprint.json ✅
│   └── *_slides.mp4 ✅           │   └── *_slides.mp4 ✅
└── 03_cask_amontillado/          └── 03_cask_amontillado/
    ├── .fingerprint.json ✅          ├── .fingerprint.json ✅
    ├── audio/.fingerprint.json ✅    ├── audio/.fingerprint.json ✅
    └── images/ (partial) ❌          └── images/ (partial) ❌

batch_progress_*.json:             batch_progress_*.json:
{                                  {
  "jobs": {                          "jobs": {
    "01_*": "completed" ✅             "01_*": "completed" ✅
    "02_*": "completed" ✅             "02_*": "completed" ✅
    "03_*": "running" ⟳                "03_*": "failed" ⚠️
  }                                    "04_*": "failed" ⚠️
}                                    }
                                   }

                                   ON RESUME:
                                   - 01, 02: Skip (complete)
                                   - 03: Retry from images
                                   - 04-20: Run normally
```

## Commands

```bash
# Start batch (first time or resume)
./run_batch_resumable.sh run_gutenberg_videos.sh

# That's it! Same command for start and resume.
# The script automatically detects if it's resuming.
```

## Key Features

```
┌─────────────────────────────────────────────────────────────┐
│  FEATURE                  │  HOW IT WORKS                   │
├─────────────────────────────────────────────────────────────┤
│  Resume after CTRL+C      │  Graceful shutdown, saves state │
│  Resume after power loss  │  Detects incomplete stages      │
│  Resume after network loss│  Retries failed jobs            │
│  Skip completed stories   │  < 1 second per story           │
│  Skip completed stages    │  Fingerprint validation         │
│  Retry API errors         │  3 attempts with backoff        │
│  Progress tracking        │  Shows 7/20, estimates time     │
│  Cost tracking            │  Records per-story costs        │
└─────────────────────────────────────────────────────────────┘
```

## Time Comparison

```
WITHOUT RESUMABILITY:
══════════════════════════════════════════════════════════════
Start: Process stories 1-3 (45 min)
[Interrupt]
Resume: Process 1-3 AGAIN (45 min wasted) + 4-20 (255 min)
Total: 300 minutes (5 hours)


WITH RESUMABILITY:
══════════════════════════════════════════════════════════════
Start: Process stories 1-3 (45 min)
[Interrupt]
Resume: Skip 1-3 (3 sec) + Process 4-20 (255 min)
Total: 255 minutes (4.25 hours)

SAVED: 45 minutes ⏱️
```

## Error Handling

```
ERROR TYPE          ACTION                      RESULT
═══════════════════════════════════════════════════════════════
429 Rate Limit     Retry 3x with backoff       Usually succeeds
Connection Timeout Retry 3x with backoff       Usually succeeds
503 Server Error   Retry 3x with backoff       Usually succeeds
400 Bad Request    Fail immediately            Log and continue
Auth Error         Fail immediately            User needs to fix
Network Down       Fail after 3 retries        Resume later
```

## Files You'll See

```
project/
├── run_batch_resumable.sh                    ← RUN THIS
├── batch_progress_gutenberg_stories.json     ← AUTO-CREATED
└── output/
    └── gutenberg/
        ├── 01_*/                             ← Story outputs
        │   ├── .fingerprint.json             ← Stage markers
        │   ├── audio/.fingerprint.json
        │   ├── images/.fingerprint.json
        │   └── *_slides.mp4
        └── 02_*/
            └── ...
```

## FAQ

**Q: Do I need to do anything special to resume?**
A: No! Just run the same command. It detects and resumes automatically.

**Q: What if I want to start fresh?**
A: `rm batch_progress_*.json` then run the script.

**Q: Can I check progress while running?**
A: Yes! `cat batch_progress_gutenberg_stories.json | jq .stats`

**Q: What if a story fails permanently?**
A: It logs the error, continues with other stories, you can fix and re-run.

**Q: Does this work with the old cache manager (V1)?**
A: Yes! Batch manager works with both V1 and V2 caching.

**Q: What if I run on a different machine?**
A: Copy the `output/` directory and `batch_progress_*.json` file.

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  YOUR SUBWAY SCENARIO                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🏠 Start batch at home                                     │
│     ✓ Stories 1-7 complete                                  │
│                                                              │
│  🚇 Lose internet in subway                                 │
│     ⚠️ Stories 8+ fail (network error)                      │
│     💾 Progress saved automatically                         │
│                                                              │
│  🏠 Resume at home                                          │
│     ✓ Stories 1-7 skipped (< 7 seconds)                     │
│     ⟳ Stories 8-20 process normally                         │
│                                                              │
│  ✅ RESULT: Fully resumable, zero manual work!             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Bottom line:** Start batch, lose internet, resume later - IT JUST WORKS! 🎉
