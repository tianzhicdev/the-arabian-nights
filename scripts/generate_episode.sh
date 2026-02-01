#!/usr/bin/env bash
# Simplified end-to-end Animal Farm episode generation
# Usage: ./generate_episode.sh --scenes SCENES.json --voice-id VOICE_ID --output-dir OUTPUT_DIR

set -e

# Default values
VOICE_ID="ePiPWpzcHZrcqRzFrgQg"
STYLE_REF="resources/styles/vg_converted.jpg"
API_KEY="${ELEVENLABS_API_KEY}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --scenes)
      SCENES="$2"
      shift 2
      ;;
    --voice-id)
      VOICE_ID="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required params
if [ -z "$SCENES" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: $0 --scenes SCENES.json --output-dir OUTPUT_DIR [--voice-id VOICE_ID]"
  exit 1
fi

if [ -z "$API_KEY" ]; then
  echo "Error: ELEVENLABS_API_KEY environment variable not set"
  exit 1
fi

echo "======================================================================"
echo "Animal Farm Episode Generation"
echo "======================================================================"
echo "Scenes: $SCENES"
echo "Output: $OUTPUT_DIR"
echo "Voice ID: $VOICE_ID"
echo "Style: $STYLE_REF"
echo "======================================================================"

# Step 1: Generate ElevenLabs audio (with skip logic)
echo ""
echo "Step 1/4: Generating ElevenLabs audio..."
python scripts/elevenlabs_audio_generator.py \
  --scenes "$SCENES" \
  --output-dir "$OUTPUT_DIR/audio" \
  --voice-id "$VOICE_ID" \
  --max-workers 10

# Step 2: Convert MP3 to WAV
echo ""
echo "Step 2/4: Converting MP3 to WAV..."
python -c "
import subprocess
from pathlib import Path

audio_dir = Path('$OUTPUT_DIR/audio')
mp3_files = sorted(audio_dir.glob('*.mp3'))
print(f'Converting {len(mp3_files)} MP3 files...')

for mp3_file in mp3_files:
    wav_file = mp3_file.with_suffix('.wav')
    if wav_file.exists():
        continue
    subprocess.run([
        'ffmpeg', '-i', str(mp3_file),
        '-ar', '24000', '-ac', '1',
        str(wav_file), '-y'
    ], capture_output=True, check=True)

wav_count = len(list(audio_dir.glob('*.wav')))
print(f'✓ {wav_count} WAV files ready')
"

# Step 3: Generate video (slides mode, with skip logic for images)
echo ""
echo "Step 3/4: Generating video..."
python generate_video.py \
  --scenes "$SCENES" \
  --mode slides \
  --art-reference "$STYLE_REF" \
  --output-dir "$OUTPUT_DIR" \
  --skip-audio

echo ""
echo "======================================================================"
echo "✓ Episode generation complete!"
echo "Output: $OUTPUT_DIR"
echo "======================================================================"
