# Explainer Video Pipeline - Architecture Diagram

```
                          EXPLAINER VIDEO PIPELINE
                          ========================

    CLI ARGS: --category, --minutes, --auto-approve, --voice-id, --art-style
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: DISCOVER NEWS                                                       │
│  ─────────────────────                                                       │
│  INPUT:  category (str, optional: "geopolitics", "tech", "economics")       │
│          count (int, default: 8)                                            │
│                                                                              │
│  TOOL:   xAI Grok API with search=True                                      │
│                                                                              │
│  OUTPUT: List[Dict] - 8 trending news topics                                │
│          [{title, summary, source_url, potential_angles, timeliness}, ...]  │
│                                                                              │
│  SAVED:  output/explainer/{hash}/01_news_topics.json                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: SELECT TOPIC                                                        │
│  ────────────────────                                                        │
│  INPUT:  topics (List[Dict] from Step 1)                                    │
│                                                                              │
│  TOOL:   OpenRouter LLM (Claude/GPT)                                        │
│          Prompt: Evaluate news hook + educational potential                 │
│                                                                              │
│  OUTPUT: Dict - selection with reasoning                                    │
│          {selected_topic, news_hook, educational_angle, reasoning}          │
│                                                                              │
│  SAVED:  output/explainer/{hash}/02_selected_topic.json                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                         ┌──────────┴──────────┐
                         │ APPROVAL CHECKPOINT │
                         │  (if not auto)      │
                         └──────────┬──────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: RESEARCH TOPIC                                                      │
│  ──────────────────────                                                      │
│  INPUT:  topic_title (str)                                                  │
│          educational_angle (str)                                            │
│                                                                              │
│  TOOL:   xAI Grok API with search=True                                      │
│          Prompt: Deep research with history, context, implications          │
│                                                                              │
│  OUTPUT: str - Comprehensive markdown research notes (~10-15K chars)        │
│          Includes: history, key players, data, different perspectives       │
│                                                                              │
│  SAVED:  output/explainer/{hash}/03_research_notes.md                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: GENERATE SCRIPT                                                     │
│  ───────────────────────                                                     │
│  INPUT:  research_notes (str from Step 3)                                   │
│          topic_title (str)                                                  │
│          educational_angle (str)                                            │
│          news_hook (str - recent event to open with)                        │
│          target_minutes (int, default: 8)                                   │
│          art_style (str: "editorial", "flat_vector", "watercolor")          │
│                                                                              │
│  TOOL:   OpenRouter LLM                                                     │
│          Prompt: Generate news-driven educational script                    │
│          Retry logic: Enforces minimum scene count (16-24 for 8 min)        │
│                                                                              │
│  OUTPUT: Dict - Complete video script                                       │
│          {                                                                  │
│            title: str,                                                      │
│            description: str (YouTube description),                          │
│            tags: List[str],                                                 │
│            scenes: [                                                        │
│              {                                                              │
│                scene_number: int,                                           │
│                narration: str (50-75 words, ~20-30 seconds),                │
│                scene_image_description: str (artistic, NOT technical),      │
│                duration_estimate: int (seconds)                             │
│              }, ...                                                         │
│            ]                                                                │
│          }                                                                  │
│                                                                              │
│  STRUCTURE: Scenes 1-2:  News event (what just happened)                    │
│             Scenes 3-5:  Historical context                                 │
│             Scenes 6-12: Deep educational content                           │
│             Scenes 13-16: Implications & perspectives                       │
│             Scenes 17-20: Future outlook                                    │
│                                                                              │
│  SAVED:  output/explainer/{hash}/04_script.json                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: GENERATE AUDIO                                                      │
│  ──────────────────────                                                      │
│  INPUT:  scenes (List[Dict] from Step 4)                                    │
│          voice_id (str, optional - defaults to ELEVENLABS_VOICE_ID env)     │
│                                                                              │
│  TOOL:   ElevenLabs API (model: eleven_turbo_v2_5)                          │
│          Wrapper: ElevenLabsExplainerAudio → ElevenLabsSceneGenerator       │
│                                                                              │
│  OUTPUT: Dict[int, float] - {scene_number: duration_seconds}                │
│          Files: scene_01.mp3, scene_02.mp3, ... scene_20.mp3                │
│                                                                              │
│  SAVED:  output/explainer/{hash}/audio/*.mp3                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: GENERATE IMAGES                                                     │
│  ───────────────────────                                                     │
│  INPUT:  scenes (List[Dict] from Step 4)                                    │
│          scene_image_description for each scene                             │
│                                                                              │
│  TOOL:   DALL-E 3 API via OpenAI                                            │
│          Size: 1792x1024 (16:9 aspect ratio)                                │
│          Quality: standard                                                  │
│                                                                              │
│  PROMPT PREFIX:                                                             │
│    "Artistic editorial illustration style, evocative and cinematic,        │
│     NOT a technical diagram, NOT scientific illustration...                 │
│     Scene: [scene_image_description]"                                       │
│                                                                              │
│  OUTPUT: Dict[int, Path] - {scene_number: image_path}                       │
│          Files: scene_01.png, scene_02.png, ... scene_20.png                │
│                                                                              │
│  SAVED:  output/explainer/{hash}/images/*.png                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: ASSEMBLE VIDEOS                                                     │
│  ───────────────────────                                                     │
│  INPUT:  audio_durations (Dict from Step 5)                                 │
│          images (Dict from Step 6)                                          │
│                                                                              │
│  TOOL:   FFmpeg via VideoAssembler                                          │
│                                                                              │
│  PROCESS:                                                                   │
│    1. For each scene:                                                       │
│       ffmpeg -loop 1 -i scene_XX.png -i scene_XX.mp3                        │
│              -c:v libx264 -tune stillimage -c:a aac                         │
│              -shortest scene_XX.mp4                                         │
│                                                                              │
│    2. Concatenate all scenes:                                               │
│       ffmpeg -f concat -i scenes.txt -c copy final_video.mp4                │
│                                                                              │
│  OUTPUT: Path - final_video.mp4                                             │
│          Intermediate: scene_01.mp4, scene_02.mp4, ... scene_20.mp4         │
│                                                                              │
│  SAVED:  output/explainer/{hash}/scenes/*.mp4                               │
│          output/explainer/{hash}/final_video.mp4                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    |
                                    v
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: QUEUE FOR UPLOAD                                                    │
│  ────────────────────────                                                    │
│  INPUT:  final_video.mp4                                                    │
│          script (Dict with title, description, tags)                        │
│          topic_hash (str)                                                   │
│                                                                              │
│  PROCESS:                                                                   │
│    1. Copy video to ~/upload_queue_main/explainer_{hash}/                   │
│    2. Create metadata.json with YouTube upload info                         │
│                                                                              │
│  OUTPUT: metadata.json                                                      │
│          {                                                                  │
│            title: str,                                                      │
│            description: str,                                                │
│            tags: List[str],                                                 │
│            category_id: "27" (Education),                                   │
│            privacy_status: "private",                                       │
│            uploaded: false,                                                 │
│            creation_timestamp: float,                                       │
│            video_filename: str                                              │
│          }                                                                  │
│                                                                              │
│  SAVED:  ~/upload_queue_main/explainer_{hash}/metadata.json                 │
│          ~/upload_queue_main/explainer_{hash}/final_video.mp4               │
│                                                                              │
│  NEXT:   Run scripts/upload_next_episode.sh (cron job)                      │
│          - Uploads to YouTube as private                                    │
│          - Sets publishAt to schedule public release                        │
└─────────────────────────────────────────────────────────────────────────────┘


## File Structure

```
output/explainer/{topic_hash}/
├── 01_news_topics.json      # Step 1 output
├── 02_selected_topic.json   # Step 2 output
├── 03_research_notes.md     # Step 3 output
├── 04_script.json           # Step 4 output
├── audio/                   # Step 5 output
│   ├── scene_01.mp3
│   ├── scene_02.mp3
│   └── ...
├── images/                  # Step 6 output
│   ├── scene_01.png
│   ├── scene_02.png
│   └── ...
├── scenes/                  # Step 7 intermediate
│   ├── scene_01.mp4
│   ├── scene_02.mp4
│   └── ...
└── final_video.mp4          # Step 7 final output
```

## API Dependencies

| Step | Service | Environment Variable |
|------|---------|---------------------|
| 1, 3 | xAI Grok | XAI_API_KEY |
| 2, 4 | OpenRouter | OPENROUTER_API_KEY |
| 5 | ElevenLabs | ELEVEN_LABS_KEY, ELEVENLABS_VOICE_ID |
| 6 | OpenAI DALL-E | OPENAI_API_KEY |


## CLI Usage

```bash
# Full auto run (8 min geopolitics video)
python -m src.pipelines.explainer_pipeline \
    --category geopolitics \
    --minutes 8 \
    --auto-approve \
    --art-style editorial

# Manual approval workflow
python -m src.pipelines.explainer_pipeline --category tech --minutes 10
# Review output, then:
python -m src.pipelines.explainer_pipeline --continue {hash} --minutes 10

# Options
--category, -c    News category (geopolitics, tech, economics)
--minutes, -m     Target video length (default: 8)
--auto-approve    Skip topic approval checkpoint
--continue, -k    Resume from topic hash
--voice-id        ElevenLabs voice ID
--art-style       Image style (editorial, flat_vector, watercolor)
```
