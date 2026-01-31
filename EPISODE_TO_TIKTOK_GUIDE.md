# Episode to TikTok Converter - Quick Guide

## Overview

Convert existing full episodes into TikTok shorts with **smart MP4 reuse**. No regeneration unless you specify voice or art overrides!

## Key Feature

> **When no overrides are specified, the converter just copies existing MP4s to the output directory. Zero regeneration cost!**

## Basic Usage

### 1. Convert with No Overrides (Just Reuse Existing MP4s)

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1 \
  --clip-count 10
```

**Result:**
- Selects 10 scenes evenly distributed across the episode
- Copies existing MP4s (no regeneration!)
- Creates manifest tracking source scenes

**Output:**
```
output/tiktok/animal_farm_e1/
├── clip_001.mp4  (copied from source)
├── clip_002.mp4
├── ...
├── clip_010.mp4
└── .tiktok_manifest.json
```

### 2. Convert with Voice Override (Regenerate Audio)

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1_voice2 \
  --clip-count 10 \
  --voice-override resources/voices/nathan.mp3
```

**Result:**
- Regenerates audio with new voice
- Reuses existing images
- Creates new MP4s

### 3. Convert with Art Style Override (Regenerate Images)

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1_anime \
  --clip-count 10 \
  --art-override resources/styles/anime.jpg
```

**Result:**
- Regenerates images with new art style
- Reuses existing audio
- Creates new MP4s

## Clip Selection Methods

### Auto (Default - Evenly Distributed)

```bash
--clip-selection auto
```

Selects clips evenly across the episode (e.g., scenes 1, 7, 13, 19, 25, 31, 37, 43, 49, 55 for 10 clips from 63 scenes)

### First N Clips

```bash
--clip-selection first
```

Takes first N scenes (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

### Last N Clips

```bash
--clip-selection last
```

Takes last N scenes

### Specific Clips by Index

```bash
--clip-selection "1,5,10,15,20,25,30,35,40,45"
```

Select specific scenes by number (1-indexed)

## Real-World Example: Animal Farm E1

```bash
# Generate 10 TikTok clips from Animal Farm E1
cd /Users/biubiu/projects/the-arabian-nights

python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1_test \
  --clip-count 10 \
  --clip-selection auto
```

**Output:**
```
🎬 Converting episode to TikTok shorts
   Episode: animal_farm_ep1_full_slides
   Clips: 10
   Voice override: None (reuse)
   Art override: None (reuse)

✓ Selected 10 scenes

📹 Processing clip 1/10
   ✓ Reused: clip_001.mp4 (8.4s)

... (9 more clips) ...

============================================================
📊 CONVERSION SUMMARY
============================================================
Total clips: 10
Reused clips: 10 ✓
Regenerated clips: 0 ⟳
Total duration: 124.6s (2.1 min)

Output directory: output/tiktok/animal_farm_e1_test
============================================================
```

## Manifest File

The converter creates `.tiktok_manifest.json` with:

```json
{
  "version": "1.0",
  "source_episode": "animal_farm_ep1_full_slides",
  "clip_count": 10,
  "config": {
    "voice_override": null,
    "art_override": null,
    "clip_selection": "auto"
  },
  "clips": [
    {
      "clip_id": 1,
      "source_scene_id": 1,
      "source_mp4": "video/scene_001_with_audio.mp4",
      "output_mp4": "clip_001.mp4",
      "reused": true,
      "regenerated_components": [],
      "duration": 8.36
    }
  ],
  "statistics": {
    "reused_count": 10,
    "regenerated_count": 0,
    "total_duration": 124.56
  }
}
```

## Cost Comparison

### Traditional Approach (Regenerate Everything)

```
10 clips × $0.152 per clip = $1.52
```

### With Converter (Reuse Existing MP4s)

```
10 clips × $0.00 (just copy) = $0.00
```

**Savings: 100% when no overrides specified!**

## Command Reference

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir <path>              # Required: Episode directory
  --output-dir <path>               # Required: Output directory
  --clip-count <int>                # Number of clips (default: 10)
  --voice-override <path>           # Optional: New voice reference
  --art-override <path>             # Optional: New art reference
  --clip-selection <method>         # auto, first, last, or "1,5,10"
```

## Current Limitations

1. **Clip Duration**: Current clips are 8-16s each (shorter than ideal TikTok length of 30-60s)
   - Future enhancement: Combine multiple scenes per clip to reach target duration

2. **Regeneration Not Implemented**: `--voice-override` and `--art-override` currently just copy existing MP4s
   - Future enhancement: Implement actual audio/image regeneration

3. **Vertical Format**: Existing MP4s may not be 9:16 vertical format
   - Future enhancement: Crop/resize to TikTok's 9:16 aspect ratio

## Next Steps

To make this production-ready:

1. **Implement regeneration logic** in `_regenerate_clip()`:
   - Audio regeneration with new voice
   - Image regeneration with new art style
   - Video assembly with FFmpeg

2. **Add clip combining** to reach 30-60s target:
   - Combine 3-4 short scenes into one TikTok clip
   - Preserve narrative flow

3. **Add vertical format conversion**:
   - Crop/resize existing MP4s to 9:16 if needed
   - Center focus area for mobile viewing

4. **Add hooks and cliffhangers**:
   - Use AI to generate engaging hooks
   - Add cliffhangers between clips

## Summary

```
┌──────────────────────────────────────────────────────────────┐
│           EPISODE TO TIKTOK CONVERTER                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  INPUT:  Existing episode with 63 scenes                     │
│  OUTPUT: 10 TikTok clips (evenly distributed)                │
│                                                               │
│  ✅ No regeneration when no overrides specified              │
│  ✅ Just copy existing MP4s to output directory              │
│  ✅ Smart selection (auto, first, last, custom)              │
│  ✅ Manifest tracks source scenes                            │
│  ✅ Future: Voice/art override regeneration                  │
│                                                               │
│  💰 Cost: $0.00 (when reusing existing MP4s)                 │
│  ⏱️  Time: <5 seconds (just file copy)                       │
│  💾 Zero regeneration = 100% cost savings                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```
