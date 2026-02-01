#!/bin/bash
#
# Upload all pending videos to YouTube with scheduled publishing.
# Each video is scheduled 24 hours apart, starting at 2pm NY time.
#
# Usage:
#   ./scripts/upload_next_episode.sh
#
# Cron example (run daily at 3am):
#   0 3 * * * /path/to/scripts/upload_next_episode.sh
#

# Configuration
UPLOAD_QUEUE="$HOME/upload_queue_main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$HOME/upload_logs"
LOG_FILE="$LOG_DIR/upload_$(date +%Y%m%d_%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "YouTube Upload Queue Processor"
log "=========================================="
log "Queue directory: $UPLOAD_QUEUE"
log "Project root: $PROJECT_ROOT"
log "Log file: $LOG_FILE"

# Check if queue directory exists
if [ ! -d "$UPLOAD_QUEUE" ]; then
    log "ERROR: Upload queue directory not found: $UPLOAD_QUEUE"
    exit 1
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

# Upload all pending videos
log "Starting upload process..."
python "$PROJECT_ROOT/src/upload/upload_episode_with_metadata.py" --all --queue-dir "$UPLOAD_QUEUE" 2>&1 | tee -a "$LOG_FILE"

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
