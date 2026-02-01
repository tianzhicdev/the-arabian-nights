# Audiobook Pipeline Auto - Step Diagram

## Overview

```
SOURCE (txt/url) + VOICE_ID
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUDIOBOOK PIPELINE AUTO                              │
│                   src/pipelines/audiobook_pipeline_auto.py                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
    output/audiobook_pipeline/{book_hash}/
```

---

## Step 0: Initialize

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 0: Download Text & Calculate Hash                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Function: download_text() + calculate_hash()                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • source (str): Text file path OR URL (e.g., gutenberg URL)             │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • text_content (str): Raw book text                                     │
│    • source_name (str): Filename or URL identifier                         │
│    • book_hash (str): SHA256 hash of content (first 7 chars)               │
│    • output_dir: output/audiobook_pipeline/{book_hash}/                    │
│    • book_{hash}.txt: Saved raw text file                                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 1: Generate Audiobook JSON

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1/7: Generate Audiobook JSON                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/tools/book_to_audiobook.py                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • source (str): Original text file path or URL                          │
│    • --output-dir: output/audiobook_pipeline/{hash}/                       │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • audiobook_{hash}.json                                                 │
│      Contains:                                                              │
│        - book_title                                                         │
│        - episodes[] with:                                                   │
│          - episode_number                                                   │
│          - title                                                            │
│          - chapters[]                                                       │
│          - text content                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 2: Generate Episode Audio

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2/7: Generate Episode Audio                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/generators/generate_audiobook_audio.py                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • audiobook_{hash}.json                                                 │
│    • --voice-id: ElevenLabs voice ID (e.g., ePiPWpzcHZrcqRzFrgQg)          │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • audio/{hash}_episode_01.mp3                                           │
│    • audio/{hash}_episode_02.mp3                                           │
│    • ... (one per episode)                                                  │
│                                                                             │
│  EXTERNAL API:                                                              │
│    • ElevenLabs TTS API                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 3: Generate Promotional Audio

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3/7: Generate Promotional Audio                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/generators/generate_promotional_audio.py                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • audiobook_{hash}.json                                                 │
│    • --voice-id: ElevenLabs voice ID                                       │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • promo_audio/*.mp3 (short promotional clips)                           │
│    • audiobook_{hash}_timing.json                                          │
│      Contains:                                                              │
│        - Original audiobook data                                            │
│        - Audio timing/duration metadata                                     │
│                                                                             │
│  EXTERNAL API:                                                              │
│    • ElevenLabs TTS API                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 4: Generate Background Images

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4/7: Generate Background Images                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/generators/generate_episode_backgrounds.py                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • audiobook_{hash}.json                                                 │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • episode_backgrounds/episode_01_background.png                         │
│    • episode_backgrounds/episode_02_background.png                         │
│    • ... (one per episode)                                                  │
│                                                                             │
│  EXTERNAL API:                                                              │
│    • Image generation API (e.g., DALL-E, Flux, etc.)                       │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 5: Create Episode Videos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5/7: Create Episode Videos                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/tools/create_episode_videos.py                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • audiobook_{hash}.json                                                 │
│    • --voice-id: ElevenLabs voice ID                                       │
│    • audio/{hash}_episode_*.mp3 (from Step 2)                              │
│    • episode_backgrounds/*.png (from Step 4)                               │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • episode_videos/episode_01_final.mp4                                   │
│    • episode_videos/episode_02_final.mp4                                   │
│    • ... (one per episode)                                                  │
│                                                                             │
│  SIDE EFFECT:                                                               │
│    • Queues videos to ~/upload_queue_main/{hash}_ep{N}/                    │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 6: Generate Promotional Videos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6/7: Generate Promotional Videos (Non-Critical)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Script: src/generators/generate_promotional_videos.py                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • audiobook_{hash}_timing.json (from Step 3)                            │
│    • promo_audio/*.mp3 (from Step 3)                                       │
│    • episode_backgrounds/*.png (from Step 4)                               │
│                                                                             │
│  OUTPUTS:                                                                   │
│    • promo_videos/**/*_SHORT.mp4                                           │
│    • Multiple short promotional clips for social media                     │
│                                                                             │
│  NOTE: Pipeline continues even if this step fails                          │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
```

---

## Step 7: Queue for YouTube Upload

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7/7: Verify YouTube Queue                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Function: queue_for_upload() / verification                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                    │
│    • episode_videos/episode_*_final.mp4                                    │
│    • audiobook_{hash}.json                                                 │
│                                                                             │
│  OUTPUTS (in ~/upload_queue_main/{hash}_ep{N}/):                           │
│    • episode_*_final.mp4 (copied)                                          │
│    • metadata.json containing:                                              │
│        - episode_number                                                     │
│        - video_filename                                                     │
│        - title                                                              │
│        - description                                                        │
│        - tags[]                                                             │
│        - category_id: "27" (Education)                                     │
│        - privacy_status                                                     │
│        - uploaded: false                                                    │
│        - creation_timestamp                                                 │
│        - book_hash                                                          │
│        - source_file                                                        │
│                                                                             │
│  NEXT:                                                                      │
│    • Cron runs scripts/upload_next_episode.sh                              │
│    • Uses src/upload/upload_audiobook_to_youtube.py                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete File Structure

```
output/audiobook_pipeline/{book_hash}/
├── book_{hash}.txt                    # Raw source text
├── audiobook_{hash}.json              # Episode structure & content
├── audiobook_{hash}_timing.json       # With audio timing data
├── audio/
│   ├── {hash}_episode_01.mp3
│   ├── {hash}_episode_02.mp3
│   └── ...
├── promo_audio/
│   └── *.mp3                          # Short promotional clips
├── episode_backgrounds/
│   ├── episode_01_background.png
│   ├── episode_02_background.png
│   └── ...
├── episode_videos/
│   ├── episode_01_final.mp4           # Full episode videos
│   ├── episode_02_final.mp4
│   └── ...
└── promo_videos/
    └── **/*_SHORT.mp4                 # Promotional short videos

~/upload_queue_main/
├── {hash}_ep01/
│   ├── episode_01_final.mp4
│   └── metadata.json
├── {hash}_ep02/
│   ├── episode_02_final.mp4
│   └── metadata.json
└── ...
```

---

## CLI Arguments

```
python src/pipelines/audiobook_pipeline_auto.py <source> <voice_id> [options]

Required:
  source          Text file path or URL
  voice_id        ElevenLabs voice ID

Options:
  --skip-queue    Skip queueing for YouTube upload
  --base-dir      Base output directory (default: output/audiobook_pipeline)
```

---

## Flow Diagram (ASCII)

```
                    ┌──────────────────┐
                    │  SOURCE (txt/url)│
                    │  + VOICE_ID      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Step 0: Download │
                    │ & Hash Content   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Step 1: Book to  │
                    │ Audiobook JSON   │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     ┌──────────────────┐          ┌──────────────────┐
     │ Step 2: Generate │          │ Step 3: Generate │
     │ Episode Audio    │          │ Promo Audio      │
     └────────┬─────────┘          └────────┬─────────┘
              │                             │
              │      ┌──────────────────┐   │
              │      │ Step 4: Generate │   │
              │      │ Background Images│   │
              │      └────────┬─────────┘   │
              │               │             │
              └───────┬───────┘             │
                      ▼                     │
             ┌──────────────────┐           │
             │ Step 5: Create   │           │
             │ Episode Videos   │           │
             └────────┬─────────┘           │
                      │                     │
                      │      ┌──────────────┘
                      │      ▼
                      │ ┌──────────────────┐
                      │ │ Step 6: Generate │
                      │ │ Promo Videos     │
                      │ └────────┬─────────┘
                      │          │
                      └────┬─────┘
                           ▼
                  ┌──────────────────┐
                  │ Step 7: Queue    │
                  │ for YouTube      │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   CRON JOB       │
                  │ upload_next_     │
                  │ episode.sh       │
                  └──────────────────┘
```
