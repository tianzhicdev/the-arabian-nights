#!/bin/bash
# Add openings to existing production-ready Animal Farm episodes

set -e

VOICE_ID="ePiPWpzcHZrcqRzFrgQg"
LOGO="resources/wornhole-logo.png"
INPUT_DIR="production_ready/animal_farm"
OUTPUT_DIR="production_ready/animal_farm/with-openning"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Starting production episode opening addition..."

process_episode() {
  local ep=$1
  local input_file=$2
  local output_name=$3

  echo ""
  echo "========================================="
  echo "Processing Episode $ep"
  echo "========================================="

  # Paths
  local input_path="$INPUT_DIR/$input_file"
  local opening_path="/tmp/opening_ep${ep}.mp4"
  local opening_25fps="/tmp/opening_ep${ep}_25fps.mp4"
  local final_path="$OUTPUT_DIR/$output_name"

  # Check if input exists
  if [ ! -f "$input_path" ]; then
    echo "ERROR: Input video not found: $input_path"
    return 1
  fi

  # Step 1: Create opening with logo and voice
  echo "Step 1: Creating opening with logo and narration..."
  python scripts/create_episode_opening.py \
    --episode-number $ep \
    --voice-id "$VOICE_ID" \
    --logo "$LOGO" \
    --silence-duration 2.0 \
    --output "$opening_path"

  if [ ! -f "$opening_path" ]; then
    echo "ERROR: Failed to create opening"
    return 1
  fi

  # Step 2: Convert opening to 25fps and 24kHz to match episode
  echo "Step 2: Converting opening to 25fps and 24kHz..."
  ffmpeg -y -i "$opening_path" -r 25 -ar 24000 -c:a aac -b:a 192k "$opening_25fps" 2>&1 | tail -2

  # Step 3: Concatenate opening + episode
  echo "Step 3: Concatenating opening + episode..."
  local concat_file="/tmp/concat_ep${ep}.txt"
  echo "file '$opening_25fps'" > "$concat_file"
  echo "file '$(pwd)/$input_path'" >> "$concat_file"

  ffmpeg -y -f concat -safe 0 -i "$concat_file" -c copy "$final_path" 2>&1 | tail -2

  # Verify output
  if [ -f "$final_path" ]; then
    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$final_path")
    echo "✓ Episode $ep complete: $final_path"
    echo "  Duration: ${duration}s"
  else
    echo "ERROR: Failed to create final video"
    return 1
  fi
}

# Process all episodes
process_episode 1 "e1-Old_Majors_Dream.mp4" "Episode_01_Old_Majors_Dream.mp4"
process_episode 2 "e2-The_Rebellion_Begins.mp4" "Episode_02_The_Rebellion_Begins.mp4"
process_episode 3 "e3-The_Summer_of_Hope.mp4" "Episode_03_The_Summer_of_Hope.mp4"
process_episode 4 "e4-The_Battle_of_the_Cowshed.mp4" "Episode_04_The_Battle_of_the_Cowshed.mp4"
process_episode 5 "e5-The_Rise_of_Napoleon.mp4" "Episode_05_The_Rise_of_Napoleon.mp4"
process_episode 6 "e6-The_Price_of_Progress.mp4" "Episode_06_The_Price_of_Progress.mp4"
process_episode 7 "e7-The_Bitter_Winter.mp4" "Episode_07_The_Bitter_Winter.mp4"
process_episode 8 "e8-The_Battle_of_the_Windmill.mp4" "Episode_08_The_Battle_of_the_Windmill.mp4"
process_episode 9 "e9-The_Fate_of_Boxer.mp4" "Episode_09_The_Fate_of_Boxer.mp4"
process_episode 10 "e10-The_Final_Betrayal.mp4" "Episode_10_The_Final_Betrayal.mp4"

echo ""
echo "========================================="
echo "Production opening addition complete!"
echo "========================================="
ls -lh "$OUTPUT_DIR"
