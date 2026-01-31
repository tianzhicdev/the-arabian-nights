#!/bin/bash
# Create production-ready Animal Farm episodes with proper openings

set -e

VOICE_ID="ePiPWpzcHZrcqRzFrgQg"
LOGO="resources/wornhole-logo.png"

# Create production_ready directory
mkdir -p production_ready/animal_farm

echo "Starting production episode creation..."

process_episode() {
  local ep=$1
  local dir=$2
  local slides_file=$3
  local title=$4

  echo ""
  echo "========================================="
  echo "Processing Episode $ep: $title"
  echo "========================================="

  # Paths
  local slides_path="experiments/$dir/$slides_file"
  local opening_path="experiments/$dir/new_opening.mp4"
  local final_path="production_ready/animal_farm/Episode_$(printf "%02d" $ep)_${title// /_}.mp4"

  # Check if slides video exists
  if [ ! -f "$slides_path" ]; then
    echo "ERROR: Slides video not found: $slides_path"
    return 1
  fi

  # Step 1: Create new opening with logo and voice
  echo "Step 1: Creating opening with logo..."
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

  # Step 2: Convert opening to 25fps and 24kHz audio to match slides
  echo "Step 2: Converting opening to 25fps and 24kHz audio to match slides..."
  local opening_25fps="experiments/$dir/new_opening_25fps.mp4"
  ffmpeg -y -i "$opening_path" -r 25 -ar 24000 -c:a aac -b:a 192k "$opening_25fps" 2>&1 | tail -2

  # Step 3: Concatenate opening + slides using concat demuxer
  echo "Step 3: Concatenating opening + episode..."

  # Create concat file
  local concat_file="/tmp/ep${ep}_concat.txt"
  echo "file '$(pwd)/$opening_25fps'" > "$concat_file"
  echo "file '$(pwd)/$slides_path'" >> "$concat_file"

  # Concatenate
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
process_episode 1 "animal_farm_e1" "Old_Majors_Dream_slides.mp4" "Old_Majors_Dream"
process_episode 2 "animal_farm_e2_emotions" "The_Rebellion_Begins_slides.mp4" "The_Rebellion_Begins"
process_episode 3 "animal_farm_e3" "The_Summer_of_Hope_slides.mp4" "The_Summer_of_Hope"
process_episode 4 "animal_farm_e4" "The_Battle_of_the_Cowshed_slides.mp4" "The_Battle_of_the_Cowshed"
process_episode 5 "animal_farm_e5" "The_Rise_of_Napoleon_slides.mp4" "The_Rise_of_Napoleon"
process_episode 6 "animal_farm_e6" "The_Price_of_Progress_slides.mp4" "The_Price_of_Progress"
process_episode 7 "animal_farm_e7" "The_Bitter_Winter_slides.mp4" "The_Bitter_Winter"
process_episode 8 "animal_farm_e8" "The_Battle_of_the_Windmill_slides.mp4" "The_Battle_of_the_Windmill"
process_episode 9 "animal_farm_e9" "The_Fate_of_Boxer_slides.mp4" "The_Fate_of_Boxer"
process_episode 10 "animal_farm_e10" "The_Final_Betrayal_slides.mp4" "The_Final_Betrayal"

echo ""
echo "========================================="
echo "Production episode creation complete!"
echo "========================================="
ls -lh production_ready/animal_farm/
