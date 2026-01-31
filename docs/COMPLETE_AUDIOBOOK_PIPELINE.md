# Complete Audiobook-to-YouTube Pipeline

Automated end-to-end pipeline for converting books into professional audiobooks with promotional videos, ready for YouTube upload.

## Overview

**Input:** Text file or Gutenberg URL + Voice ID
**Output:** Complete audiobook (videos with opening/background) + Promotional shorts → Uploaded to YouTube

### Pipeline Stages

```
📚 TXT/URL
   ↓
1. Generate Audiobook JSON (with promotional shorts + Film Noir style guide)
   ↓
2. Generate Episode TTS Audio (ElevenLabs)
   ↓
3. Generate Promotional TTS Audio (ElevenLabs with timing)
   ↓
4. Generate Background Images (DALL-E, Van Gogh impressionist style)
   ↓
5. Create Episode Videos (opening logo + background + audio)
   ↓
6. Generate Promotional Videos (Sora + vertical format + 10s ending)
   ↓
7. Upload to YouTube (episode videos + shorts with metadata)
```

## Quick Start

### One-Command Pipeline

```bash
python scripts/audiobook_pipeline_complete.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/audiobook_pipeline/shooting_an_elephant \
  --voice-id ePiPWpzcHZrcqRzFrgQg \
  --upload --upload-privacy public
```

This single command will:
1. Generate all JSON, audio, images, and videos
2. Upload everything to YouTube with proper metadata
3. Organize files for Mac Mini transfer

### Step-by-Step Workflow

For more control, run each stage separately:

#### Step 1: Generate Audiobook JSON with Promotional Shorts

```bash
python scripts/book_to_audiobook.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/audiobook_pipeline/shooting_an_elephant
```

**With semantic chapter inference:**
```bash
python scripts/book_to_audiobook.py \
  "https://gutenberg.net.au/ebooks02/0200991.txt" \
  --output-dir experiments/audiobook_pipeline/notes_from_underground \
  --infer-chapter
```

**Features:**
- Detects or infers chapters (~2000 words each)
- Creates story bible
- Generates narrated text with emotion tags
- **NEW:** Generates 2-3 promotional shorts per chapter with Film Noir style guide
- **NEW:** Structured scene descriptions (STYLE, SETTING, SUBJECT, CAMERA, LIGHTING, ACTION)
- **NEW:** JSON response format enforcement

#### Step 2: Generate Episode Audio

```bash
python scripts/generate_audiobook_audio.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json \
  --voice-id ePiPWpzcHZrcqRzFrgQg
```

**Output:** `episode_audio/episode_*.mp3`

#### Step 3: Generate Promotional Audio

```bash
python scripts/generate_promotional_audio.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json \
  --voice-id ePiPWpzcHZrcqRzFrgQg
```

**Output:**
- `promo_audio/chapter_*/short_*/scene_*.mp3`
- `audiobook_with_timing.json` (with timing metadata)

#### Step 4: Generate Background Images

```bash
python scripts/generate_episode_backgrounds.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json
```

**Features:**
- DALL-E 3 generated images
- Van Gogh impressionist style (references `resources/styles/vg_converted.jpg`)
- Abstract, atmospheric backgrounds
- One image per episode

**Output:** `episode_backgrounds/episode_*_background.png`

#### Step 5: Create Episode Videos

```bash
python scripts/create_episode_videos.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json \
  --voice-id ePiPWpzcHZrcqRzFrgQg
```

**Features:**
- Opening segment: Logo (`resources/wornhole-logo.png`) + TTS narration
- Main content: Background image + episode audio
- Horizontal format (1280x720)
- Proper concatenation

**Output:** `episode_videos/episode_*_final.mp4`

#### Step 6: Generate Promotional Videos

```bash
python scripts/generate_promotional_videos.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook_with_timing.json
```

**Features:**
- Sora 2 video generation with Film Noir style
- Vertical format (1080x1920) for TikTok/Instagram/YouTube Shorts
- **NEW:** 10-second ending segment (black background + logo + '@the-wormhole-podcast')
- Audio-video sync with silence padding
- Structured scene descriptions for consistency

**Output:** `promo_videos/chapter_*/SCENE_NAME_SHORT.mp4`

#### Step 7: Upload to YouTube

```bash
python scripts/upload_audiobook_to_youtube.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json \
  --privacy public
```

**Features:**
- Auto-generates metadata (title, description, tags)
- Category: Education (27)
- Auto-detects shorts (<60s) and adds #shorts tag
- Separate uploads for episode videos and shorts
- Upload summary with URLs

**Options:**
- `--episodes-only` - Upload only episode videos
- `--shorts-only` - Upload only promotional shorts
- `--privacy` - public, private, or unlisted

## Video Style Guides

### Available Styles

The pipeline includes 5 hardcoded style guides for visual consistency:

1. **Film Noir** (DEFAULT)
   - High-contrast black and white
   - Dramatic shadows, venetian blind lighting
   - Mysterious, tense atmosphere
   - Perfect for literary classics

2. **Studio Ghibli**
   - Hand-drawn animation style
   - Soft watercolor backgrounds
   - Whimsical, emotional atmosphere
   - Great for fantasy/adventure

3. **Impressionist**
   - Visible brushstrokes, vibrant colors
   - Emphasis on light and movement
   - Like Monet or Renoir
   - Ideal for romantic/artistic works

4. **Vintage Illustration**
   - Detailed pen and ink line work
   - Limited color palette, cross-hatching
   - Like Arthur Rackham or N.C. Wyeth
   - Perfect for classic literature

5. **Abstract Expressionist**
   - Bold colors, dynamic shapes
   - Emotional expression through abstract forms
   - Like Kandinsky or Rothko
   - Great for experimental/modern works

### Changing the Style

Edit `scripts/book_to_audiobook.py`:

```python
# Line 559
DEFAULT_VIDEO_STYLE = "film_noir"  # Change to: studio_ghibli, impressionist, etc.
```

## File Organization

### Complete Directory Structure

```
experiments/audiobook_pipeline/shooting_an_elephant/
├── audiobook.json                      # Original JSON with shorts
├── audiobook_with_timing.json          # With timing metadata
├── book_raw.txt                        # Downloaded source text
│
├── original_chapters/                  # Chapter text files
│   ├── chapter_01_*.txt
│   └── ...
│
├── episode_audio/                      # Episode TTS audio
│   ├── episode_01.mp3
│   ├── episode_02.mp3
│   └── ...
│
├── episode_backgrounds/                # DALL-E generated backgrounds
│   ├── episode_01_background.png
│   ├── episode_02_background.png
│   └── ...
│
├── episode_videos/                     # Final episode videos
│   ├── episode_01_temp/               # Temporary files
│   │   ├── opening_audio.mp3
│   │   ├── opening_video.mp4
│   │   └── main_video.mp4
│   ├── episode_01_final.mp4          # FINAL VIDEO
│   └── ...
│
├── promo_audio/                        # Promotional TTS audio
│   ├── chapter_01/
│   │   ├── short_01/
│   │   │   ├── scene_01.mp3
│   │   │   └── ...
│   │   └── short_02/
│   └── ...
│
└── promo_videos/                       # Promotional videos
    ├── chapter_01/
    │   ├── short_01/
    │   │   ├── scene_01_raw.mp4          # Sora output
    │   │   ├── scene_01_vertical.mp4     # Converted to 1080x1920
    │   │   ├── scene_01_audio_padded.mp3 # Padded audio
    │   │   ├── scene_01_final.mp4        # Scene with audio
    │   │   └── ending_segment.mp4        # 10s ending
    │   └── TENSION_IN_THE_AIR_SHORT.mp4   # FINAL SHORT
    └── ...
```

## API Requirements

### Required API Keys

Set in `.env.secrets`:

```bash
ELEVEN_LABS_KEY=your_elevenlabs_key
OPEN_AI_API=your_openai_key
```

### YouTube API Setup

1. Follow `YOUTUBE_API_SETUP_GUIDE.md`
2. Place `client_secret.json` in `credentials/`
3. First run will authenticate and save token

### API Usage Estimates

For a 5-chapter book like "Shooting an Elephant":

- **ElevenLabs:**
  - Episode audio: ~15,000 characters
  - Promo audio: ~5,000 characters
  - **Total:** ~20,000 characters

- **OpenAI:**
  - JSON generation: ~$0.50
  - DALL-E images (5): ~$0.20
  - Sora videos (11 shorts, ~50 scenes): ~$50-100
  - **Total:** ~$50-100

- **YouTube:**
  - Uploads: Free (within quota)
  - Daily quota: 10,000 units
  - Each upload: ~1,600 units
  - **Limit:** ~6 videos/day

## Mac Mini Transfer

### Preparing Files for Mac Mini

1. **Complete Pipeline:**
   ```bash
   python scripts/audiobook_pipeline_complete.py <book_url> \
     --output-dir experiments/audiobook_pipeline/<book_name> \
     --voice-id <voice_id>
   ```

2. **Transfer to Mac Mini:**
   ```bash
   scp -r experiments/audiobook_pipeline/<book_name> \
     user@macmini:/path/to/upload/queue/
   ```

3. **Mac Mini Scheduled Upload:**
   - Mac Mini runs scheduled script to upload queued content
   - Uploads at specified times to stay within YouTube quota
   - Tracks uploaded videos to avoid duplicates

## Advanced Options

### Skip Stages

Resume from any point by skipping completed stages:

```bash
python scripts/audiobook_pipeline_complete.py <book_url> \
  --output-dir <dir> \
  --skip-episode-audio \
  --skip-promo-audio \
  --skip-backgrounds \
  --skip-episode-videos \
  --skip-promo-videos
```

### Custom Voice

```bash
python scripts/audiobook_pipeline_complete.py <book_url> \
  --output-dir <dir> \
  --voice-id <your_custom_voice_id>
```

### Private Upload for Testing

```bash
python scripts/audiobook_pipeline_complete.py <book_url> \
  --output-dir <dir> \
  --upload \
  --upload-privacy private
```

## Troubleshooting

### Common Issues

1. **Sora Video Inconsistency:**
   - Solution: Enhanced prompts with style guides now provide better consistency
   - Structured descriptions include STYLE, SETTING, SUBJECT, CAMERA, LIGHTING, ACTION
   - Film Noir style provides strong visual identity

2. **Logo Not Found:**
   - Error: `Logo not found: resources/wornhole-logo.png`
   - Solution: Note the typo - file is "wornhole" not "wormhole"
   - Create symlink or rename: `mv resources/wornhole-logo.png resources/wormhole-logo.png`

3. **YouTube Upload Quota:**
   - Error: Quota exceeded
   - Solution: YouTube allows ~6 uploads/day
   - Use `--upload-privacy private` for testing
   - Schedule uploads across multiple days

4. **FFmpeg Errors:**
   - Ensure ffmpeg and ffprobe are installed: `brew install ffmpeg`
   - Check video codec compatibility
   - Try re-encoding: `-c:v libx264 -pix_fmt yuv420p`

## Scripts Reference

### Main Scripts

1. `audiobook_pipeline_complete.py` - Master pipeline orchestrator
2. `book_to_audiobook.py` - JSON generation with promotional shorts
3. `generate_audiobook_audio.py` - Episode TTS audio
4. `generate_promotional_audio.py` - Promotional TTS audio with timing
5. `generate_episode_backgrounds.py` - DALL-E background images
6. `create_episode_videos.py` - Episode videos (opening + background + audio)
7. `generate_promotional_videos.py` - Sora videos (vertical + ending)
8. `upload_audiobook_to_youtube.py` - YouTube upload with metadata

### Supporting Scripts

- `create_episode_opening.py` - Logo opening generator (standalone)
- `make_short_video.py` - Branding overlay utility (standalone)
- `youtube_uploader.py` - YouTube upload client
- `openai_client.py` - OpenAI/Sora API wrapper

## Examples

### Example 1: Quick Test (No Upload)

```bash
python scripts/audiobook_pipeline_complete.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/test_book
```

### Example 2: Full Pipeline with Upload

```bash
python scripts/audiobook_pipeline_complete.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/audiobook_pipeline/shooting_an_elephant \
  --upload --upload-privacy public
```

### Example 3: Long Book with Chapter Inference

```bash
python scripts/audiobook_pipeline_complete.py \
  "https://gutenberg.net.au/ebooks02/0200991.txt" \
  --output-dir experiments/audiobook_pipeline/notes_from_underground \
  --infer-chapter \
  --upload --upload-privacy public
```

### Example 4: Resume from Backgrounds

```bash
python scripts/audiobook_pipeline_complete.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/audiobook_pipeline/shooting_an_elephant \
  --skip-episode-audio \
  --skip-promo-audio \
  --upload
```

## Key Features Summary

### New in This Version

1. ✅ **Film Noir Style Guide** - Consistent visual style for all promotional videos
2. ✅ **Structured Scene Descriptions** - STYLE, SETTING, SUBJECT, CAMERA, LIGHTING, ACTION
3. ✅ **JSON Response Format** - Guaranteed valid JSON from GPT-4o-mini
4. ✅ **DALL-E Background Generation** - Van Gogh impressionist style backgrounds
5. ✅ **Episode Video Composition** - Opening + background + audio
6. ✅ **10-Second Ending** - Logo + '@the-wormhole-podcast' on promotional shorts
7. ✅ **YouTube Upload Integration** - Auto-metadata, shorts detection, upload tracking
8. ✅ **Master Pipeline Script** - One command from TXT to YouTube
9. ✅ **Mac Mini Transfer Ready** - Organized structure for scheduled uploads

### Pipeline Benefits

- **Fully Automated:** TXT → YouTube with one command
- **Professional Quality:** Opening logos, styled videos, proper metadata
- **YouTube Optimized:** Vertical shorts, proper tags, education category
- **Cost Effective:** Reuses audio, skips completed stages, batch processing
- **Scalable:** Works for 5-chapter or 31-chapter books
- **Consistent Style:** Hardcoded style guides ensure visual coherence

## Next Steps

After pipeline completion:

1. **Review Outputs:** Check episode videos and shorts for quality
2. **YouTube Studio:** Add custom thumbnails, end screens, playlists
3. **Scheduling:** Plan upload schedule to stay within YouTube quota
4. **Promotion:** Share shorts on TikTok, Instagram Reels
5. **Analytics:** Track views, engagement, audience retention
6. **Iteration:** Adjust style guide based on performance

---

**Documentation:** `docs/COMPLETE_AUDIOBOOK_PIPELINE.md`
**Original Pipeline:** `docs/AUDIOBOOK_PIPELINE.md`
**YouTube Setup:** `YOUTUBE_API_SETUP_GUIDE.md`
**Quick Reference:** `YOUTUBE_QUICK_REFERENCE.md`
