#!/bin/bash

# Re-encode episodes with opening using filter_complex for proper audio sync

# Episode 1
echo "Processing Episode 1..."
ffmpeg -y -i experiments/animal_farm_e1/opening.mp4 -i experiments/animal_farm_e1/Old_Majors_Dream_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e1/Old_Majors_Dream_FINAL.mp4

# Episode 2
echo "Processing Episode 2..."
ffmpeg -y -i experiments/animal_farm_e2_emotions/opening.mp4 -i experiments/animal_farm_e2_emotions/The_Rebellion_Begins_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e2_emotions/The_Rebellion_Begins_FINAL.mp4

# Episode 3
echo "Processing Episode 3..."
ffmpeg -y -i experiments/animal_farm_e3/opening.mp4 -i experiments/animal_farm_e3/The_Summer_of_Hope_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e3/The_Summer_of_Hope_FINAL.mp4

# Episode 4
echo "Processing Episode 4..."
ffmpeg -y -i experiments/animal_farm_e4/opening.mp4 -i experiments/animal_farm_e4/The_Battle_of_the_Cowshed_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e4/The_Battle_of_the_Cowshed_FINAL.mp4

# Episode 5
echo "Processing Episode 5..."
ffmpeg -y -i experiments/animal_farm_e5/opening.mp4 -i experiments/animal_farm_e5/The_Rise_of_Napoleon_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e5/The_Rise_of_Napoleon_FINAL.mp4

# Episode 6
echo "Processing Episode 6..."
ffmpeg -y -i experiments/animal_farm_e6/opening.mp4 -i experiments/animal_farm_e6/The_Price_of_Progress_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e6/The_Price_of_Progress_FINAL.mp4

# Episode 7
echo "Processing Episode 7..."
ffmpeg -y -i experiments/animal_farm_e7/opening.mp4 -i experiments/animal_farm_e7/The_Bitter_Winter_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e7/The_Bitter_Winter_FINAL.mp4

# Episode 8
echo "Processing Episode 8..."
ffmpeg -y -i experiments/animal_farm_e8/opening.mp4 -i experiments/animal_farm_e8/The_Battle_of_the_Windmill_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e8/The_Battle_of_the_Windmill_FINAL.mp4

# Episode 9
echo "Processing Episode 9..."
ffmpeg -y -i experiments/animal_farm_e9/opening.mp4 -i experiments/animal_farm_e9/The_Fate_of_Boxer_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e9/The_Fate_of_Boxer_FINAL.mp4

# Episode 10
echo "Processing Episode 10..."
ffmpeg -y -i experiments/animal_farm_e10/opening.mp4 -i experiments/animal_farm_e10/The_Final_Betrayal_slides.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k \
  experiments/animal_farm_e10/The_Final_Betrayal_FINAL.mp4

echo "All episodes re-encoded successfully with proper audio sync!"
