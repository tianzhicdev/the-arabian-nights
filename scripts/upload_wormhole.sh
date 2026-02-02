#!/bin/bash
#
# Upload all pending videos to YouTube channel @wornhole-news
# Each video is scheduled 24 hours apart, starting at 2pm NY time.
#
# Usage:
#   ./scripts/upload_wormhole.sh
#
# Cron example (run daily at 3am):
#   0 3 * * * /path/to/scripts/upload_wormhole.sh
#

# Configuration - DIFFERENT from main channel
UPLOAD_QUEUE="$HOME/upload_queue_wormhole"
TOKEN_FILE="youtube_token_wormhole.pickle"  # Different token for different channel

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$HOME/upload_logs"
LOG_FILE="$LOG_DIR/upload_wormhole_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$UPLOAD_QUEUE"

# Log function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "YouTube Upload - @wornhole-news"
log "=========================================="
log "Queue directory: $UPLOAD_QUEUE"
log "Token file: $TOKEN_FILE"
log "Project root: $PROJECT_ROOT"
log "Log file: $LOG_FILE"

# Check if queue directory exists
if [ ! -d "$UPLOAD_QUEUE" ]; then
    log "Creating upload queue directory: $UPLOAD_QUEUE"
    mkdir -p "$UPLOAD_QUEUE"
fi

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    log "Activated virtual environment: .venv"
elif [ -d "venv" ]; then
    source venv/bin/activate
    log "Activated virtual environment: venv"
else
    log "WARNING: No virtual environment found, using system Python"
fi

# Load environment secrets if available
if [ -f ".env.secrets" ]; then
    source .env.secrets
    log "Loaded environment secrets"
fi

# Upload all pending videos with the wormhole token
log "Starting upload process..."
python "$PROJECT_ROOT/src/upload/upload_episode_with_metadata.py" \
    --all \
    --queue-dir "$UPLOAD_QUEUE" \
    --token-file "$PROJECT_ROOT/credentials/$TOKEN_FILE" \
    2>&1 | tee -a "$LOG_FILE"

# Check exit code
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -eq 0 ]; then
    log "Upload process completed successfully!"
else
    log "Upload process completed with errors (exit code: $EXIT_CODE)"
fi

log "=========================================="
log "Log saved to: $LOG_FILE"
exit $EXIT_CODE
