#!/bin/bash

# Concatenate with audio re-encoding to match sample rates

# Episode 1
echo "Episode 1..."
ffmpeg -y -i experiments/animal_farm_e1/opening.mp4 -i experiments/animal_farm_e1/Old_Majors_Dream_slides.mp4 \
  -filter_complex "[0:a]aresample=24000[a0];[a0][1:a]concat=n=2:v=0:a=1[outa]" \
  -map "0:v" -map "[outa]" -c:v copy -c:a aac -b:a 192k \
  experiments/animal_farm_e1/Old_Majors_Dream_FINAL_part1.mp4 && \
ffmpeg -y -i experiments/animal_farm_e1/Old_Majors_Dream_FINAL_part1.mp4 -i experiments/animal_farm_e1/Old_Majors_Dream_slides.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map "0:a" -c:v libx264 -preset fast -crf 23 -c:a copy \
  experiments/animal_farm_e1/Old_Majors_Dream_FINAL.mp4 && rm experiments/animal_farm_e1/Old_Majors_Dream_FINAL_part1.mp4

echo "Done!"
