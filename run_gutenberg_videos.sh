#!/bin/bash
# Generated commands for 20 Gutenberg stories
# Usage: ./run_gutenberg_videos.sh

# Story 1: The Call of Cthulhu - Male narrator, cosmic horror
python generate_video.py \
  --text resources/stories/gutenberg/01_the_call_of_cthulhu.txt \
  --mode slides \
  --art-reference resources/styles/vg_converted.jpg \
  --narration-style "Deep gravelly baritone with measured pacing, building dread, academic narrator" \
  --audio-reference resources/voices/sam-deep.mp3 \
  --output-dir output/gutenberg/01_call_of_cthulhu \
  --test

# Story 2: The Tell-Tale Heart - Male narrator, psychological horror
python generate_video.py \
  --text resources/stories/gutenberg/02_the_tell_tale_heart.txt \
  --mode slides \
  --art-reference resources/styles/picasso.jpeg \
  --narration-style "Intense whispered urgency building to mania, paranoid confession" \
  --audio-reference resources/voices/nathan.mp3 \
  --output-dir output/gutenberg/02_tell_tale_heart \
  --test

# Story 3: The Cask of Amontillado - Male narrator, revenge thriller
python generate_video.py \
  --text resources/stories/gutenberg/03_the_cask_of_amontillado.txt \
  --mode slides \
  --art-reference resources/styles/roman-mural.jpg \
  --narration-style "Cultured aristocratic with cold satisfaction, smooth menace" \
  --audio-reference resources/voices/nigel.mp3 \
  --output-dir output/gutenberg/03_cask_amontillado \
  --test

# Story 4: The Gift of the Magi - Female narrator, heartwarming drama
python generate_video.py \
  --text resources/stories/gutenberg/04_the_gift_of_the_magi.txt \
  --mode slides \
  --art-reference resources/styles/broadsroke.webp \
  --narration-style "Warm maternal with gentle humor, tender and playful" \
  --audio-reference resources/voices/linda-story.mp3 \
  --output-dir output/gutenberg/04_gift_magi \
  --test

# Story 5: The Yellow Wallpaper - Female narrator, psychological horror
python generate_video.py \
  --text resources/stories/gutenberg/05_the_yellow_wallpaper.txt \
  --mode slides \
  --art-reference resources/styles/vg_converted.jpg \
  --narration-style "Fragile diary-intimate deteriorating to frantic, Victorian woman unraveling" \
  --audio-reference resources/voices/celeste-bedtime.mp3 \
  --output-dir output/gutenberg/05_yellow_wallpaper \
  --test

# Story 6: The Fall of the House of Usher - Male narrator, gothic horror
python generate_video.py \
  --text resources/stories/gutenberg/06_the_fall_of_the_house_of_usher.txt \
  --mode slides \
  --art-reference resources/styles/roman.jpg \
  --narration-style "Melancholic literary with mounting unease, cultured but disturbed" \
  --audio-reference resources/voices/bill_calm.mp3 \
  --output-dir output/gutenberg/06_fall_house_usher \
  --test

# Story 7: An Occurrence at Owl Creek Bridge - Male narrator, war thriller
python generate_video.py \
  --text resources/stories/gutenberg/07_an_occurrence_at_owl_creek_bridge.txt \
  --mode slides \
  --art-reference resources/styles/picasso.jpeg \
  --narration-style "Calm documentary shifting to desperate hope, military precision" \
  --audio-reference resources/voices/chris-slow.mp3 \
  --output-dir output/gutenberg/07_owl_creek_bridge \
  --test

# Story 8: The Masque of the Red Death - Male narrator, allegorical horror
python generate_video.py \
  --text resources/stories/gutenberg/08_the_masque_of_the_red_death.txt \
  --mode slides \
  --art-reference resources/styles/roman-mural.jpg \
  --narration-style "Theatrical grandiose narrator becoming solemn, dark fairy tale quality" \
  --audio-reference resources/voices/lock-slow.mp3 \
  --output-dir output/gutenberg/08_masque_red_death \
  --test

# Story 9: Bartleby the Scrivener - Male narrator, existential drama
python generate_video.py \
  --text resources/stories/gutenberg/09_bartleby_the_scrivener.txt \
  --mode slides \
  --art-reference resources/styles/broadsroke.webp \
  --narration-style "Bewildered professional growing compassionate, confused but decent lawyer" \
  --audio-reference resources/voices/maurice-meditate.mp3 \
  --output-dir output/gutenberg/09_bartleby_scrivener \
  --test

# Story 10: The Dunwich Horror - Male narrator, cosmic horror
python generate_video.py \
  --text resources/stories/gutenberg/10_the_dunwich_horror.txt \
  --mode slides \
  --art-reference resources/styles/vg_converted.jpg \
  --narration-style "New England folksy elder with growing alarm, local historian" \
  --audio-reference resources/voices/sam-deep.mp3 \
  --output-dir output/gutenberg/10_dunwich_horror \
  --test

# Story 11: The Colour Out of Space - Male narrator, sci-fi horror
python generate_video.py \
  --text resources/stories/gutenberg/11_the_colour_out_of_space.txt \
  --mode slides \
  --art-reference resources/styles/picasso.jpeg \
  --narration-style "Scientific investigator becoming increasingly disturbed, rational researcher" \
  --audio-reference resources/voices/nathan.mp3 \
  --output-dir output/gutenberg/11_colour_out_of_space \
  --test

# Story 12: The Shadow Over Innsmouth - Male narrator, cosmic horror
python generate_video.py \
  --text resources/stories/gutenberg/12_the_shadow_over_innsmouth.txt \
  --mode slides \
  --art-reference resources/styles/roman.jpg \
  --narration-style "Young curious traveler becoming terrified then transformed, tourist to horror" \
  --audio-reference resources/voices/nigel.mp3 \
  --output-dir output/gutenberg/12_shadow_innsmouth \
  --test

# Story 13: The Monkey's Paw - Male narrator, supernatural horror
python generate_video.py \
  --text resources/stories/gutenberg/13_the_monkeys_paw.txt \
  --mode slides \
  --art-reference resources/styles/roman-mural.jpg \
  --narration-style "Warm British fireside storyteller, cozy ghost story framing" \
  --audio-reference resources/voices/bill_calm.mp3 \
  --output-dir output/gutenberg/13_monkeys_paw \
  --test

# Story 14: The Shunned House - Male narrator, gothic horror
python generate_video.py \
  --text resources/stories/gutenberg/14_the_shunned_house.txt \
  --mode slides \
  --art-reference resources/styles/broadsroke.webp \
  --narration-style "Academic nephew with antiquarian enthusiasm dimming to dread" \
  --audio-reference resources/voices/chris-slow.mp3 \
  --output-dir output/gutenberg/14_shunned_house \
  --test

# Story 15: The Red Room - Male narrator, supernatural horror
python generate_video.py \
  --text resources/stories/gutenberg/15_the_red_room.txt \
  --mode slides \
  --art-reference resources/styles/vg_converted.jpg \
  --narration-style "Young arrogant skeptic humbled by terror, confidence breaking" \
  --audio-reference resources/voices/lock-slow.mp3 \
  --output-dir output/gutenberg/15_red_room \
  --test

# Story 16: The Lurking Fear (file named 18 in directory) - Male narrator, gothic horror
python generate_video.py \
  --text resources/stories/gutenberg/18_the_lurking_fear.txt \
  --mode slides \
  --art-reference resources/styles/picasso.jpeg \
  --narration-style "Obsessive monster-hunter pushing limits, determined investigator" \
  --audio-reference resources/voices/maurice-meditate.mp3 \
  --output-dir output/gutenberg/16_lurking_fear \
  --test

# Story 17: A Pail of Air (file named 17 in directory) - Female narrator, post-apocalyptic sci-fi
python generate_video.py \
  --text resources/stories/gutenberg/17_a_pail_of_air.txt \
  --mode slides \
  --art-reference resources/styles/roman.jpg \
  --narration-style "Young child narrator with wonder and resilience, innocent hope" \
  --audio-reference resources/voices/maysie.mp3 \
  --output-dir output/gutenberg/17_pail_air \
  --test

# Story 18: 2BR02B - Male narrator, dystopian satire
python generate_video.py \
  --text resources/stories/gutenberg/19_2br02b.txt \
  --mode slides \
  --art-reference resources/styles/roman-mural.jpg \
  --narration-style "Dry sardonic detachment with undercurrent of despair, dark comedy" \
  --audio-reference resources/voices/sam-deep.mp3 \
  --output-dir output/gutenberg/18_2br02b \
  --test

# Story 19: The Eyes Have It - Male/Female narrator, comedic sci-fi
python generate_video.py \
  --text resources/stories/gutenberg/20_the_eyes_have_it.txt \
  --mode slides \
  --art-reference resources/styles/broadsroke.webp \
  --narration-style "Paranoid conspiracy theorist played for comedy, escalating absurdity" \
  --audio-reference resources/voices/amara.mp3 \
  --output-dir output/gutenberg/19_eyes_have_it \
  --test

# Story 20: First Poe Collection - Male narrator, horror anthology
# Note: This file doesn't exist yet in the directory, but included per CSV
# python generate_video.py \
#   --text resources/stories/gutenberg/20_poe_collection.txt \
#   --mode slides \
#   --art-reference resources/styles/vg_converted.jpg \
#   --narration-style "Desperate prisoner clinging to reason, fighting panic" \
#   --audio-reference resources/voices/nathan.mp3 \
#   --output-dir output/gutenberg/20_poe_collection \
#   --test

echo "All commands generated successfully!"
echo "Note: Story 20 (Poe Collection) is commented out as the text file doesn't exist yet"
