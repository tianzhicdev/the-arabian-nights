# TikTok Shorts Generation - Feature Design

## Overview

Generate multiple short-form videos (TikTok/YouTube Shorts/Instagram Reels) from a single story, with the ability to regenerate with different art styles and voices.

## User Story

> "I have a 5-minute story. I want to generate 10 TikTok shorts (30-45 seconds each), then try different art styles and voices to see which performs better."

## Command-Line Interface

### Basic Usage

```bash
# Generate 10 TikTok shorts (default)
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --art-reference style.jpg \
  --audio-reference voice.mp3

# Output:
# output/tiktok_clips/
#   clip_001.mp4  (30s)
#   clip_002.mp4  (35s)
#   clip_003.mp4  (40s)
#   ...
#   clip_010.mp4  (32s)
```

### Advanced Options

```bash
# Specify number of clips
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --tiktok-count 5 \
  --tiktok-duration 45 \
  --art-reference style.jpg \
  --audio-reference voice.mp3

# Regenerate with different art style (voice cached)
python generate_video.py \
  --tiktok-outputs output/tiktok_clips \
  --rerun-tiktok \
  --art-reference new_style.jpg

# Regenerate with different voice (art cached)
python generate_video.py \
  --tiktok-outputs output/tiktok_clips \
  --rerun-tiktok \
  --audio-reference new_voice.mp3

# Mix styles/voices per clip
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --tiktok-style-rotation "picasso.jpg,vg.jpg,roman.jpg" \
  --tiktok-voice-rotation "deep.mp3,calm.mp3,dramatic.mp3"
```

## Architecture

### 1. Content Splitting Strategy

```python
class TikTokClipper:
    """Splits story into TikTok-optimized clips."""

    def split_story_to_clips(self,
                            text: str,
                            target_count: int = 10,
                            target_duration: int = 40) -> List[Clip]:
        """
        Split story into clips optimized for TikTok.

        Strategy:
        1. Identify natural breakpoints (dramatic moments, cliffhangers)
        2. Ensure each clip is 30-60 seconds
        3. Add hooks at start, cliffhangers at end
        4. Optimize for vertical 9:16 format

        Returns:
            List of Clip objects with text, expected_duration, hook, cliffhanger
        """
```

### 2. Clip Structure

```python
@dataclass
class TikTokClip:
    """Represents a single TikTok short."""

    clip_id: int                    # 1-10
    text: str                       # Narrative content
    hook: str                       # Opening hook (first 3 seconds)
    body: str                       # Main content
    cliffhanger: str                # Ending (drives to next clip)

    # Generated content
    narration: str                  # Narrator text
    video_description: str          # Visual prompts

    # Metadata
    expected_duration: int          # Target seconds (30-60)
    vertical_optimized: bool        # 9:16 format

    # Dependencies
    art_style: str                  # Reference or description
    voice_id: str                   # Voice reference

    # Caching
    fingerprint: str                # For cache validation
```

### 3. Directory Structure

```
output/tiktok_clips/
├── .tiktok_manifest.json          # Overall config
├── clips/
│   ├── clip_001/
│   │   ├── .fingerprint.json      # Cache validation
│   │   ├── clip_config.json       # Clip metadata
│   │   ├── narration.json         # Scene data
│   │   ├── audio/
│   │   │   └── clip_001.wav
│   │   ├── images/
│   │   │   └── clip_001_9x16.png
│   │   └── clip_001_final.mp4     # Final output
│   ├── clip_002/
│   │   └── ...
│   └── ...
├── clip_001_final.mp4             # Symlink to clips/clip_001/clip_001_final.mp4
├── clip_002_final.mp4
└── ...
```

### 4. Manifest File

```json
{
  "version": "1.0",
  "story_source": "story.txt",
  "story_hash": "abc123...",
  "created_at": "2026-01-28T15:00:00",
  "config": {
    "clip_count": 10,
    "target_duration": 40,
    "aspect_ratio": "9:16",
    "mode": "slides"
  },
  "clips": [
    {
      "clip_id": 1,
      "text_preview": "In the shadows of ancient...",
      "duration": 35,
      "art_style": {
        "reference": "resources/styles/vg.jpg",
        "hash": "f9cc5c65..."
      },
      "voice": {
        "reference": "resources/voices/deep.mp3",
        "hash": "4b0264d9..."
      },
      "status": "completed",
      "output": "clips/clip_001/clip_001_final.mp4"
    },
    // ... 9 more clips
  ],
  "variations": [
    {
      "variation_id": "style_picasso",
      "type": "art_style",
      "reference": "resources/styles/picasso.jpeg",
      "clips_affected": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    },
    {
      "variation_id": "voice_calm",
      "type": "voice",
      "reference": "resources/voices/calm.mp3",
      "clips_affected": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    }
  ]
}
```

## Feature Design: Rerun with Different Styles/Voices

### Use Case 1: Regenerate All Clips with New Art Style

```bash
# Initial generation
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --art-reference style_a.jpg \
  --audio-reference voice.mp3

# Regenerate with new art (voice cached)
python generate_video.py \
  --tiktok-outputs output/tiktok_clips \
  --rerun-tiktok \
  --art-reference style_b.jpg \
  --output-variation style_b
```

**Result:**
```
output/tiktok_clips/
├── clip_001_final.mp4          # Original (style_a)
├── clip_001_style_b.mp4        # Variation (style_b)
├── clip_002_final.mp4
├── clip_002_style_b.mp4
└── ...
```

### Use Case 2: Regenerate Specific Clips

```bash
# Regenerate clips 3, 5, 7 with new voice
python generate_video.py \
  --tiktok-outputs output/tiktok_clips \
  --rerun-tiktok-clips 3,5,7 \
  --audio-reference new_voice.mp3 \
  --output-variation voice_dramatic
```

### Use Case 3: Style/Voice Rotation

```bash
# Different style per clip (cycle through 3 styles)
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --tiktok-style-rotation "style_a.jpg,style_b.jpg,style_c.jpg" \
  --audio-reference voice.mp3
```

**Result:**
- Clip 1: style_a
- Clip 2: style_b
- Clip 3: style_c
- Clip 4: style_a (cycles)
- Clip 5: style_b
- etc.

### Use Case 4: A/B Testing Matrix

```bash
# Generate matrix of style x voice combinations
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok_clips \
  --tiktok-ab-test \
  --art-references "style_a.jpg,style_b.jpg" \
  --audio-references "voice_1.mp3,voice_2.mp3"
```

**Result:**
```
output/tiktok_clips/
├── clip_001_style_a_voice_1.mp4
├── clip_001_style_a_voice_2.mp4
├── clip_001_style_b_voice_1.mp4
├── clip_001_style_b_voice_2.mp4
├── clip_002_style_a_voice_1.mp4
└── ...
```

## Caching Strategy

### Per-Clip Fingerprinting

```python
class TikTokClipFingerprint:
    """Fingerprint for a single clip."""

    def __init__(self,
                 clip_id: int,
                 text_hash: str,
                 art_hash: str,
                 voice_hash: str,
                 params: dict):
        self.clip_id = clip_id
        self.components = {
            'text': text_hash,      # Content of this clip
            'art': art_hash,        # Art style reference
            'voice': voice_hash,    # Voice reference
            'params': params        # Other parameters
        }
        self.hash = self._calculate_hash()

    def allows_art_reuse(self, new_fingerprint) -> bool:
        """Check if art can be reused (text + art unchanged)."""
        return (self.components['text'] == new_fingerprint.components['text'] and
                self.components['art'] == new_fingerprint.components['art'])

    def allows_audio_reuse(self, new_fingerprint) -> bool:
        """Check if audio can be reused (text + voice unchanged)."""
        return (self.components['text'] == new_fingerprint.components['text'] and
                self.components['voice'] == new_fingerprint.components['voice'])
```

### Regeneration Decision Matrix

| Change | Narration | Audio | Images | Video | Assembly |
|--------|-----------|-------|--------|-------|----------|
| Text | Regenerate | Regenerate | Regenerate | Regenerate | Regenerate |
| Art Style | Cache | Cache | Regenerate | Regenerate | Regenerate |
| Voice | Cache | Regenerate | Cache | Regenerate | Regenerate |
| Both | Cache | Regenerate | Regenerate | Regenerate | Regenerate |

## TikTok-Specific Optimizations

### 1. Vertical Format (9:16)

```python
def generate_vertical_image(self, prompt: str, style_ref: str) -> Image:
    """
    Generate 9:16 vertical image optimized for mobile.

    Considerations:
    - Focus subjects in center/upper-center (safe area)
    - Text overlay space at top/bottom
    - High contrast for small screens
    - Face-focused compositions
    """
    return client.generate_with_style_reference(
        prompt=prompt,
        style_reference=style_ref,
        size="1080x1920",  # 9:16 vertical
        composition_hints={
            'focal_area': 'upper_center',
            'safe_zone': 'center_60_percent',
            'text_overlay_space': 'top_and_bottom'
        }
    )
```

### 2. Hook Generation

```python
def generate_clip_hook(self, clip_text: str) -> str:
    """
    Generate compelling 3-second hook.

    Strategies:
    - Question: "What if you discovered..."
    - Shock: "Nobody saw it coming..."
    - Mystery: "The secret that changed everything..."
    - Promise: "Wait until you see what happens next..."
    """
```

### 3. Cliffhanger Generation

```python
def generate_cliffhanger(self, clip_text: str, next_clip: str) -> str:
    """
    Generate cliffhanger ending to drive to next clip.

    Strategies:
    - Tease: "But then something unexpected happened..."
    - Question: "The question is, what came next?"
    - Reveal: "The truth was far more terrifying..."
    - Continue: "Part 2 reveals the shocking twist..."
    """
```

### 4. Captions/Subtitles

```python
def generate_captions(self, audio_path: Path, output_path: Path):
    """
    Generate word-level captions for accessibility and engagement.

    Features:
    - Word-by-word highlighting (TikTok style)
    - Auto-positioned at top of frame
    - High contrast background
    - Emoji injection at key moments
    """
```

## Command-Line Parameters

### New Parameters

```python
parser.add_argument('--tiktok-outputs', type=str,
                   help='Generate TikTok shorts to this directory')

parser.add_argument('--tiktok-count', type=int, default=10,
                   help='Number of clips to generate (default: 10)')

parser.add_argument('--tiktok-duration', type=int, default=40,
                   help='Target duration per clip in seconds (default: 40)')

parser.add_argument('--tiktok-format', type=str, default='vertical',
                   choices=['vertical', 'square'],
                   help='Aspect ratio: vertical (9:16) or square (1:1)')

parser.add_argument('--rerun-tiktok', action='store_true',
                   help='Regenerate existing TikTok clips with new settings')

parser.add_argument('--rerun-tiktok-clips', type=str,
                   help='Comma-separated clip IDs to regenerate (e.g., "1,3,5")')

parser.add_argument('--output-variation', type=str,
                   help='Variation name for outputs (e.g., "style_b", "voice_dramatic")')

parser.add_argument('--tiktok-style-rotation', type=str,
                   help='Comma-separated art references to rotate through clips')

parser.add_argument('--tiktok-voice-rotation', type=str,
                   help='Comma-separated voice references to rotate through clips')

parser.add_argument('--tiktok-ab-test', action='store_true',
                   help='Generate all combinations of styles and voices')

parser.add_argument('--tiktok-captions', action='store_true',
                   help='Add word-level captions (TikTok style)')

parser.add_argument('--tiktok-music', type=str,
                   help='Background music track to mix with narration')
```

## Implementation Plan

### Phase 1: Basic TikTok Generation (MVP)

```python
# File: scripts/tiktok_generator.py

class TikTokGenerator:
    """Generate TikTok-optimized short videos."""

    def generate_clips(self,
                      text: str,
                      output_dir: Path,
                      count: int = 10,
                      target_duration: int = 40,
                      art_reference: str = None,
                      audio_reference: str = None):
        """
        Generate TikTok clips from story.

        Steps:
        1. Split text into clips using ClipSplitter
        2. Generate narration for each clip
        3. Generate audio for each clip
        4. Generate vertical images (9:16)
        5. Assemble clips with captions
        6. Save manifest
        """

        # Split story into clips
        splitter = TikTokClipSplitter()
        clips = splitter.split(text, count, target_duration)

        # Process each clip
        for clip in clips:
            clip_dir = output_dir / 'clips' / f'clip_{clip.id:03d}'
            clip_dir.mkdir(parents=True, exist_ok=True)

            # Check cache
            fingerprint = self._create_fingerprint(clip, art_reference, audio_reference)
            if self._check_cache(clip_dir, fingerprint):
                continue

            # Generate content
            self._generate_clip(clip, clip_dir, art_reference, audio_reference)

            # Save fingerprint
            self._save_fingerprint(clip_dir, fingerprint)
```

### Phase 2: Regeneration Support

```python
def regenerate_clips(self,
                    output_dir: Path,
                    clip_ids: List[int] = None,
                    art_reference: str = None,
                    audio_reference: str = None,
                    variation_name: str = None):
    """
    Regenerate clips with new art/voice.

    Caching logic:
    - Same art reference → Reuse images
    - Same voice reference → Reuse audio
    - Only regenerate what changed
    """

    # Load manifest
    manifest = self._load_manifest(output_dir)

    # Determine which clips to regenerate
    if clip_ids is None:
        clip_ids = list(range(1, len(manifest['clips']) + 1))

    # Process each clip
    for clip_id in clip_ids:
        clip = manifest['clips'][clip_id - 1]
        clip_dir = output_dir / 'clips' / f'clip_{clip_id:03d}'

        # Determine what changed
        art_changed = (art_reference and
                      art_reference != clip['art_style']['reference'])
        voice_changed = (audio_reference and
                        audio_reference != clip['voice']['reference'])

        # Regenerate only what changed
        if art_changed:
            self._regenerate_images(clip_dir, art_reference)
        if voice_changed:
            self._regenerate_audio(clip_dir, audio_reference)

        # Reassemble
        self._reassemble_clip(clip_dir, variation_name)
```

### Phase 3: Style/Voice Rotation

```python
def generate_with_rotation(self,
                          text: str,
                          output_dir: Path,
                          art_references: List[str],
                          voice_references: List[str] = None):
    """
    Generate clips with rotating styles/voices.

    Example:
        art_references = ['a.jpg', 'b.jpg', 'c.jpg']
        Clip 1 → a.jpg, Clip 2 → b.jpg, Clip 3 → c.jpg, Clip 4 → a.jpg, ...
    """

    clips = self._split_story(text)

    for i, clip in enumerate(clips):
        # Rotate through references
        art_ref = art_references[i % len(art_references)]
        voice_ref = voice_references[i % len(voice_references)] if voice_references else None

        self._generate_clip(clip, output_dir, art_ref, voice_ref)
```

### Phase 4: A/B Testing Matrix

```python
def generate_ab_test_matrix(self,
                           text: str,
                           output_dir: Path,
                           art_references: List[str],
                           voice_references: List[str]):
    """
    Generate all combinations for A/B testing.

    Example:
        art_references = ['a.jpg', 'b.jpg']
        voice_references = ['v1.mp3', 'v2.mp3']

        Generates:
        - clip_001_a_v1.mp4
        - clip_001_a_v2.mp4
        - clip_001_b_v1.mp4
        - clip_001_b_v2.mp4
        - ... for all clips
    """

    clips = self._split_story(text)

    for clip in clips:
        for art_ref in art_references:
            for voice_ref in voice_references:
                variation_name = f"{Path(art_ref).stem}_{Path(voice_ref).stem}"
                self._generate_clip(clip, output_dir, art_ref, voice_ref, variation_name)
```

## Usage Examples

### Example 1: Generate 10 TikTok Clips

```bash
python generate_video.py \
  --text resources/stories/gutenberg/01_the_call_of_cthulhu.txt \
  --tiktok-outputs output/tiktok/cthulhu \
  --art-reference resources/styles/vg_converted.jpg \
  --audio-reference resources/voices/sam-deep.mp3
```

Output: `clip_001.mp4` through `clip_010.mp4` (~40s each)

### Example 2: Try Different Art Style

```bash
# Original
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok/test \
  --art-reference vg.jpg \
  --audio-reference deep.mp3

# Try Picasso style (audio cached)
python generate_video.py \
  --tiktok-outputs output/tiktok/test \
  --rerun-tiktok \
  --art-reference picasso.jpg \
  --output-variation picasso
```

Result:
- `clip_001.mp4` (VG style, deep voice)
- `clip_001_picasso.mp4` (Picasso style, deep voice - reused audio!)

### Example 3: Try Different Voice

```bash
# Try calm voice (images cached)
python generate_video.py \
  --tiktok-outputs output/tiktok/test \
  --rerun-tiktok \
  --audio-reference calm.mp3 \
  --output-variation calm
```

Result:
- `clip_001.mp4` (VG style, deep voice)
- `clip_001_calm.mp4` (VG style, calm voice - reused images!)

### Example 4: Regenerate Specific Clips

```bash
# Clips 1-3 are good, regenerate 4-6 with new style
python generate_video.py \
  --tiktok-outputs output/tiktok/test \
  --rerun-tiktok-clips 4,5,6 \
  --art-reference new_style.jpg \
  --output-variation v2
```

### Example 5: Style Rotation

```bash
python generate_video.py \
  --text story.txt \
  --tiktok-outputs output/tiktok/test \
  --tiktok-style-rotation "vg.jpg,picasso.jpg,roman.jpg" \
  --audio-reference deep.mp3
```

Result:
- Clip 1: VG style
- Clip 2: Picasso style
- Clip 3: Roman style
- Clip 4: VG style (cycles)
- ...

## Cost Estimation

### Per-Clip Costs (Slides Mode)

| Stage | Cost | Time |
|-------|------|------|
| Narration generation | $0.002 | 2s |
| Audio generation | $0.00 | 8s |
| Image generation (9:16) | $0.15 | 8s |
| Video assembly | $0.00 | 2s |
| **Total per clip** | **$0.152** | **20s** |

### 10 Clips

- First generation: $1.52 (10 clips)
- Regenerate with new art: $1.50 (images only, audio cached)
- Regenerate with new voice: $0.02 (audio only, images cached)
- A/B test (2 styles × 2 voices): $6.08 (4 combinations × 10 clips)

## Summary

### Feature Highlights

✅ **Generate TikTok shorts** from any story (10 by default)
✅ **Regenerate with new art** (cache audio)
✅ **Regenerate with new voice** (cache images)
✅ **Selective regeneration** (specific clips only)
✅ **Style/voice rotation** (different style per clip)
✅ **A/B testing matrix** (all combinations)
✅ **Fingerprint caching** (avoid redundant work)
✅ **Vertical format** (9:16 optimized)

### Next Steps

1. Implement `TikTokClipSplitter` (split story into clips)
2. Implement `TikTokGenerator` (generate clips)
3. Add `--tiktok-outputs` parameter
4. Add regeneration support
5. Test with real stories
