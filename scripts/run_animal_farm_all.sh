#!/bin/bash
#
# Run all Animal Farm episodes concurrently
# Uses consolidated JSON files with consistent objects
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Animal Farm - Concurrent Video Generation ===${NC}"
echo "Episodes: 2-10 (9 episodes total)"
echo "Voice: maurice-meditate.mp3"
echo "Art Style: vg_converted.jpg (Van Gogh style)"
echo "Mode: slides"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Configuration
VOICE="resources/voices/maurice-meditate.mp3"
ART_STYLE="resources/styles/vg_converted.jpg"
MODE="slides"
BASE_DIR="resources/stories/gutenberg"
OUTPUT_BASE="output/animal_farm"

# Ensure output directory exists
mkdir -p "$OUTPUT_BASE"

# Function to run single episode
run_episode() {
    local episode_num=$1
    local scene_file="${BASE_DIR}/animal_farm_e${episode_num}-consolidated.json"
    local output_dir="${OUTPUT_BASE}/episode_${episode_num}"

    echo -e "${BLUE}[Episode ${episode_num}] Starting...${NC}"

    python generate_video.py \
        --scenes "$scene_file" \
        --mode "$MODE" \
        --art-reference "$ART_STYLE" \
        --skip-audio \
        --output-dir "$output_dir" \
        2>&1 | sed "s/^/[E${episode_num}] /"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[Episode ${episode_num}] ✓ Complete${NC}"
    else
        echo -e "${YELLOW}[Episode ${episode_num}] ✗ Failed${NC}"
    fi
}

# Export function for parallel execution
export -f run_episode
export VOICE ART_STYLE MODE BASE_DIR OUTPUT_BASE BLUE GREEN YELLOW NC

echo -e "${YELLOW}Starting concurrent generation...${NC}"
echo ""

# Run all episodes in parallel using background jobs
for ep in {2..10}; do
    run_episode $ep &
done

# Wait for all background jobs to complete
wait

echo ""
echo -e "${GREEN}=== All Episodes Complete ===${NC}"
echo ""

# Summary
echo "Generated videos:"
for ep in {2..10}; do
    video_file="${OUTPUT_BASE}/episode_${ep}/"*.mp4
    if ls $video_file 1> /dev/null 2>&1; then
        size=$(du -h $video_file 2>/dev/null | cut -f1)
        echo -e "  ${GREEN}✓${NC} Episode ${ep}: $video_file ($size)"
    else
        echo -e "  ${YELLOW}✗${NC} Episode ${ep}: Not found"
    fi
done

echo ""
echo "Total output size: $(du -sh $OUTPUT_BASE | cut -f1)"
