# YouTube Shorts Workflow - Complete Guide

## Overview

Convert existing episodes to TikTok shorts and automatically upload them to YouTube to drive traffic to your main video.

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   COMPLETE WORKFLOW                          │
└─────────────────────────────────────────────────────────────┘

INPUT: Full episode (e.g., Animal Farm E1 with 63 scenes)
   ↓
STEP 1: Convert to TikTok shorts (10 clips)
   ↓
STEP 2: Upload to YouTube with links to main video
   ↓
OUTPUT: 10 YouTube shorts driving traffic to main episode
```

## Prerequisites

### 1. Install Python Dependencies

```bash
pip install google-auth-oauthlib google-api-python-client
```

### 2. Set Up YouTube API Credentials

Follow **YOUTUBE_API_SETUP_GUIDE.md** to:
1. Create Google Cloud Project
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials
4. Download `client_secret.json`
5. Place in `credentials/client_secret.json`

### 3. Test Authentication

```bash
python scripts/test_youtube_auth.py
```

Expected output:
```
============================================================
✅ SUCCESS - Authentication working!
============================================================
```

## Step-by-Step Workflow

### Step 1: Convert Episode to TikTok Shorts

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1 \
  --clip-count 10
```

**Result:**
```
output/tiktok/animal_farm_e1/
├── clip_001.mp4
├── clip_002.mp4
├── ...
└── clip_010.mp4
```

### Step 2: Upload Main Video to YouTube (Manual)

1. Go to [YouTube Studio](https://studio.youtube.com/)
2. Upload full episode: `output/animal_farm_ep1_full_slides/Old_Major's_Dream_slides.mp4`
3. Set title: "Animal Farm Episode 1: Old Major's Dream"
4. Publish and copy video URL (e.g., `https://www.youtube.com/watch?v=ABC123`)

### Step 3: Batch Upload Shorts to YouTube

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm,animation,georgeorwell"
```

**What this does:**
- Uploads all 10 clips to YouTube
- Automatically adds `#shorts` tag
- Adds link to main video in description
- Generates titles: "Animal Farm Episode 1 - Part 1", "Part 2", etc.
- Tracks progress in `.upload_progress.json`

**Output:**
```
[1/10] Uploading clip_001
⬆️  Uploading: Animal Farm Episode 1 - Part 1
   File: clip_001.mp4
   Size: 0.5 MB
   Duration: 8.4s
   Type: Short
✓ Upload successful!
   Video ID: XYZ123
   URL: https://www.youtube.com/watch?v=XYZ123

... (9 more clips) ...

============================================================
📊 UPLOAD SUMMARY
============================================================
Total clips: 10
Uploaded: 10 ✓
Failed: 0 ✗
Skipped: 0 ⏭️
============================================================
```

## Real-World Example: Animal Farm E1

### Complete Command Sequence

```bash
# Step 1: Convert episode to shorts
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1 \
  --clip-count 10

# Step 2: Upload main video manually (get URL)

# Step 3: Batch upload shorts
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1: Old Major's Dream" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm,animation,georgeorwell,story"
```

### Result

**10 YouTube shorts created:**
- Animal Farm Episode 1 - Part 1
- Animal Farm Episode 1 - Part 2
- ...
- Animal Farm Episode 1 - Part 10

**Each short has:**
```
Title: Animal Farm Episode 1 - Part 3
Description:
  Part 3 of 10

  Animal Farm Episode 1: Old Major's Dream

  #shorts

  🎬 Watch full episode: https://www.youtube.com/watch?v=ABC123
```

## Advanced Features

### Resume Interrupted Upload

If upload fails partway through, just rerun the command:

```bash
# Same command - automatically resumes!
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

Progress is saved in `.upload_progress.json`, skips already uploaded clips.

### Upload Single Clip

```bash
python scripts/youtube_uploader.py \
  --video output/tiktok/animal_farm_e1/clip_001.mp4 \
  --title "Animal Farm - Part 1" \
  --description "Opening scene from Animal Farm" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm"
```

### Custom Title Template

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm EP1" \
  --title-template "📖 {episode_title} - Part {clip_num}/{total_clips}" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

Result: "📖 Animal Farm EP1 - Part 1/10"

### Upload as Unlisted (Testing)

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --privacy unlisted \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

## Cost Analysis

### Traditional Approach

1. Create 10 shorts from scratch: $1.52
2. Manual upload: Free but time-consuming (~30 min)

**Total: $1.52 + 30 minutes**

### With Automation

1. Convert existing episode to shorts: $0.00 (reuse existing MP4s)
2. Automated upload: Free and fast (~5 minutes)

**Total: $0.00 + 5 minutes**

**Savings: 100% cost, 83% time**

## YouTube Shorts Algorithm Tips

### 1. Upload Strategy

**Option A: All at once**
- Upload all 10 shorts immediately
- YouTube algorithm sees content burst
- Good for initial launch

**Option B: Scheduled release**
- Upload as unlisted first
- Schedule 1 short per day over 10 days
- Sustained engagement
- Better for long-term growth

### 2. Title Best Practices

```
✓ GOOD: "Animal Farm Episode 1 - Part 3"
✗ BAD:  "clip_003"

✓ GOOD: "📖 Animal Farm - The Rebellion Begins (Part 5)"
✗ BAD:  "Animal Farm Video 5"
```

### 3. Description Best Practices

```
Part 3 of 10

Animal Farm Episode 1: Old Major's Dream

In this part, Old Major reveals his revolutionary vision to the animals of Manor Farm.

#shorts #animalfarm #animation #story #georgeorwell

🎬 Watch full episode: https://www.youtube.com/watch?v=ABC123
```

### 4. Engagement Hooks

Add to description:
- "👇 Watch the full episode to see what happens next!"
- "🔥 This is just the beginning..."
- "⚠️ Warning: Major plot twist in full episode"

## Troubleshooting

### Error: "client_secret.json not found"

**Solution:**
```bash
# Check if file exists
ls credentials/client_secret.json

# If missing, follow YOUTUBE_API_SETUP_GUIDE.md
```

### Error: "Quota exceeded"

YouTube API has daily limits:
- Daily quota: 10,000 units
- Upload cost: 1,600 units
- Max uploads per day: 6 videos

**Solution:**
- Wait until next day (quota resets midnight Pacific Time)
- Request quota increase in Google Cloud Console
- Upload as unlisted, publish later

### Error: "Access blocked: has not completed Google verification"

**Solution:**
- Add your Google account as test user
- Google Cloud Console → OAuth consent screen → Test users → Add Users

### Upload Interrupted

**Solution:**
```bash
# Just rerun - automatically resumes from where it stopped
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

## File Structure

```
the-arabian-nights/
├── credentials/
│   ├── client_secret.json           # OAuth credentials
│   └── youtube_token.pickle         # Saved auth token
├── scripts/
│   ├── convert_episode_to_tiktok.py # Convert episode to shorts
│   ├── test_youtube_auth.py         # Test authentication
│   ├── youtube_uploader.py          # Upload single video
│   └── upload_tiktok_batch.py       # Batch upload shorts
├── output/
│   ├── animal_farm_ep1_full_slides/ # Original episode
│   └── tiktok/
│       └── animal_farm_e1/          # TikTok shorts
│           ├── clip_001.mp4
│           ├── ...
│           └── .upload_progress.json
└── YOUTUBE_SHORTS_WORKFLOW.md       # This file
```

## Summary

```
┌──────────────────────────────────────────────────────────────┐
│              YOUTUBE SHORTS AUTOMATION                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  INPUT:  Full episode with 63 scenes                         │
│  OUTPUT: 10 YouTube shorts driving traffic                   │
│                                                               │
│  ✅ Zero cost (reuse existing MP4s)                          │
│  ✅ Automated upload with progress tracking                  │
│  ✅ Auto-add #shorts tag                                     │
│  ✅ Auto-link to main video                                  │
│  ✅ Resume on interruption                                   │
│  ✅ Smart title generation                                   │
│                                                               │
│  ⏱️  Time: ~5 minutes (vs 30 minutes manual)                │
│  💰 Cost: $0.00 (vs $1.52 regeneration)                     │
│  📈 Result: 10 shorts → drive traffic to main video         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Next Steps

1. **Set up credentials** (YOUTUBE_API_SETUP_GUIDE.md)
2. **Test authentication** (`python scripts/test_youtube_auth.py`)
3. **Convert episode to shorts** (`convert_episode_to_tiktok.py`)
4. **Upload main video** (manual, YouTube Studio)
5. **Batch upload shorts** (`upload_tiktok_batch.py`)
6. **Monitor performance** (YouTube Analytics)
7. **Iterate based on data** (adjust titles, tags, hooks)
