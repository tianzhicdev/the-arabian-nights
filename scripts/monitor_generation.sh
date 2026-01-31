#!/bin/bash
# Monitor scene generation and report when complete

LOG_FILE="$1"
OUTPUT_DIR="$2"

if [ -z "$LOG_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <log_file> <output_dir>"
    exit 1
fi

echo "Monitoring generation..."
echo "Log: $LOG_FILE"
echo "Output: $OUTPUT_DIR"
echo ""

# Wait for process to complete
while ps aux | grep -q "[g]enerate_scenes_ollama.py"; do
    sleep 30
done

# Check if generation completed successfully
if [ -f "$OUTPUT_DIR/scenes.json" ]; then
    SCENE_COUNT=$(jq '.scenes | length' "$OUTPUT_DIR/scenes.json" 2>/dev/null || echo "0")
    echo ""
    echo "=========================================="
    echo "✓ GENERATION COMPLETE"
    echo "=========================================="
    echo "Scenes generated: $SCENE_COUNT"
    echo "Output: $OUTPUT_DIR"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 "$LOG_FILE"
else
    echo ""
    echo "=========================================="
    echo "✗ GENERATION FAILED"
    echo "=========================================="
    echo ""
    echo "Last 50 lines of log:"
    tail -50 "$LOG_FILE"
fi
