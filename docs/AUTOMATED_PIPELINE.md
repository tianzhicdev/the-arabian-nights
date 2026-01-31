# Fully Automated Audiobook Pipeline

## Overview

Single command to convert TXT file → Complete audiobook ready for YouTube upload on Mac Mini.

## Command

```bash
python scripts/audiobook_pipeline_auto.py <txt_file_or_url> <voice_id>
```

### Examples

```bash
# From URL
python scripts/audiobook_pipeline_auto.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  ePiPWpzcHZrcqRzFrgQg

# From local file
python scripts/audiobook_pipeline_auto.py \
  "my_book.txt" \
  ePiPWpzcHZrcqRzFrgQg

# Skip Mac Mini transfer (testing)
python scripts/audiobook_pipeline_auto.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  ePiPWpzcHZrcqRzFrgQg \
  --no-transfer
```

## Pipeline Flow

```
📥 INPUT: TXT File/URL + Voice ID
   |
   ├─→ Calculate SHA-256 Hash (7 digits)
   |     e.g., "717d51e"
   |
   ├─→ Create Output Directory
   |     experiments/audiobook_pipeline/{hash}/
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 1: Generate Audiobook JSON (with Promo Shorts)    │
│  ────────────────────────────────────────────────────    │
│  Input:  TXT file or URL                                 │
│  Output: audiobook_{hash}.json                           │
│  Tool:   book_to_audiobook.py                           │
│  ────────────────────────────────────────────────────    │
│  ✓ Download/read text                                    │
│  ✓ Detect or infer chapters                              │
│  ✓ Generate story bible (GPT-4o-mini)                    │
│  ✓ Simplify narration with emotion tags                  │
│  ✓ Generate 2-3 promotional shorts per chapter           │
│      → Film Noir style (hardcoded)                       │
│      → Structured scene descriptions                     │
│      → JSON format enforced                              │
│  ✓ Group chapters into episodes                          │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 2: Generate Episode Audio (TTS)                   │
│  ────────────────────────────────────────────────────    │
│  Input:  audiobook_{hash}.json                           │
│  Output: audio/{hash}_episode_01.mp3                     │
│  Tool:   generate_audiobook_audio.py                    │
│  API:    ElevenLabs TTS                                  │
│  ────────────────────────────────────────────────────    │
│  ✓ Convert narrated text to speech                       │
│  ✓ Process emotion tags                                  │
│  ✓ Split large texts into chunks                         │
│  ✓ Concatenate chunks into final MP3                     │
│  ✓ Skip if file already exists ✓                         │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 3: Generate Promotional Audio (TTS)               │
│  ────────────────────────────────────────────────────    │
│  Input:  audiobook_{hash}.json                           │
│  Output: promo_audio/chapter_*/short_*/scene_*.mp3       │
│          audiobook_{hash}_timing.json                    │
│  Tool:   generate_promotional_audio.py                  │
│  API:    ElevenLabs TTS                                  │
│  ────────────────────────────────────────────────────    │
│  ✓ Generate TTS for each promotional short scene         │
│  ✓ Capture timing metadata (duration)                    │
│  ✓ Save timing to audiobook_with_timing.json             │
│  ✓ Skip if files already exist ✓                         │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 4: Generate Background Images (DALL-E)            │
│  ────────────────────────────────────────────────────    │
│  Input:  audiobook_{hash}.json                           │
│  Output: episode_backgrounds/episode_01_background.png   │
│  Tool:   generate_episode_backgrounds.py                │
│  API:    DALL-E 3                                        │
│  ────────────────────────────────────────────────────    │
│  ✓ Generate abstract Van Gogh impressionist backgrounds  │
│  ✓ One image per episode (1792x1024)                     │
│  ✓ Atmospheric, artistic style                           │
│  ✓ Skip if file already exists ✓                         │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 5: Create Episode Videos (Composition)            │
│  ────────────────────────────────────────────────────    │
│  Input:  audiobook_{hash}.json                           │
│          audio/{hash}_episode_01.mp3                     │
│          episode_backgrounds/episode_01_background.png   │
│  Output: episode_videos/episode_01_final.mp4             │
│  Tool:   create_episode_videos.py                       │
│  Tech:   FFmpeg                                          │
│  ────────────────────────────────────────────────────    │
│  ✓ Generate opening audio (TTS):                         │
│      "Book Title by Author. Episode One."                │
│  ✓ Create opening video:                                 │
│      → Logo (resources/wornhole-logo.png)                │
│      → Black background (1280x720)                       │
│      → Logo centered + opening audio                     │
│  ✓ Create main video:                                    │
│      → Background image looped                           │
│      → Episode audio synced                              │
│  ✓ Concatenate opening + main video                      │
│  ✓ Skip if file already exists ✓                         │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 6: Generate Promotional Videos (Sora) [NON-CRITICAL]│
│  ────────────────────────────────────────────────────    │
│  Input:  audiobook_{hash}_timing.json                    │
│          promo_audio/chapter_*/short_*/scene_*.mp3       │
│  Output: promo_videos/chapter_*/SCENE_NAME_SHORT.mp4     │
│  Tool:   generate_promotional_videos.py                 │
│  API:    Sora 2 (OpenAI)                                 │
│  ────────────────────────────────────────────────────    │
│  ✓ Generate video for each scene (Sora 2)                │
│      → Film Noir style                                   │
│      → Structured prompts                                │
│      → 4-second duration                                 │
│  ✓ Convert to vertical format (1080x1920)                │
│  ✓ Sync audio with video:                                │
│      → Pad audio with silence if needed                  │
│  ✓ Create 10-second ending segment:                      │
│      → Black background                                  │
│      → Logo centered                                     │
│      → '@the-wormhole-podcast' text                      │
│  ✓ Concatenate scenes + ending                           │
│  ⚠️  Some shorts may fail (acceptable)                    │
│  ✓ Skip if file already exists ✓                         │
└──────────────────────────────────────────────────────────┘
   |
   v
┌──────────────────────────────────────────────────────────┐
│  STEP 7: Transfer to Mac Mini (Upload Queue)            │
│  ────────────────────────────────────────────────────    │
│  Input:  experiments/audiobook_pipeline/{hash}/          │
│  Output: macmini:/Users/user/youtube_upload_queue/{hash} │
│  Tech:   SSH + SCP                                       │
│  ────────────────────────────────────────────────────    │
│  ✓ Check Mac Mini accessibility                          │
│  ✓ Create remote directory                               │
│  ✓ Transfer all files recursively                        │
│  ⚠️  If Mac Mini unavailable: show manual command         │
│                                                          │
│  Mac Mini will upload on schedule using:                 │
│  → scripts/upload_audiobook_to_youtube.py                │
└──────────────────────────────────────────────────────────┘
   |
   v
📤 OUTPUT: Files ready on Mac Mini for scheduled YouTube upload
```

## Hash-Based File Naming

All intermediate files include the book hash (first 7 characters of SHA-256):

```
experiments/audiobook_pipeline/717d51e/
├── book_717d51e.txt                              # Raw text
├── audiobook_717d51e.json                        # Main JSON
├── audiobook_717d51e_timing.json                 # With timing
├── audio/
│   └── 717d51e_episode_01.mp3                    # Episode audio
├── promo_audio/
│   └── chapter_01/short_01/scene_01.mp3          # Promo audio
├── episode_backgrounds/
│   └── episode_01_background.png                 # Background image
├── episode_videos/
│   └── episode_01_final.mp4                      # ✅ FINAL VIDEO
└── promo_videos/
    └── chapter_01/SCENE_NAME_SHORT.mp4           # ✅ FINAL SHORT
```

## Resume Capability

The pipeline is **fully resumable**:

- Before creating any expensive file, checks if it exists
- If exists: **Skip** (show "✓ Output already exists, skipping")
- If error occurs: **Restart** command without remaking existing files

Example:
```bash
# Run 1: Completes steps 1-4, fails on step 5
python scripts/audiobook_pipeline_auto.py <url> <voice>

# Run 2: Skips steps 1-4 (already done), continues from step 5
python scripts/audiobook_pipeline_auto.py <url> <voice>
```

## Mac Mini Configuration

Set environment variables (optional):

```bash
export MAC_MINI_HOST="macmini.local"
export MAC_MINI_USER="user"
export MAC_MINI_UPLOAD_DIR="/Users/user/youtube_upload_queue"
```

Defaults:
- Host: `macmini.local`
- User: `user`
- Upload dir: `/Users/user/youtube_upload_queue`

## API Requirements

**Required API Keys** (in `.env.secrets`):
- `ELEVEN_LABS_KEY` - ElevenLabs TTS
- `OPEN_AI_API` - OpenAI (GPT-4o-mini, DALL-E 3, Sora 2)

**Cost Estimate** (5-chapter book):
- ElevenLabs: ~20,000 characters (~$2.40)
- GPT-4o-mini: ~$0.50
- DALL-E 3: ~$0.20 (1 image)
- Sora 2: ~$50-100 (10-15 shorts, 40-60 scenes)
- **Total:** ~$53-103

## Key Features

### ✅ Fully Automated
- **2 parameters only:** `<txt_file_or_url>` `<voice_id>`
- No manual intervention required
- Runs all 7 pipeline steps automatically

### ✅ Hash-Based Identification
- SHA-256 hash (7 digits) calculated from text content
- All files named with hash prefix
- Same book → same hash → same directory

### ✅ Skip-If-Exists Logic
- Every expensive operation checks file existence
- Avoids re-generating existing files
- Saves API costs and time

### ✅ Resumable
- Pipeline can restart from failure point
- No duplicate work
- Idempotent execution

### ✅ Mac Mini Ready
- Automatic transfer via SSH/SCP
- Organized directory structure
- Ready for scheduled YouTube upload

### ✅ Style Consistency
- Film Noir style hardcoded for all videos
- Structured scene descriptions
- JSON format enforced

### ✅ Non-Critical Promo Videos
- Main audiobook is priority
- Promotional shorts are optional
- Pipeline continues even if some shorts fail

## Troubleshooting

### Issue: "Mac Mini not accessible"
**Solution:** Files remain in local directory. Manual transfer command shown.

### Issue: Some promotional videos fail
**Expected:** Sora API may fail 20-30% of the time. Audiobook still completes.

### Issue: JSON generation error with promotional shorts
**Fixed:** Prompt now includes "JSON" keyword for OpenAI's response_format.

### Issue: File naming mismatch
**Fixed:** All files now consistently use `{hash}` in filenames.

## Next Steps After Pipeline

1. **Mac Mini scheduled upload** will pick up files automatically
2. **YouTube Studio** - Add thumbnails, end screens, playlists
3. **Social media** - Share promotional shorts on TikTok, Instagram
4. **Analytics** - Track views, engagement, retention

---

**Script:** `scripts/audiobook_pipeline_auto.py`
**Documentation:** `docs/AUTOMATED_PIPELINE.md`
**Full pipeline details:** `docs/COMPLETE_AUDIOBOOK_PIPELINE.md`
