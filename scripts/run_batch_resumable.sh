#!/bin/bash
# Resumable Batch Runner - Run with automatic resume on interruption
#
# Usage:
#   ./run_batch_resumable.sh [batch_script.sh]
#
# Features:
#   - Automatic resume after interruption (CTRL+C, network loss, etc.)
#   - Skips completed stories instantly
#   - Retries API errors automatically
#   - Shows progress (7/20 complete)
#   - Saves state to batch_progress_*.json
#
# Example:
#   ./run_batch_resumable.sh run_gutenberg_videos.sh

BATCH_SCRIPT="${1:-run_gutenberg_videos.sh}"

if [ ! -f "$BATCH_SCRIPT" ]; then
    echo "Error: Batch script not found: $BATCH_SCRIPT"
    echo ""
    echo "Usage: $0 [batch_script.sh]"
    exit 1
fi

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                      RESUMABLE BATCH PROCESSOR                                ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Batch script: $BATCH_SCRIPT"
echo ""
echo "Features:"
echo "  ✓ Automatic resume after interruption"
echo "  ✓ Skips completed stories"
echo "  ✓ Retries API errors (3 attempts with backoff)"
echo "  ✓ Graceful shutdown (CTRL+C)"
echo "  ✓ Progress tracking"
echo ""
echo "Press CTRL+C to stop gracefully after current job"
echo "Run this script again to resume from where you left off"
echo ""
echo "Starting in 3 seconds..."
sleep 3

python scripts/batch_manager.py "$BATCH_SCRIPT"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "Batch processing complete or interrupted"
echo ""
echo "To resume if interrupted:"
echo "  ./run_batch_resumable.sh $BATCH_SCRIPT"
echo ""
echo "To start fresh (clear progress):"
echo "  rm batch_progress_*.json"
echo "  ./run_batch_resumable.sh $BATCH_SCRIPT"
echo "═══════════════════════════════════════════════════════════════════════════════"
