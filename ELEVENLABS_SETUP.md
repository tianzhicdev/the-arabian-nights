# ElevenLabs Parallel Audio Generation Setup

## Overview

Parallel ElevenLabs audio generation is now ready for the experiments. The system uses ThreadPoolExecutor for concurrent HTTP requests to the ElevenLabs API, enabling fast audio generation for multiple scenes simultaneously.

## What's Been Prepared

### 1. Parallel Audio Generator (`scripts/elevenlabs_audio_generator.py`)

**Key Features:**
- `ElevenLabsSceneGenerator`: Individual scene audio generation
- `ParallelElevenLabsGenerator`: Concurrent generation using ThreadPoolExecutor
- Default 10 concurrent workers (adjustable via `--max-workers`)
- Support for ElevenLabs v3 emotion tags (e.g., `[happy]`, `[sad]`, `[excited]`)
- Automatic progress tracking and error handling
- CLI interface for standalone testing

**API Details:**
- Endpoint: `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- Default model: `eleven_turbo_v2_5` (supports emotion tags)
- Voice settings: stability=0.5, similarity_boost=0.75, style=0.0

### 2. Experiment Directory (`experiments/animal_farm_e2/`)

Copied from `output/animal_farm/episode_2/`:
- `scenes.json` - 50 scenes (awaiting emotion tags)
- `audio/` - Original Chatterbox-generated audio
- `images/` - Scene images
- `video/` - Scene videos
- `metadata.json` - Pipeline metadata

### 3. Validation Test (`test_elevenlabs_setup.py`)

Validates:
- Module imports correctly
- Classes instantiate properly
- Scenes JSON structure is valid
- Dependencies are available
- Emotion tag detection (for future use)

## Next Steps

### 1. Add ElevenLabs API Key

Add to `.env.secrets`:
```bash
ELEVENLABS_API_KEY=your_api_key_here
```

### 2. Get Voice ID

Get a voice ID from your ElevenLabs account. Example voice IDs:
- Rachel: `pNInz6obpgDQGcFmaJgB`
- Clyde: `2EiwWnXFnvU5JabPnv8n`
- (Use your preferred voice)

### 3. Wait for Emotion-Tagged Scenes

User will provide an updated `experiments/animal_farm_e2/scenes.json` with ElevenLabs v3 emotion tags.

**Example emotion tags:**
```json
{
  "scene_id": 1,
  "sentences": [
    "[thoughtful] Old Major had inspired the animals with dreams of freedom.",
    "[sad] But he passed away peacefully one night in early March.",
    "[hopeful] His ideas didn't die with him - they were just beginning to spread."
  ]
}
```

### 4. Test with Small Batch

Once API key and scenes are ready, test with a few scenes first:

```bash
python scripts/elevenlabs_audio_generator.py \
  --scenes experiments/animal_farm_e2/scenes.json \
  --output-dir experiments/animal_farm_e2/audio_elevenlabs \
  --voice-id YOUR_VOICE_ID \
  --max-workers 5
```

### 5. Full Generation

If test succeeds, run full generation with higher concurrency:

```bash
python scripts/elevenlabs_audio_generator.py \
  --scenes experiments/animal_farm_e2/scenes.json \
  --output-dir experiments/animal_farm_e2/audio_elevenlabs \
  --voice-id YOUR_VOICE_ID \
  --max-workers 10
```

## Performance Expectations

- **50 scenes** with concurrent processing (10 workers)
- Average API response: ~2-5 seconds per scene
- Expected total time: ~5-10 minutes (depending on scene length and API performance)
- Much faster than sequential: ~25-50 minutes saved

## Technical Details

### Why ThreadPoolExecutor?

- ElevenLabs uses HTTP API (I/O-bound, not CPU-bound)
- ThreadPoolExecutor is optimal for concurrent HTTP requests
- ProcessPoolExecutor would add unnecessary overhead for I/O operations

### Rate Limiting

- Default: 10 concurrent workers
- Adjust `--max-workers` based on your API tier
- ElevenLabs typically handles 10-20 concurrent requests well
- Monitor for 429 (rate limit) errors and reduce workers if needed

### Emotion Tag Support

- Tags are preserved in the text sent to API
- ElevenLabs v3 models (`eleven_turbo_v2_5` and higher) natively support emotion tags
- No special parsing required - just include tags in sentences

## Files Created

1. `scripts/elevenlabs_audio_generator.py` - Main parallel generator
2. `test_elevenlabs_setup.py` - Setup validation script
3. `experiments/animal_farm_e2/` - Experimental workspace
4. `ELEVENLABS_SETUP.md` - This documentation

## Validation Status

All setup tests passed:
- ✓ Module imports successfully
- ✓ Classes instantiate correctly
- ✓ Scenes JSON structure valid (50 scenes)
- ✓ Dependencies available
- ℹ Awaiting emotion tags from user

## Ready to Proceed

The system is fully prepared for parallel ElevenLabs audio generation. Once the API key is added and emotion-tagged scenes are provided, testing can begin immediately.
