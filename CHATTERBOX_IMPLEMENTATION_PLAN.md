# Chatterbox Integration Implementation Plan

## ✅ Research Summary

### What is Chatterbox?
- **Open-source TTS model** from Resemble AI
- **Voice cloning** capability using audio prompts (5-10 second reference clips)
- **Supports emotion tags** like `[laugh]`, `[chuckle]`, `[pause]`, etc.
- **Sample rate:** 24,000 Hz
- **Runs locally** (CPU or GPU) - no API costs

### Test Results
✓ Chatterbox successfully installed (`pip install chatterbox-tts`)
✓ Model loaded successfully (`ChatterboxTTS.from_pretrained(device="cpu")`)
✓ Audio generation works with voice cloning
✓ Generated 570 KB WAV file from test text
✓ Audio prompt file format: `.mp3`, `.wav`, `.flac` all supported

---

## Implementation Plan

### 1. Core Changes

#### A. Add `--audio` Parameter
**Location:** `scripts/generate_podcast_audio.py`

```python
parser.add_argument('--audio',
                   choices=['elevenlabs', 'chatterbox'],
                   default='elevenlabs',
                   help='Audio generation backend: elevenlabs (API) or chatterbox (local)')
```

#### B. Add `--audio-prompt-path` Parameter (Chatterbox Only)
```python
parser.add_argument('--audio-prompt-path',
                   help='Path to audio prompt file for chatterbox voice cloning (5-10s clip)')
```

---

### 2. Validation Logic

#### A. Incompatible Parameter Check
**When `--audio chatterbox` is specified:**

```python
if args.audio == 'chatterbox':
    # These are ElevenLabs-only parameters
    elevenlabs_only_params = []

    if config['host_1'].get('voice_id'):
        elevenlabs_only_params.append('voice_id')
    if config['host_1'].get('editor_notes'):
        elevenlabs_only_params.append('editor_notes (voice selection)')

    if elevenlabs_only_params:
        print(f"✗ ERROR: --audio chatterbox is incompatible with ElevenLabs-only parameters")
        print(f"  Found: {', '.join(elevenlabs_only_params)}")
        print(f"\n  ElevenLabs-only config fields:")
        print(f"    - voice_id (use --audio-prompt-path instead)")
        print(f"    - editor_notes for voice selection")
        print(f"\n  For chatterbox, use:")
        print(f"    --audio-prompt-path <path-to-speaker-sample.wav>")
        sys.exit(1)
```

**Correct validation per your question:** ✅ YES
- `voice_id` → ElevenLabs only
- `voice_notes`/`editor_notes` for voice selection → ElevenLabs only
- `audio_prompt_path` → Chatterbox only

---

### 3. Config File Format

#### A. ElevenLabs Config (Current)
```json
{
  "host_1": {
    "name": "Speaker Name",
    "voice_id": "abc123...",
    "editor_notes": "Voice description"
  }
}
```

#### B. Chatterbox Config (New)
```json
{
  "host_1": {
    "name": "Speaker Name",
    "audio_prompt_path": "path/to/speaker_sample.wav"
  }
}
```

**Note:** `audio_prompt_path` can also be provided via command line `--audio-prompt-path`

---

### 4. Code Architecture

#### A. Create Audio Generator Abstraction

**New file:** `scripts/audio_backend.py`

```python
from abc import ABC, abstractmethod

class AudioBackend(ABC):
    @abstractmethod
    def generate_chunk(self, dialogues, chunk_num, total_chunks):
        """Generate audio for a chunk of dialogues"""
        pass

class ElevenLabsBackend(AudioBackend):
    def __init__(self, voice_mapping):
        self.voice_mapping = voice_mapping
        # existing ElevenLabs code

    def generate_chunk(self, dialogues, chunk_num, total_chunks):
        # existing generate_dialogue_chunk logic
        pass

class ChatterboxBackend(AudioBackend):
    def __init__(self, audio_prompt_path, device='cpu'):
        from chatterbox import ChatterboxTTS
        self.model = ChatterboxTTS.from_pretrained(device=device)
        self.audio_prompt_path = audio_prompt_path

    def generate_chunk(self, dialogues, chunk_num, total_chunks):
        import torchaudio as ta
        import tempfile

        # Combine all dialogue text
        full_text = " ".join([text for speaker, text in dialogues])

        # Generate audio with voice cloning
        wav = self.model.generate(
            full_text,
            audio_prompt_path=self.audio_prompt_path
        )

        # Save to temp file and return bytes
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            ta.save(f.name, wav, self.model.sr)
            with open(f.name, 'rb') as audio_file:
                return audio_file.read()
```

#### B. Update `generate_podcast_audio.py`

```python
def main():
    # ... existing arg parsing ...

    # Select backend
    if args.audio == 'chatterbox':
        # Validate audio_prompt_path provided
        if not args.audio_prompt_path and 'audio_prompt_path' not in config['host_1']:
            print("✗ ERROR: --audio-prompt-path required for chatterbox")
            sys.exit(1)

        prompt_path = args.audio_prompt_path or config['host_1']['audio_prompt_path']
        backend = ChatterboxBackend(audio_prompt_path=prompt_path)
    else:
        # Existing ElevenLabs logic
        voice_mapping = build_voice_mapping(config)
        backend = ElevenLabsBackend(voice_mapping)

    # Generate audio (same interface for both)
    chunks = chunk_dialogues(dialogues, MAX_CHARS_PER_REQUEST)
    for i, chunk in enumerate(chunks, 1):
        audio_bytes = backend.generate_chunk(chunk, i, len(chunks))
        # ... save chunk ...
```

---

### 5. Important Differences

| Feature | ElevenLabs | Chatterbox |
|---------|-----------|------------|
| **Cost** | API costs (~$0.30/1K chars) | Free (local) |
| **Speed** | Fast (API) | Slower (local compute) |
| **Voice Selection** | voice_id from library | audio_prompt_path (file) |
| **Multi-voice** | Different voice_id per speaker | One audio_prompt for all speakers* |
| **Output Format** | MP3 (streaming) | WAV (24kHz) |
| **Emotion Tags** | v3 supports `[emotion]` | Supports `[laugh]`, `[chuckle]`, etc. |

**Challenge:** Chatterbox uses one voice per generation. For multi-speaker dialogues:
- **Option A:** Generate each speaker separately, then combine (more complex)
- **Option B:** Use single narrator voice for entire dialogue (simpler, current test approach)

---

### 6. Implementation Steps

#### Phase 1: Basic Integration
1. ✅ Install and test chatterbox (`pip install chatterbox-tts`)
2. ✅ Verify audio generation works
3. Add `--audio` parameter
4. Add `--audio-prompt-path` parameter
5. Add validation logic for incompatible params
6. Create `ChatterboxBackend` class
7. Update `generate_podcast_audio.py` to use backend abstraction

#### Phase 2: Multi-Speaker Support (Optional)
1. Generate speaker segments separately
2. Combine audio files with silence gaps
3. Support multiple `audio_prompt_path` for different speakers

#### Phase 3: Testing
1. Test single-narrator script (Crime & Punishment style)
2. Test with emotion tags
3. Compare output quality vs ElevenLabs
4. Performance benchmarks (CPU vs GPU)

---

### 7. Usage Examples

#### Example 1: Single Narrator (Recommended for Chatterbox)
```bash
python3 scripts/generate_podcast_audio.py \
  --source resources/sources/crime-punishment-part1 \
  --audio chatterbox \
  --audio-prompt-path "/Users/biubiu/Downloads/narrator_voice.mp3"
```

#### Example 2: ElevenLabs (Current)
```bash
python3 scripts/generate_podcast_audio.py \
  --source resources/sources/episode1-consciousness \
  --audio elevenlabs
```

---

### 8. Error Messages

```
✗ ERROR: Incompatible parameters for chatterbox backend

  Found in config:
    - host_1.voice_id
    - host_2.voice_id

  These are ElevenLabs-only parameters.

  For chatterbox, remove voice_id from config and use:
    --audio-prompt-path <path-to-speaker-voice-sample.wav>

  Or switch back to ElevenLabs:
    --audio elevenlabs
```

---

## Recommendation

**Start with Phase 1** - Single narrator support for chatterbox
- ✅ Works well for Crime & Punishment style narration
- ✅ Simpler implementation
- ✅ No multi-voice complexity
- ✅ Free & unlimited local generation

**Later:** Add Phase 2 if multi-speaker support needed
- Requires separate generation per speaker
- More complex audio stitching
- May have quality issues at speaker transitions
