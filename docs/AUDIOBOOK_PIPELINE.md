# Audiobook + Promotional Video Pipeline

Complete pipeline for converting Gutenberg books into audiobooks with promotional short videos.

## Pipeline Overview

```
Text Book (TXT/URL)
    ↓
Step 1: Generate Audiobook JSON (with promotional shorts)
    ↓
Step 2: Generate Promotional Audio (TTS)
    ↓
Step 3: Generate Promotional Videos (Sora + vertical format)
    ↓
Final Output: Audiobook JSON + Audio files + Promotional videos
```

## Step-by-Step Process

### Step 1: Convert Book to Audiobook with Promotional Shorts

**Command:**
```bash
python scripts/book_to_audiobook.py <gutenberg_url> --output-dir experiments/audiobook_pipeline/<book_name>
```

**With chapter inference** (for books without explicit chapters):
```bash
python scripts/book_to_audiobook.py <gutenberg_url> --output-dir experiments/audiobook_pipeline/<book_name> --infer-chapter
```

**What it does:**
- Downloads book from Gutenberg
- Detects or infers chapters (~2000 words each using semantic analysis)
- Creates Story Bible (summary of characters, plot, themes)
- Generates narrated version of each chapter with emotion tags
- **Generates 2-3 promotional shorts per chapter** (4-5 scenes each, ~30 seconds)
- Promotional shorts have:
  - Marketing-focused names ("EPIC SHOWDOWN", "HEART-STOPPING REVEAL")
  - Bold, creative scene descriptions for Sora video generation
  - Emotion-tagged narrated text excerpts
- Groups chapters into episodes
- Saves everything to JSON

**Output:**
```
experiments/audiobook_pipeline/<book_name>/
├── audiobook.json              # Main output with promotional shorts
├── book_raw.txt               # Original downloaded text
└── original_chapters/         # Individual chapter files
    ├── chapter_01_*.txt
    ├── chapter_02_*.txt
    └── ...
```

**Key JSON Structure:**
```json
{
  "metadata": {...},
  "story_bible": "...",
  "chapters": [
    {
      "chapter_number": 1,
      "title": "Chapter Title",
      "narrated_text": "Narrated version with [emotion] tags",
      "promotional_shorts": [
        {
          "short_id": 1,
          "name": "EPIC DISCOVERY",
          "target_duration": 30,
          "scenes": [
            {
              "scene_id": 1,
              "promotional_narrated_text": "[dramatic] Excerpt with emotion tag",
              "scene_description": "BOLD VISUAL: Creative description for Sora"
            }
          ]
        }
      ]
    }
  ],
  "episodes": [...],
  "stats": {...}
}
```

### Step 2: Generate Promotional Audio (TTS)

**Command:**
```bash
python scripts/generate_promotional_audio.py experiments/audiobook_pipeline/<book_name>/audiobook.json
```

**What it does:**
- Reads audiobook.json with promotional shorts
- For each scene in each short:
  - Generates ElevenLabs TTS audio
  - Measures actual audio duration with ffprobe
  - Picks appropriate Sora video duration (4, 8, or 12 seconds)
  - Calculates silence padding needed
- Updates JSON with timing metadata
- Saves organized audio files

**Output:**
```
experiments/audiobook_pipeline/<book_name>/
├── promo_audio/
│   ├── chapter_01/
│   │   ├── short_01/
│   │   │   ├── scene_01.mp3
│   │   │   ├── scene_02.mp3
│   │   │   └── ...
│   │   ├── short_02/
│   │   └── ...
│   └── ...
└── audiobook_with_timing.json  # Updated with timing data
```

**Timing Data Added to JSON:**
```json
{
  "scene_id": 1,
  "promotional_narrated_text": "[serious] Audio text",
  "scene_description": "Visual description",
  "audio_duration": 2.69,        // Measured TTS duration
  "sora_duration": 4,             // Selected Sora duration
  "silence_padding": 1.31,        // Padding to add
  "audio_file": "scene_01.mp3"    // Generated audio file
}
```

### Step 3: Generate Promotional Videos (Sora + Vertical Format)

**Command:**
```bash
python scripts/generate_promotional_videos.py experiments/audiobook_pipeline/<book_name>/audiobook_with_timing.json
```

**What it does:**
- Reads audiobook_with_timing.json
- For each scene:
  - Generates Sora video using scene_description
  - **Converts to VERTICAL format (1080x1920)** for TikTok/Instagram
  - Pads audio with silence to match video duration
  - Combines audio + video
- Concatenates all scenes in a short into final promotional video

**Output:**
```
experiments/audiobook_pipeline/<book_name>/
└── promo_videos/
    ├── chapter_01/
    │   ├── short_01/
    │   │   ├── scene_01_raw.mp4          # Original Sora video
    │   │   ├── scene_01_vertical.mp4     # Converted to 1080x1920
    │   │   ├── scene_01_audio_padded.mp3 # Audio with silence padding
    │   │   └── scene_01_final.mp4        # Audio + video combined
    │   ├── EPIC_DISCOVERY_SHORT.mp4      # Final concatenated short
    │   └── ...
    └── ...
```

## File Organization

### Example Complete Structure

```
experiments/audiobook_pipeline/shooting_an_elephant/
├── audiobook.json                    # Original JSON with shorts
├── audiobook_with_timing.json        # JSON with audio timing data
├── book_raw.txt                      # Downloaded source text
│
├── original_chapters/                # Original chapter text files
│   ├── chapter_01_Introduction_to_Moulmein.txt
│   ├── chapter_02_The_Incident_with_the_Elephant.txt
│   └── ...
│
├── promo_audio/                      # Generated TTS audio
│   ├── chapter_01/
│   │   ├── short_01/
│   │   │   ├── scene_01.mp3
│   │   │   ├── scene_02.mp3
│   │   │   ├── scene_03.mp3
│   │   │   └── scene_04.mp3
│   │   └── short_02/
│   │       ├── scene_01.mp3
│   │       └── ...
│   └── ...
│
└── promo_videos/                     # Generated Sora videos (vertical)
    ├── chapter_01/
    │   ├── short_01/
    │   │   ├── scene_01_raw.mp4
    │   │   ├── scene_01_vertical.mp4
    │   │   ├── scene_01_audio_padded.mp3
    │   │   ├── scene_01_final.mp4
    │   │   └── ...
    │   ├── TENSION_IN_THE_AIR_SHORT.mp4    # Final short video
    │   └── CONFLICT_WITHIN_SHORT.mp4
    └── ...
```

## Quick Start Examples

### Example 1: Short Book (No Chapter Inference)

```bash
# Step 1: Generate audiobook JSON
python scripts/book_to_audiobook.py \
  "https://gutenberg.net.au/ebooks02/0200141.txt" \
  --output-dir experiments/audiobook_pipeline/shooting_an_elephant

# Step 2: Generate promotional audio
python scripts/generate_promotional_audio.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook.json

# Step 3: Generate promotional videos (requires Sora API)
python scripts/generate_promotional_videos.py \
  experiments/audiobook_pipeline/shooting_an_elephant/audiobook_with_timing.json
```

### Example 2: Long Book (With Chapter Inference)

```bash
# Step 1: Generate audiobook JSON with semantic chapter detection
python scripts/book_to_audiobook.py \
  "https://gutenberg.net.au/ebooks02/0200991.txt" \
  --output-dir experiments/audiobook_pipeline/notes_from_underground \
  --infer-chapter

# Step 2: Generate promotional audio
python scripts/generate_promotional_audio.py \
  experiments/audiobook_pipeline/notes_from_underground/audiobook.json

# Step 3: Generate promotional videos (requires Sora API)
python scripts/generate_promotional_videos.py \
  experiments/audiobook_pipeline/notes_from_underground/audiobook_with_timing.json
```

## Configuration

### ElevenLabs Voice

Default voice ID: `ePiPWpzcHZrcqRzFrgQg`

To use a different voice:
```bash
python scripts/generate_promotional_audio.py <json_file> --voice-id <your_voice_id>
```

### Sora Video Durations

Available durations: **4, 8, or 12 seconds**

The system automatically picks the smallest duration that fits the audio:
- Audio 2.5s → Use 4s Sora video → Pad with 1.5s silence
- Audio 6.2s → Use 8s Sora video → Pad with 1.8s silence
- Audio 11.5s → Use 12s Sora video → Pad with 0.5s silence

### Video Format

All promotional videos are converted to **VERTICAL FORMAT (1080x1920)** for:
- TikTok
- Instagram Reels
- YouTube Shorts

## Requirements

- Python 3.8+
- ElevenLabs API key (set in `.env.secrets` as `ELEVEN_LABS_KEY`)
- OpenAI API key (set in `.env.secrets` as `OPEN_AI_API`)
- ffmpeg (for audio/video processing)
- ffprobe (for duration measurement)

## Features

### Semantic Chapter Detection

When using `--infer-chapter`, the system:
1. Uses GPT-4o-mini to analyze text for natural chapter breaks
2. Looks for scene changes, time shifts, location changes
3. Targets ~2000 words per chapter
4. Falls back to simple word-count division if needed

### Promotional Shorts

Each chapter gets 2-3 promotional shorts:
- **Marketing-focused**: Designed to attract listeners
- **Dramatic moments**: Most exciting/emotional scenes
- **Bold visuals**: Creative scene descriptions for video generation
- **Emotion tags**: `[dramatic]`, `[excited]`, `[mysterious]`, etc.

### Audio-Video Sync

1. **Audio-first approach**: Generate TTS to know exact duration
2. **Smart duration selection**: Pick Sora duration >= audio duration
3. **Silence padding**: Add silence to audio to match video length
4. **No trimming**: Videos are never cut short

## Troubleshooting

### API Keys Not Found

Make sure `.env.secrets` contains:
```
ELEVEN_LABS_KEY=your_elevenlabs_key
OPEN_AI_API=your_openai_key
```

### ffmpeg/ffprobe Not Found

Install ffmpeg:
```bash
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
```

### Chapter Detection Failed

Try with `--infer-chapter` flag for semantic analysis:
```bash
python scripts/book_to_audiobook.py <url> --output-dir <dir> --infer-chapter
```

## Notes

- Promotional videos require Sora API access
- Audio generation uses ElevenLabs with emotion tag support (eleven_v3 model)
- Vertical video conversion uses ffmpeg with padding to maintain aspect ratio
- All timing calculations are automatic based on actual TTS duration
