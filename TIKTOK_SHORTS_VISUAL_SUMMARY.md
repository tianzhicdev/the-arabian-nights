# TikTok Shorts Feature - Visual Summary

## Problem → Solution

```
PROBLEM: Want to create TikTok content from stories
         Want to test different art styles and voices
         Don't want to regenerate everything each time

SOLUTION: --tiktok-outputs feature with smart caching
```

## Visual Workflow

```
┌────────────────────────────────────────────────────────────────┐
│                     ONE STORY → 10 TIKTOK SHORTS               │
└────────────────────────────────────────────────────────────────┘

INPUT                          
┌──────────────────┐           
│  Story (5 min)   │           
│  • Horror tale   │           
│  • 1500 words    │           
└──────────────────┘           
         ↓                     
    [AI SPLIT]                 
         ↓                     
┌──────────────────┐           
│  10 Clips        │           
│  • 30-45s each   │           
│  • Hooks         │           
│  • Cliffhangers  │           
└──────────────────┘           
         ↓                     
    [GENERATE]                 
         ↓                     
┌──────────────────┐           
│  10 MP4 Files    │           
│  • Vertical 9:16 │           
│  • TikTok ready  │           
└──────────────────┘           

THEN EXPERIMENT:

Try Style B              Try Voice B               Try Both
    ↓                        ↓                         ↓
[Regenerate Images]     [Regenerate Audio]      [Regenerate Both]
    ↓                        ↓                         ↓
10 New Videos           10 New Videos            10 New Videos
(audio cached!)         (images cached!)         (narration cached!)
```

## Command Comparison

### Traditional Way (Manual)

```bash
# Generate with Style A + Voice A
python generate_video.py ... --art style_a.jpg --audio voice_a.mp3
# Output: 10 clips ($1.52)

# Want Style B? Generate 10 MORE clips from scratch
python generate_video.py ... --art style_b.jpg --audio voice_a.mp3
# Output: 10 MORE clips ($1.52)

# Want Voice B? Generate 10 MORE clips from scratch
python generate_video.py ... --art style_a.jpg --audio voice_b.mp3
# Output: 10 MORE clips ($1.52)

Total: 30 clips generated, $4.56
Problem: Lots of redundant work!
```

### New Way (Smart Caching)

```bash
# Generate initial
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok/test \
  --art style_a.jpg --audio voice_a.mp3
# Output: 10 clips ($1.52)

# Try Style B (audio cached!)
python generate_video.py \
  --tiktok-outputs output/tiktok/test \
  --rerun-tiktok --art style_b.jpg --output-variation style_b
# Output: 10 clips ($1.50 - only images regenerated!)

# Try Voice B (images cached!)
python generate_video.py \
  --tiktok-outputs output/tiktok/test \
  --rerun-tiktok --audio voice_b.mp3 --output-variation voice_b
# Output: 10 clips ($0.02 - only audio regenerated!)

Total: 30 clips output, $3.04
Savings: $1.52 (33%)
```

## File Structure Visual

```
output/tiktok/horror/
│
├── 📄 .tiktok_manifest.json          "Master config"
│
├── 📁 clips/                         "Internal structure"
│   ├── 📁 clip_001/
│   │   ├── 🔑 .fingerprint.json      "Cache key"
│   │   ├── 📝 clip_config.json       "Metadata"
│   │   ├── 📝 narration.json         "Scene data"
│   │   ├── 🔊 audio/clip_001.wav
│   │   ├── 🖼️  images/clip_001_9x16.png
│   │   └── 🎬 clip_001_final.mp4
│   │
│   ├── 📁 clip_002/ ...
│   └── 📁 clip_003/ ...
│
├── 🎬 clip_001.mp4                   "Original (symlink)"
├── 🎬 clip_001_anime.mp4             "Anime style variation"
├── 🎬 clip_001_whisper.mp4           "Whisper voice variation"
│
├── 🎬 clip_002.mp4
├── 🎬 clip_002_anime.mp4
└── ...
```

## Caching Decision Tree

```
User Changes Art Style?
    │
    ├─ YES → Fingerprint Changes
    │         │
    │         ├─ Narration: ✓ CACHE (text unchanged)
    │         ├─ Audio:     ✓ CACHE (voice unchanged)
    │         ├─ Images:    ✗ REGENERATE (art changed)
    │         └─ Video:     ✗ REGENERATE (images changed)
    │
    └─ NO → Fingerprint Match
              └─ Use all cached ✓

User Changes Voice?
    │
    ├─ YES → Fingerprint Changes
    │         │
    │         ├─ Narration: ✓ CACHE (text unchanged)
    │         ├─ Audio:     ✗ REGENERATE (voice changed)
    │         ├─ Images:    ✓ CACHE (art unchanged)
    │         └─ Video:     ✗ REGENERATE (audio changed)
    │
    └─ NO → Fingerprint Match
              └─ Use all cached ✓
```

## Cost Breakdown Visual

```
┌─────────────────────────────────────────────────────────────┐
│                  COST PER CLIP BREAKDOWN                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Narration:  $0.002  ████                                   │
│  Audio:      $0.000  Free (Chatterbox local)                │
│  Image:      $0.150  ████████████████████████████████████   │
│  Video:      $0.000  Free (FFmpeg)                          │
│  ─────────────────────────────────────────────────────────  │
│  TOTAL:      $0.152                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

10 Clips = $1.52

REGENERATION COSTS:

Change Art:    $1.50  (images only - 99% of cost)
Change Voice:  $0.02  (narration + audio - 1% of cost!)
Change Both:   $1.52  (full regeneration)
```

## Real-World Example

```
DAY 1: Generate Horror Content
──────────────────────────────────────────────────────────────
$ python generate_video.py \
    --text horror_story.txt \
    --tiktok-outputs output/tiktok/horror_v1 \
    --art gothic_dark.jpg \
    --audio deep_narrator.mp3

✓ 10 clips generated (3 minutes, $1.52)
├─ clip_001.mp4 (35s)
├─ clip_002.mp4 (42s)
├─ clip_003.mp4 (38s)
└─ ... clip_010.mp4 (40s)

Upload to TikTok → Track engagement


DAY 2: Engagement Good, Try Anime Style
──────────────────────────────────────────────────────────────
$ python generate_video.py \
    --tiktok-outputs output/tiktok/horror_v1 \
    --rerun-tiktok \
    --art anime_horror.jpg \
    --output-variation anime

✓ 10 NEW clips (1.5 minutes, $1.50 - audio cached!)
├─ clip_001_anime.mp4
├─ clip_002_anime.mp4
└─ ...

Test on TikTok → Anime performs better!


DAY 3: Try Whisper Voice with Anime Style
──────────────────────────────────────────────────────────────
$ python generate_video.py \
    --tiktok-outputs output/tiktok/horror_v1 \
    --rerun-tiktok \
    --art anime_horror.jpg \
    --audio whisper_narrator.mp3 \
    --output-variation anime_whisper

✓ 10 NEW clips (1 minute, $0.02 - images cached!)
├─ clip_001_anime_whisper.mp4
├─ clip_002_anime_whisper.mp4
└─ ...

Winner found: Anime + Whisper
Total spent: $3.04 (vs $4.56 without caching)
```

## Feature Matrix

```
┌──────────────────────────────────────────────────────────────┐
│ FEATURE                    │ STATUS  │ BENEFIT               │
├────────────────────────────┼─────────┼───────────────────────┤
│ Generate 10 shorts         │ ✅ Design│ TikTok content       │
│ Vertical format (9:16)     │ ✅ Design│ Mobile optimized     │
│ Smart art regeneration     │ ✅ Design│ $1.50 vs $1.52       │
│ Smart voice regeneration   │ ✅ Design│ $0.02 vs $1.52 (97%)│
│ Selective clip regen       │ ✅ Design│ Target specific clips│
│ Style rotation             │ ✅ Design│ Variety per clip     │
│ Voice rotation             │ ✅ Design│ Variety per clip     │
│ A/B testing matrix         │ ✅ Design│ Test combinations    │
│ Hooks & cliffhangers       │ ✅ Design│ Engagement boost     │
│ Word-level captions        │ 📋 Future│ Accessibility        │
│ Background music           │ 📋 Future│ Production value     │
└──────────────────────────────────────────────────────────────┘
```

## Commands Quick Reference

```bash
# BASIC
--tiktok-outputs <dir>              Generate 10 clips
--tiktok-count 15                   Generate 15 clips
--tiktok-duration 45                45s per clip

# REGENERATION
--rerun-tiktok                      Regenerate all
--rerun-tiktok-clips 1,3,5          Regenerate specific
--output-variation <name>           Name the variation

# ADVANCED
--tiktok-style-rotation <list>      Different style per clip
--tiktok-voice-rotation <list>      Different voice per clip
--tiktok-ab-test                    All combinations
```

## Bottom Line

```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│  INPUT:  One story (5 minutes)                             │
│  OUTPUT: 10 TikTok shorts (30-45s each)                    │
│                                                             │
│  ✨ MAGIC: Smart caching                                   │
│                                                             │
│  Try new art:   $1.50 (vs $1.52 regenerate all)           │
│  Try new voice: $0.02 (vs $1.52 regenerate all)           │
│                                                             │
│  💰 SAVINGS: 33-97% on variations                          │
│  ⏱️  SPEED:   37-67% faster iterations                     │
│                                                             │
│  🎯 PERFECT FOR: Content creators testing styles/voices    │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

**Read the docs:**
- 📖 `TIKTOK_SHORTS_QUICKSTART.md` - Start here!
- 📐 `TIKTOK_SHORTS_DESIGN.md` - Full technical design
- 📝 `TIKTOK_FEATURE_SUMMARY.md` - Feature summary
