#!/bin/bash
#
# Generic upload script for YouTube uploads from queue
# Scans ~/upload_queue_main/ for unuploaded videos and uploads them by timestamp order
#
# Usage:
#   ./scripts/upload_next_episode.sh
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

# Check if queue directory exists
if [ ! -d "$UPLOAD_QUEUE" ]; then
    log "ERROR: Upload queue directory not found: $UPLOAD_QUEUE"
    exit 1
fi

# Activate virtual environment
cd "$PROJECT_ROOT"
if [ -d ".venv" ]; then
    source .venv/bin/activate
    log "Activated virtual environment: .venv"
elif [ -d "venv" ]; then
    source venv/bin/activate
    log "Activated virtual environment: venv"
else
    log "WARNING: No virtual environment found, using system Python"
fi

# Function to extract creation_timestamp from metadata.json
get_timestamp() {
    local metadata_file="$1"
    python3 -c "
import json
import sys
try:
    with open('$metadata_file') as f:
        data = json.load(f)
        print(data.get('creation_timestamp', 0))
except:
    print(0)
"
}

# Function to check if video is uploaded
is_uploaded() {
    local metadata_file="$1"
    python3 -c "
import json
import sys
try:
    with open('$metadata_file') as f:
        data = json.load(f)
        print('true' if data.get('uploaded', False) else 'false')
except:
    print('false')
"
}

log "Scanning queue for unuploaded videos..."

# Find all metadata.json files that haven't been uploaded
declare -a pending_uploads
while IFS= read -r -d '' metadata_file; do
    dir=$(dirname "$metadata_file")

    # Check if video is already uploaded
    uploaded=$(is_uploaded "$metadata_file")

    if [ "$uploaded" = "false" ]; then
        timestamp=$(get_timestamp "$metadata_file")
        log "  Found: $(basename "$dir") (timestamp: $timestamp)"
        pending_uploads+=("$timestamp:$dir")
    fi
done < <(find "$UPLOAD_QUEUE" -name "metadata.json" -type f -print0)

# Check if any videos found
if [ ${#pending_uploads[@]} -eq 0 ]; then
    log "No videos pending upload"
    log "=========================================="
    exit 0
fi

log "Found ${#pending_uploads[@]} video(s) pending upload"

# Sort by timestamp (oldest first)
IFS=$'\n' sorted_uploads=($(sort -n <<<"${pending_uploads[*]}"))
unset IFS

# Get the oldest video
oldest_entry="${sorted_uploads[0]}"
upload_dir="${oldest_entry#*:}"

log "Uploading oldest video from: $(basename "$upload_dir")"
log "Directory: $upload_dir"

# Upload using Python script
log "Running upload script..."
python "$PROJECT_ROOT/src/upload/upload_episode_with_metadata.py" "$upload_dir" 2>&1 | tee -a "$LOG_FILE"

# Check exit code
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log "Upload successful!"
    log "=========================================="
    exit 0
else
    log "Upload failed!"
    log "=========================================="
    exit 1
fi
