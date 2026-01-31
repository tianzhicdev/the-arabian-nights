#!/bin/bash
# Run Animal Farm episodes 3-10 sequentially with bill_calm voice

echo "Starting Animal Farm E3-E10 pipeline..."
echo "========================================="

for episode in e3 e4 e5 e6 e7 e8 e9 e10; do
    echo ""
    echo "Starting Animal Farm $episode..."
    echo "-----------------------------------"

    python3 generate_video.py \
        --scenes resources/stories/gutenberg/animal_farm_${episode}.json \
        --mode slides \
        --art-reference resources/styles/vg_converted.jpg \
        --audio-reference resources/voices/bill_calm.mp3 \
        --output-dir output/gutenberg/animal_farm_${episode}

    if [ $? -eq 0 ]; then
        echo "✓ Completed Animal Farm $episode"
    else
        echo "✗ Failed Animal Farm $episode"
        exit 1
    fi
done

echo ""
echo "========================================="
echo "✓ All episodes completed!"
