#!/bin/bash
#  Convert all openings to 24kHz and concatenate properly

# Episodes 2-10
for ep in 2 3 4 5 6 7 8 9 10; do
  case $ep in
    2) dir="experiments/animal_farm_e2_emotions"; name="The_Rebellion_Begins" ;;
    3) dir="experiments/animal_farm_e3"; name="The_Summer_of_Hope" ;;
    4) dir="experiments/animal_farm_e4"; name="The_Battle_of_the_Cowshed" ;;
    5) dir="experiments/animal_farm_e5"; name="The_Rise_of_Napoleon" ;;
    6) dir="experiments/animal_farm_e6"; name="The_Price_of_Progress" ;;
    7) dir="experiments/animal_farm_e7"; name="The_Bitter_Winter" ;;
    8) dir="experiments/animal_farm_e8"; name="The_Battle_of_the_Windmill" ;;
    9) dir="experiments/animal_farm_e9"; name="The_Fate_of_Boxer" ;;
    10) dir="experiments/animal_farm_e10"; name="The_Final_Betrayal" ;;
  esac

  echo "Episode $ep: Converting opening to 24kHz..."
  ffmpeg -y -i "$dir/opening.mp4" -ar 24000 -c:v copy -c:a aac -b:a 192k "$dir/opening_24k.mp4" 2>&1 | tail -1

  echo "Episode $ep: Concatenating..."
  python scripts/prepend_opening.py --opening "$dir/opening_24k.mp4" --episode-video "$dir/${name}_slides.mp4" --output "$dir/Episode_0${ep}_FINAL.mp4" 2>&1 | tail -2
done

echo "All episodes complete with proper audio sync!"
