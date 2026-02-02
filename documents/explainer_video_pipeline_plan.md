# Explainer Video Pipeline - Implementation Plan

## Overview

Create a pipeline that generates 8-minute explanatory videos on trending topics.

**User Choices:**
- News API: xAI Grok (real-time web search)
- Voice: Kokoro local (`am_onyx` deep male, `speed=0.75`)
- Art Style: Flat vector illustration
- Duration: ~8 minutes (16-20 scenes)

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXPLAINER VIDEO PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: NEWS DISCOVERY (xAI Grok)
    Input:  Category hint (optional): "geopolitics", "tech", "economics"
    Output: List of 5-10 trending topics with brief summaries

         │
         ▼

Step 2: TOPIC SELECTION (OpenRouter - Claude/GPT-4)
    Input:  List of topics from Step 1
    Output: Selected topic + reasoning + target angle

         │
         ▼

Step 3: DEEP RESEARCH (xAI Grok with search)
    Input:  Selected topic
    Output: Comprehensive research notes (facts, context, implications)

         │
         ▼

Step 4: SCRIPT GENERATION (OpenRouter)
    Input:  Research notes + target duration (8 min)
    Output: JSON with scenes:
            [
              {
                "scene_number": 1,
                "narration": "Text to speak (15-30 seconds worth)",
                "scene_image_description": "Flat vector illustration of...",
                "duration_estimate": 20
              },
              ...
            ]

         │
         ▼

Step 5: AUDIO GENERATION (Kokoro local)
    Input:  Scene narrations
    Output: audio/scene_01.wav, scene_02.wav, ...
    Voice:  am_onyx, speed=0.75

         │
         ▼

Step 6: IMAGE GENERATION (OpenAI DALL-E 3)
    Input:  Scene image descriptions (with flat vector style prefix)
    Output: images/scene_01.png, scene_02.png, ...
    Style:  "Flat vector illustration style, clean lines, simple shapes..."

         │
         ▼

Step 7: VIDEO ASSEMBLY
    Input:  Audio files + Image files
    Output: scenes/scene_01.mp4, scene_02.mp4, ...
    Method: Image as background, audio overlay, Ken Burns effect

         │
         ▼

Step 8: FINAL COMPOSITION
    Input:  All scene videos
    Output: output/explainer_{topic_hash}_{timestamp}.mp4
    Add:    Intro card, outro card, background music (optional)

         │
         ▼

Step 9: QUEUE FOR UPLOAD
    Output: ~/upload_queue_main/{hash}/
            - video.mp4
            - metadata.json (title, description, tags)
```

---

## New Components to Build

### 1. `src/clients/xai_client.py` (NEW)

```python
class XAIClient:
    """xAI Grok API client with web search capabilities."""

    def __init__(self):
        self.api_key = os.getenv("XAI_TOKEN")
        self.base_url = "https://api.x.ai/v1"

    def search_news(self, category: str = None) -> List[Dict]:
        """Search for trending news topics."""
        # Uses Grok's real-time search capability

    def research_topic(self, topic: str) -> str:
        """Deep research on a specific topic."""
        # Returns comprehensive research notes
```

### 2. `src/generators/explainer_script_generator.py` (NEW)

```python
class ExplainerScriptGenerator:
    """Generate educational video scripts with scenes."""

    def __init__(self, openrouter_client):
        self.llm = openrouter_client

    def select_topic(self, topics: List[Dict]) -> Dict:
        """Use LLM to pick best topic for explainer video."""

    def generate_script(self, research: str, target_minutes: int = 8) -> Dict:
        """Generate scene-by-scene script."""
        # Returns: {
        #   "title": "...",
        #   "description": "...",
        #   "scenes": [...]
        # }
```

### 3. `src/generators/kokoro_audio_generator.py` (NEW)

```python
class KokoroAudioGenerator:
    """Kokoro TTS for natural narration."""

    def __init__(self, voice: str = "am_onyx", speed: float = 0.75):
        self.kokoro = Kokoro(...)
        self.voice = voice
        self.speed = speed

    def generate_scene_audio(self, text: str, output_path: Path) -> float:
        """Generate audio for a scene. Returns duration."""

    def generate_all_scenes(self, scenes: List[Dict], output_dir: Path) -> Dict[int, float]:
        """Generate audio for all scenes. Returns {scene_num: duration}."""
```

### 4. `src/pipelines/explainer_pipeline.py` (NEW)

```python
class ExplainerPipeline:
    """Main orchestrator for explainer video generation."""

    def __init__(self):
        self.xai = XAIClient()
        self.openrouter = OpenRouterClient()
        self.script_gen = ExplainerScriptGenerator(self.openrouter)
        self.audio_gen = KokoroAudioGenerator()
        self.image_gen = OpenAIImageClient()  # existing
        self.video_assembler = VideoAssembler()  # existing

    def run(self, category: str = None) -> Path:
        """Run full pipeline. Returns path to final video."""
```

---

## Files to Create

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/clients/xai_client.py` | xAI Grok API | requests |
| `src/generators/explainer_script_generator.py` | Script generation | OpenRouterClient |
| `src/generators/kokoro_audio_generator.py` | Kokoro TTS wrapper | kokoro-onnx |
| `src/pipelines/explainer_pipeline.py` | Main orchestrator | All above |
| `scripts/run_explainer_pipeline.sh` | Shell wrapper | Python venv |

## Files to Reuse (No Changes)

| File | Usage |
|------|-------|
| `src/clients/openrouter_client.py` | LLM calls |
| `src/clients/openai_image_client.py` | DALL-E 3 |
| `src/generators/video_assembler.py` | Video composition |
| `src/upload/youtube_uploader.py` | YouTube upload |
| `src/utils/cache_manager_v2.py` | Caching |

---

## Image Prompt Template

For flat vector illustration style:

```
"Flat vector illustration style, clean geometric shapes, limited color palette,
no gradients, simple minimalist design, infographic aesthetic.
Scene: {scene_image_description}"
```

---

## Estimated Costs Per Video

| Step | API | Est. Cost |
|------|-----|-----------|
| News Search | xAI Grok | ~$0.05 |
| Topic Selection | OpenRouter (Claude) | ~$0.02 |
| Deep Research | xAI Grok | ~$0.10 |
| Script Generation | OpenRouter (Claude) | ~$0.15 |
| Audio (Kokoro) | Local | $0.00 |
| Images (18 scenes) | DALL-E 3 | ~$0.72 (18 × $0.04) |
| **Total** | | **~$1.04** |

---

## User Decisions

| Question | Answer |
|----------|--------|
| Background music | No - clean narration only |
| Approval step | Pause after topic selection for user approval |
| Intermediate outputs | Yes - save research notes, script JSON, etc. |

## Output Structure

```
output/explainer/{topic_hash}/
├── 01_news_topics.json          # Raw news search results
├── 02_selected_topic.json       # Topic + reasoning
├── 03_research_notes.md         # Deep research output
├── 04_script.json               # Scene-by-scene script
├── audio/
│   ├── scene_01.wav
│   ├── scene_02.wav
│   └── ...
├── images/
│   ├── scene_01.png
│   ├── scene_02.png
│   └── ...
├── scenes/
│   ├── scene_01.mp4
│   ├── scene_02.mp4
│   └── ...
└── final_video.mp4              # Complete video
```

---

## Next Steps

1. ✅ Plan created
2. ⏳ User approval
3. 🔨 Implement xai_client.py
4. 🔨 Implement kokoro_audio_generator.py
5. 🔨 Implement explainer_script_generator.py
6. 🔨 Implement explainer_pipeline.py
7. 🧪 Test with a sample topic
8. 📤 Queue for upload
