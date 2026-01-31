# TikTok Shorts - Quick Start Guide

## One-Liner

> **Generate 10 TikTok shorts from a story, then experiment with different art styles and voices without regenerating everything.**

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIKTOK SHORTS WORKFLOW                        │
└─────────────────────────────────────────────────────────────────┘

INPUT: Story (5 minutes)
   ↓
SPLIT: 10 clips (30-45s each)
   ↓
GENERATE: Images + Audio + Video
   ↓
OUTPUT: 10 TikTok-ready MP4 files

THEN:
   ↓
RERUN: Different art style → Only regenerate images
   ↓
RERUN: Different voice → Only regenerate audio
   ↓
RESULT: Multiple variations without full regeneration!
```

## Basic Usage

### 1. Generate Initial Clips

```bash
python generate_video.py \
  --text resources/stories/gutenberg/01_the_call_of_cthulhu.txt \
  --tiktok-outputs output/tiktok/cthulhu \
  --art-reference resources/styles/vg_converted.jpg \
  --audio-reference resources/voices/sam-deep.mp3
```

**Result:**
```
output/tiktok/cthulhu/
├── clip_001.mp4  (35s) 📱
├── clip_002.mp4  (40s) 📱
├── clip_003.mp4  (38s) 📱
├── ...
└── clip_010.mp4  (42s) 📱
```

**Cost:** ~$1.52 (10 clips × $0.152)
**Time:** ~3 minutes

### 2. Try Different Art Style

```bash
python generate_video.py \
  --tiktok-outputs output/tiktok/cthulhu \
  --rerun-tiktok \
  --art-reference resources/styles/picasso.jpeg \
  --output-variation picasso
```

**Result:**
```
output/tiktok/cthulhu/
├── clip_001.mp4              (original - VG style)
├── clip_001_picasso.mp4      (NEW - Picasso style)
├── clip_002.mp4
├── clip_002_picasso.mp4
└── ...
```

**Cost:** ~$1.50 (images only, audio cached! ✅)
**Time:** ~1.5 minutes

### 3. Try Different Voice

```bash
python generate_video.py \
  --tiktok-outputs output/tiktok/cthulhu \
  --rerun-tiktok \
  --audio-reference resources/voices/nathan.mp3 \
  --output-variation dramatic
```

**Result:**
```
output/tiktok/cthulhu/
├── clip_001.mp4              (VG style, sam voice)
├── clip_001_picasso.mp4      (Picasso style, sam voice)
├── clip_001_dramatic.mp4     (NEW - VG style, nathan voice)
└── ...
```

**Cost:** ~$0.02 (audio only, images cached! ✅)
**Time:** ~1 minute

## Advanced Features

### Regenerate Specific Clips

```bash
# Only regenerate clips 4, 5, 6 with new style
python generate_video.py \
  --tiktok-outputs output/tiktok/cthulhu \
  --rerun-tiktok-clips 4,5,6 \
  --art-reference resources/styles/roman.jpg \
  --output-variation roman
```

**Cost:** ~$0.45 (3 clips × $0.15)

### Style Rotation

```bash
# Different style per clip (cycles through 3 styles)
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok/test \
  --tiktok-style-rotation "vg.jpg,picasso.jpeg,roman.jpg" \
  --audio-reference voice.mp3
```

**Result:**
- Clip 1: VG style
- Clip 2: Picasso style
- Clip 3: Roman style
- Clip 4: VG style (cycles)
- ...

### A/B Testing Matrix

```bash
# Generate ALL combinations (2 styles × 2 voices = 4 per clip)
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok/ab_test \
  --tiktok-ab-test \
  --art-references "vg.jpg,picasso.jpeg" \
  --audio-references "deep.mp3,calm.mp3"
```

**Result:**
```
output/tiktok/ab_test/
├── clip_001_vg_deep.mp4
├── clip_001_vg_calm.mp4
├── clip_001_picasso_deep.mp4
├── clip_001_picasso_calm.mp4
├── clip_002_vg_deep.mp4
└── ...
```

**Total outputs:** 40 videos (10 clips × 4 combinations)
**Cost:** ~$6.08

## File Structure

### After Initial Generation

```
output/tiktok/cthulhu/
├── .tiktok_manifest.json           # Config + metadata
├── clips/                          # Internal structure
│   ├── clip_001/
│   │   ├── .fingerprint.json       # Cache validation
│   │   ├── clip_config.json        # Clip metadata
│   │   ├── narration.json          # Scene data
│   │   ├── audio/
│   │   │   └── clip_001.wav
│   │   ├── images/
│   │   │   └── clip_001_9x16.png  (1080x1920)
│   │   └── clip_001_final.mp4
│   ├── clip_002/
│   └── ...
├── clip_001.mp4                    # Symlink to clips/clip_001/clip_001_final.mp4
├── clip_002.mp4
└── ...
```

### Manifest File

```json
{
  "version": "1.0",
  "story_source": "01_the_call_of_cthulhu.txt",
  "clip_count": 10,
  "config": {
    "target_duration": 40,
    "aspect_ratio": "9:16"
  },
  "clips": [
    {
      "clip_id": 1,
      "text_preview": "In the shadows of ancient...",
      "duration": 35,
      "art_style": {"reference": "vg.jpg", "hash": "f9cc..."},
      "voice": {"reference": "deep.mp3", "hash": "4b02..."},
      "status": "completed"
    }
  ],
  "variations": [
    {
      "variation_id": "picasso",
      "type": "art_style",
      "reference": "picasso.jpeg",
      "cost": 1.50
    },
    {
      "variation_id": "dramatic",
      "type": "voice",
      "reference": "nathan.mp3",
      "cost": 0.02
    }
  ]
}
```

## How Caching Works

### Fingerprint per Clip

```python
Clip Fingerprint = SHA256({
    'text': 'hash_of_clip_text',
    'art': 'hash_of_art_reference',
    'voice': 'hash_of_voice_reference',
    'params': {...}
})
```

### Regeneration Logic

```
Change Art Style:
  ✓ Narration: Cache (text unchanged)
  ✓ Audio: Cache (voice unchanged)
  ✗ Images: Regenerate (art changed)
  ✗ Video: Regenerate (images changed)

Change Voice:
  ✓ Narration: Cache (text unchanged)
  ✗ Audio: Regenerate (voice changed)
  ✓ Images: Cache (art unchanged)
  ✗ Video: Regenerate (audio changed)

Change Both:
  ✓ Narration: Cache (text unchanged)
  ✗ Audio: Regenerate (voice changed)
  ✗ Images: Regenerate (art changed)
  ✗ Video: Regenerate (both changed)
```

## TikTok Optimization

### 1. Vertical Format (9:16)

```
┌──────────────┐
│              │  ← Text overlay space
│   ┌──────┐   │
│   │      │   │
│   │ Main │   │  ← Focus area (upper center)
│   │Scene │   │
│   │      │   │
│   └──────┘   │
│              │  ← Caption space
│  @username   │  ← Branding
└──────────────┘
   1080x1920
```

### 2. Hook Structure

**First 3 seconds matter!**

Examples:
- ❓ **Question:** "What if everything you knew was a lie?"
- 🎭 **Shock:** "Nobody saw it coming..."
- 🔍 **Mystery:** "The secret that changed everything..."
- 🎯 **Promise:** "Wait until you see what happens next..."

### 3. Cliffhanger Structure

**Last 3 seconds drive to next clip!**

Examples:
- 🪝 **Tease:** "But then something unexpected happened..."
- ❓ **Question:** "The question is, what came next?"
- 💡 **Reveal:** "The truth was far more terrifying..."
- ➡️ **Continue:** "Part 2 reveals the shocking twist..."

## Cost Comparison

### Traditional Approach

```
Generate 10 clips with Style A: $1.52
Want to try Style B? Generate 10 MORE clips: $1.52
Want to try Style C? Generate 10 MORE clips: $1.52
Want to try Voice B? Generate 10 MORE clips: $1.52

Total: $6.08 for 4 variations
```

### With TikTok Shorts Feature

```
Generate 10 clips with Style A: $1.52
Try Style B? Regenerate images only: $1.50
Try Style C? Regenerate images only: $1.50
Try Voice B? Regenerate audio only: $0.02

Total: $4.54 for 4 variations
Savings: $1.54 (25%)
```

**For A/B testing (2 styles × 2 voices):**
- Traditional: $6.08 (generate each combination separately)
- With feature: $4.54 (smart caching)

## Real-World Workflow

### Content Creator Workflow

```
DAY 1: Generate initial batch
──────────────────────────────
$ python generate_video.py \
    --text horror_story.txt \
    --tiktok-outputs output/tiktok/horror_v1 \
    --art-reference dark_gothic.jpg \
    --audio-reference deep_voice.mp3

Result: 10 clips ready to post
Upload clip_001.mp4 to TikTok
Check engagement after 24 hours


DAY 2: Engagement is good, try different style
───────────────────────────────────────────────
$ python generate_video.py \
    --tiktok-outputs output/tiktok/horror_v1 \
    --rerun-tiktok \
    --art-reference anime_horror.jpg \
    --output-variation anime

Result: 10 NEW clips with anime style
Test clip_001_anime.mp4 on TikTok
Compare performance


DAY 3: Anime style performs better! Try voice variation
────────────────────────────────────────────────────────
$ python generate_video.py \
    --tiktok-outputs output/tiktok/horror_v1 \
    --rerun-tiktok \
    --art-reference anime_horror.jpg \
    --audio-reference whisper_voice.mp3 \
    --output-variation anime_whisper

Result: Combined best style + new voice
Post and optimize based on data
```

## Command Reference

```bash
# Basic generation
--tiktok-outputs <dir>              # Enable TikTok mode
--tiktok-count 10                   # Number of clips (default: 10)
--tiktok-duration 40                # Seconds per clip (default: 40)

# Regeneration
--rerun-tiktok                      # Regenerate all clips
--rerun-tiktok-clips 1,3,5          # Regenerate specific clips
--output-variation <name>           # Name for variation outputs

# Advanced
--tiktok-style-rotation <list>      # Rotate styles per clip
--tiktok-voice-rotation <list>      # Rotate voices per clip
--tiktok-ab-test                    # Generate all combinations

# Future features
--tiktok-captions                   # Add word-level captions
--tiktok-music <file>               # Background music
--tiktok-format square              # Square format (1:1) instead of vertical
```

## FAQ

**Q: Can I change both art and voice at once?**
A: Yes! Both will regenerate, only narration is cached.

**Q: What if I want to regenerate just one clip?**
A: `--rerun-tiktok-clips 5` regenerates only clip 5.

**Q: Can I test multiple styles without regenerating each time?**
A: Yes! Use `--tiktok-style-rotation` to generate different styles per clip in one run.

**Q: How long does initial generation take?**
A: ~3 minutes for 10 clips (20s per clip)

**Q: How long does art style regeneration take?**
A: ~1.5 minutes (only images regenerate, audio cached)

**Q: How long does voice regeneration take?**
A: ~1 minute (only audio regenerates, images cached)

**Q: Does this work with existing stories?**
A: Yes! Works with any text file.

## Summary

```
┌──────────────────────────────────────────────────────────────┐
│              TIKTOK SHORTS FEATURE SUMMARY                    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ✅ Generate 10 shorts from any story                        │
│  ✅ Regenerate with new art (cache audio)                    │
│  ✅ Regenerate with new voice (cache images)                 │
│  ✅ Selective regeneration (specific clips)                  │
│  ✅ Style/voice rotation (variety)                           │
│  ✅ A/B testing (all combinations)                           │
│  ✅ Fingerprint caching (avoid redundant work)               │
│  ✅ Vertical format (9:16 TikTok optimized)                  │
│  ✅ Hooks & cliffhangers (engagement optimized)              │
│                                                               │
│  💰 Cost: $1.52 for 10 clips                                 │
│  ⏱️  Time: 3 minutes initial, 1-2 min regeneration           │
│  💾 Savings: 25-98% on style/voice variations                │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Next:** See `TIKTOK_SHORTS_DESIGN.md` for full technical design.
