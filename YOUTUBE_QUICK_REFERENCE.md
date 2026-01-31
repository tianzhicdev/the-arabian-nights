# YouTube Shorts - Quick Reference Card

## Prerequisites (One-Time Setup)

```bash
# 1. Install dependencies
pip install -r requirements_youtube.txt

# 2. Follow YOUTUBE_API_SETUP_GUIDE.md to get credentials
# 3. Place credentials/client_secret.json

# 4. Test authentication
python scripts/test_youtube_auth.py
```

## Complete Workflow (3 Steps)

### Step 1: Convert Episode to Shorts

```bash
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1 \
  --clip-count 10
```

### Step 2: Upload Main Video (Manual)

1. Go to YouTube Studio
2. Upload full episode MP4
3. Copy video URL: `https://www.youtube.com/watch?v=ABC123`

### Step 3: Batch Upload Shorts

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm,animation"
```

## Common Commands

### Convert with Custom Selection

```bash
# First 10 scenes
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/EPISODE \
  --output-dir output/tiktok/NAME \
  --clip-count 10 \
  --clip-selection first

# Specific scenes
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/EPISODE \
  --output-dir output/tiktok/NAME \
  --clip-selection "1,5,10,15,20,25,30,35,40,45"
```

### Upload Single Video

```bash
python scripts/youtube_uploader.py \
  --video output/tiktok/animal_farm_e1/clip_001.mp4 \
  --title "Animal Farm - Part 1" \
  --description "Opening scene" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm"
```

### Upload as Unlisted (Testing)

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --privacy unlisted
```

### Resume Interrupted Upload

```bash
# Just rerun the same command - automatically resumes!
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

## Custom Templates

### Custom Title Format

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm EP1" \
  --title-template "📖 {episode_title} | Part {clip_num}" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

Result: "📖 Animal Farm EP1 | Part 1"

### Custom Description

```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1" \
  --description-template "Part {clip_num} of {total_clips}\n\n{episode_title}\n\n👇 Watch full episode below!" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123"
```

## File Locations

```
credentials/
├── client_secret.json       # From Google Cloud Console
└── youtube_token.pickle     # Auto-generated after first auth

output/tiktok/NAME/
├── clip_001.mp4
├── clip_002.mp4
├── ...
└── .upload_progress.json    # Resume tracking
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `client_secret.json not found` | Follow YOUTUBE_API_SETUP_GUIDE.md |
| `Quota exceeded` | Wait until tomorrow or request increase |
| `Access blocked` | Add your email as test user in Google Cloud Console |
| Upload interrupted | Rerun same command - auto-resumes |

## Daily Quota Limits

- **Daily quota**: 10,000 units
- **Upload cost**: 1,600 units per video
- **Max uploads/day**: ~6 videos
- **Quota reset**: Midnight Pacific Time

## Quick Example: Animal Farm E1

```bash
# Convert
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1 \
  --clip-count 10

# Upload (replace ABC123 with your video ID)
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1 \
  --episode-title "Animal Farm Episode 1: Old Major's Dream" \
  --main-video-url "https://www.youtube.com/watch?v=ABC123" \
  --tags "shorts,animalfarm,animation,georgeorwell,story"
```

## Next Episode Template

```bash
# Convert episode
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/EPISODE_DIR \
  --output-dir output/tiktok/EPISODE_NAME \
  --clip-count 10

# Upload shorts
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/EPISODE_NAME \
  --episode-title "FULL EPISODE TITLE" \
  --main-video-url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --tags "shorts,CUSTOM,TAGS,HERE"
```
