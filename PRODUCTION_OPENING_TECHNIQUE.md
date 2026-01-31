# Production Episode Opening Technique

## Overview

This document describes the technique for adding professional openings to video episodes while maintaining consistent quality, resolution, and audio/video synchronization throughout the final product.

## Problem Statement

**Goal**: Add professional branded openings to existing episode videos without degrading quality or causing synchronization issues.

**Requirements**:
- Logo display on black background
- Voice narration ("Title by Author. Episode X. Narrated by Brand.")
- Configurable silence duration after narration
- Consistent resolution throughout (opening must match episode content)
- Consistent frame rate throughout
- Consistent audio sample rate throughout
- Preserve all original episode content without modification

## Architecture

### Two-Script Approach

1. **`scripts/create_episode_opening.py`** - Creates individual opening segments
2. **`scripts/add_openings_to_production.sh`** - Batch processes all episodes

### Data Flow

```
Episode Number + Config → create_episode_opening.py → Opening Video (temp)
                                                            ↓
                                                    Frame Rate Conversion
                                                            ↓
Opening Video (converted) + Episode Video → FFmpeg Concat → Final Episode
```

## Key Technical Challenges & Solutions

### Challenge 1: Resolution Mismatch

**Problem**: Initial implementation created 1920x1080 openings but episode content was 1280x720, causing visible size inconsistency.

**Solution**: Match opening resolution to episode content resolution.

**Implementation** (`scripts/create_episode_opening.py`):

```python
def create_opening_video(
    logo_path: Path,
    audio_path: Path,
    output_path: Path,
    audio_duration: float,
    silence_duration: float = 2.0
):
    """Create opening video with logo/black background and audio."""
    total_duration = audio_duration + silence_duration

    # Create 1280x720 video (matching episode resolution)
    filter_complex = (
        f"color=c=black:s=1280x720:d={total_duration}:r=30[bg];"
        f"[1:v]scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease[logo];"
        f"[bg][logo]overlay=(W-w)/2:(H-h)/2[v]"
    )

    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'color=c=black:s=1280x720:d={total_duration}:r=30',
        '-i', str(logo_path),
        '-i', str(audio_path),
        '-filter_complex', filter_complex,
        '-map', '[v]',
        '-map', '2:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', str(total_duration),
        '-pix_fmt', 'yuv420p',
        str(output_path)
    ]
```

**Key Points**:
- `color=c=black:s=1280x720` - Creates black background at target resolution
- `scale='min(1280,iw)':'min(720,ih)'` - Scales logo to fit within bounds
- `force_original_aspect_ratio=decrease` - Preserves logo aspect ratio
- `overlay=(W-w)/2:(H-h)/2` - Centers logo on background

### Challenge 2: Frame Rate Mismatch

**Problem**: Opening videos at 30fps concatenated with 25fps episodes caused timing corruption - slides stopped updating at 16:25 mark despite audio continuing.

**Solution**: Convert opening to match episode frame rate before concatenation.

**Implementation** (`scripts/add_openings_to_production.sh`):

```bash
# Step 2: Convert opening to 25fps and 24kHz to match episode
echo "Step 2: Converting opening to 25fps and 24kHz..."
ffmpeg -y -i "$opening_path" -r 25 -ar 24000 -c:a aac -b:a 192k "$opening_25fps"
```

**Key Points**:
- `-r 25` - Sets output frame rate to 25fps
- `-ar 24000` - Sets audio sample rate to 24kHz (matching episode)
- `-c:a aac -b:a 192k` - Re-encodes audio with consistent codec and bitrate

**Why This Matters**: FFmpeg's concat demuxer with `-c copy` requires identical stream parameters. Mismatched frame rates cause timestamp corruption when using stream copy.

### Challenge 3: Audio Sample Rate Mismatch

**Problem**: Opening audio at 44.1kHz vs episode audio at 24kHz caused synchronization drift.

**Solution**: Include audio sample rate conversion in the frame rate conversion step (see above).

### Challenge 4: Concatenation Without Re-encoding

**Problem**: Re-encoding the entire episode would degrade quality and take excessive time.

**Solution**: Use FFmpeg's concat demuxer with stream copy.

**Implementation**:

```bash
# Step 3: Concatenate opening + episode using concat demuxer
local concat_file="/tmp/concat_ep${ep}.txt"
echo "file '$opening_25fps'" > "$concat_file"
echo "file '$(pwd)/$input_path'" >> "$concat_file"

ffmpeg -y -f concat -safe 0 -i "$concat_file" -c copy "$final_path"
```

**Key Points**:
- `-f concat` - Uses concat demuxer (file-based concatenation)
- `-safe 0` - Allows absolute file paths in concat file
- `-c copy` - Copies streams without re-encoding (fast, lossless)
- Concat file uses absolute paths to avoid path resolution issues

**Why This Matters**:
- Stream copy is 100x faster than re-encoding
- No quality loss from re-encoding
- BUT requires perfectly matched stream parameters (codec, resolution, frame rate, sample rate)

### Challenge 5: Path Handling in Concat Files

**Problem**: Initial implementation created paths like `/Users/biubiu/projects/the-arabian-nights//tmp/opening_ep1_25fps.mp4` (double slash).

**Solution**: Use consistent absolute paths, avoid mixing `$(pwd)` with absolute `/tmp` paths.

**Correct Implementation**:

```bash
# /tmp paths are already absolute - don't prefix with $(pwd)
echo "file '$opening_25fps'" > "$concat_file"

# Project paths need $(pwd) prefix
echo "file '$(pwd)/$input_path'" >> "$concat_file"
```

## Audio Generation with ElevenLabs

### Text-to-Speech Configuration

```python
def generate_opening_audio(episode_number: int, voice_id: str, api_key: str, output_path: Path):
    """Generate opening narration using ElevenLabs."""

    # Convert episode number to word
    episode_words = {
        1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
        6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"
    }

    episode_word = episode_words.get(episode_number, str(episode_number))
    text = f"Animal Farm by George Orwell. Episode {episode_word}. Narrated by Wormhole Podcast."

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    # Save MP3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(response.content)

    # Get duration using ffprobe
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)],
        capture_output=True,
        text=True
    )

    duration = float(result.stdout.strip())
    return duration
```

**Key Configuration**:
- Voice ID: `ePiPWpzcHZrcqRzFrgQg` (consistent narrator)
- Model: `eleven_v3` (latest quality)
- Stability: 0.5 (balanced)
- Similarity Boost: 0.75 (strong voice match)

## Complete Workflow

### Step 1: Generate Opening Audio

```bash
python scripts/create_episode_opening.py \
  --episode-number 1 \
  --voice-id "ePiPWpzcHZrcqRzFrgQg" \
  --logo "resources/wornhole-logo.png" \
  --silence-duration 2.0 \
  --output "/tmp/opening_ep1.mp4"
```

**Output**: Opening video at 30fps, 1280x720, with audio

### Step 2: Convert to Match Episode Specs

```bash
ffmpeg -y -i "/tmp/opening_ep1.mp4" \
  -r 25 \
  -ar 24000 \
  -c:a aac \
  -b:a 192k \
  "/tmp/opening_ep1_25fps.mp4"
```

**Output**: Opening video at 25fps, 1280x720, 24kHz audio

### Step 3: Create Concat File

```bash
cat > /tmp/concat_ep1.txt << EOF
file '/tmp/opening_ep1_25fps.mp4'
file '/Users/biubiu/projects/the-arabian-nights/production_ready/animal_farm/e1-Old_Majors_Dream.mp4'
EOF
```

### Step 4: Concatenate

```bash
ffmpeg -y \
  -f concat \
  -safe 0 \
  -i /tmp/concat_ep1.txt \
  -c copy \
  "production_ready/animal_farm/with-openning/Episode_01_Old_Majors_Dream.mp4"
```

**Output**: Final episode with opening, no re-encoding

## Verification Commands

### Check Resolution

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height \
  -of csv=p=0 \
  video.mp4
```

Expected output: `1280,720`

### Check Frame Rate

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate \
  -of csv=p=0 \
  video.mp4
```

Expected output: `25/1`

### Check Audio Sample Rate

```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=sample_rate \
  -of csv=p=0 \
  video.mp4
```

Expected output: `24000`

### Check Duration

```bash
ffprobe -v error \
  -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  video.mp4
```

## Batch Processing Script

**File**: `scripts/add_openings_to_production.sh`

**Key Features**:
- Processes all 10 episodes automatically
- Error handling for missing inputs
- Progress reporting
- Verification of outputs

**Usage**:

```bash
export ELEVENLABS_API_KEY="sk_..."
bash scripts/add_openings_to_production.sh
```

**Configuration**:

```bash
VOICE_ID="ePiPWpzcHZrcqRzFrgQg"
LOGO="resources/wornhole-logo.png"
INPUT_DIR="production_ready/animal_farm"
OUTPUT_DIR="production_ready/animal_farm/with-openning"
```

## Results

### Final Specifications

All episodes have:
- **Resolution**: 1280x720 (HD/720p)
- **Frame Rate**: 25fps
- **Audio**: 24kHz, AAC, mono
- **Video Codec**: H.264 (libx264)
- **Pixel Format**: yuv420p (maximum compatibility)

### Episode Durations

| Episode | Title | Size | Duration |
|---------|-------|------|----------|
| 1 | Old Majors Dream | 87MB | 18:35 |
| 2 | The Rebellion Begins | 79MB | 16:38 |
| 3 | The Summer of Hope | 68MB | 14:09 |
| 4 | The Battle of the Cowshed | 58MB | 11:02 |
| 5 | The Rise of Napoleon | 72MB | 15:11 |
| 6 | The Price of Progress | 81MB | 17:19 |
| 7 | The Bitter Winter | 60MB | 13:00 |
| 8 | The Battle of the Windmill | 76MB | 16:26 |
| 9 | The Fate of Boxer | 81MB | 15:30 |
| 10 | The Final Betrayal | 88MB | 18:26 |

**Total**: ~2.3GB for complete series

### Opening Structure

Each opening consists of:
1. **Logo Display**: Wormhole logo centered on black background (1280x720)
2. **Narration**: "Animal Farm by George Orwell. Episode [X]. Narrated by Wormhole Podcast."
3. **Silence**: 2.0 seconds
4. **Episode Content**: Original stitched slides with audio (completely preserved)

## Lessons Learned

### Critical Success Factors

1. **Match ALL stream parameters** - Resolution, frame rate, audio sample rate must match exactly for concat demuxer with stream copy
2. **Convert opening, not episode** - Opening is small (~10s), episode is large (10-20min). Convert the small file.
3. **Use absolute paths in concat files** - Avoids path resolution issues
4. **Verify at each step** - Check resolution, frame rate, audio sample rate after each transformation
5. **Stream copy when possible** - 100x faster, no quality loss

### Common Pitfalls to Avoid

1. **Resolution mismatch** - Creates visible size changes during playback
2. **Frame rate mismatch** - Causes timestamp corruption and content truncation
3. **Audio sample rate mismatch** - Causes audio sync drift over time
4. **Re-encoding everything** - Slow and causes quality degradation
5. **Relative paths in concat files** - Can cause "No such file or directory" errors

## File References

### Main Scripts

- `scripts/create_episode_opening.py` - Opening creation (lines 73-143)
- `scripts/add_openings_to_production.sh` - Batch processing (lines 16-73)

### Configuration

- Voice ID: `ePiPWpzcHZrcqRzFrgQg`
- Logo: `resources/wornhole-logo.png` (1024x1024)
- Input: `production_ready/animal_farm/*.mp4`
- Output: `production_ready/animal_farm/with-openning/*.mp4`

### Environment Variables

```bash
ELEVENLABS_API_KEY - Required for audio generation
```

## Adaptability

This technique can be adapted for:

- **Different resolutions** - Change `1280x720` to target resolution
- **Different frame rates** - Change `25` to target fps
- **Different audio rates** - Change `24000` to target sample rate
- **Different narration** - Modify text template in `generate_opening_audio()`
- **Different silence duration** - Use `--silence-duration` parameter
- **Different logos** - Use `--logo` parameter
- **Different voices** - Use `--voice-id` parameter

## Performance

- **Opening creation**: ~10-15 seconds per episode (API call + video creation)
- **Frame rate conversion**: ~1-2 seconds per opening
- **Concatenation**: ~1-2 seconds per episode (stream copy, no re-encoding)
- **Total per episode**: ~15-20 seconds
- **Total for 10 episodes**: ~3-4 minutes

## Conclusion

This technique successfully creates production-ready episodes with professional openings while:
- Maintaining perfect quality (no unnecessary re-encoding)
- Preserving all original content
- Ensuring consistent specifications throughout
- Processing efficiently (minutes, not hours)
- Handling edge cases (path issues, format mismatches)

The key insight is that **consistency in stream parameters enables fast, lossless concatenation**. By converting only the small opening segment to match the episode specifications, we achieve the best balance of quality, speed, and simplicity.
