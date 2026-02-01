#!/bin/bash
#
# Automated audiobook pipeline runner
# Creates venv, installs deps, and runs the Python pipeline
#
# Usage:
#   ./scripts/audiobook_pipeline_auto.sh <text_file_or_url> [voice_id] [options]
#
# Examples:
#   # With ElevenLabs (paid)
#   ./scripts/audiobook_pipeline_auto.sh resources/stories/book.txt JBFqnCBsd6RMkjVDRZzb
#
#   # With Coqui TTS (free, local)
#   ./scripts/audiobook_pipeline_auto.sh resources/stories/book.txt --coqui
#
# Options are passed through to the Python script:
#   --coqui          Use Coqui TTS (local, free) instead of ElevenLabs
#   --coqui-model    Coqui model (default: tts_models/en/ljspeech/vits)
#   --skip-queue     Skip queueing for YouTube upload
#   --base-dir DIR   Custom output directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
LOG_DIR="$PROJECT_ROOT/output/logs"

cd "$PROJECT_ROOT"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <text_file_or_url> [voice_id] [options]"
    echo ""
    echo "Examples:"
    echo "  # With ElevenLabs (paid)"
    echo "  $0 resources/stories/book.txt JBFqnCBsd6RMkjVDRZzb"
    echo ""
    echo "  # With Coqui TTS (free, local)"
    echo "  $0 resources/stories/book.txt --coqui"
    echo ""
    echo "Options:"
    echo "  --coqui          Use Coqui TTS (local, free) instead of ElevenLabs"
    echo "  --coqui-model M  Coqui model (default: tts_models/en/ljspeech/vits)"
    echo "  --skip-queue     Skip queueing for YouTube upload"
    echo "  --base-dir DIR   Custom output directory (default: output/audiobook_pipeline)"
    exit 1
fi

SOURCE_FILE="$1"
shift  # Remove first arg

# Check if using --coqui mode (no voice_id needed)
USE_COQUI=false
VOICE_ID=""
EXTRA_ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--coqui" ]; then
        USE_COQUI=true
    fi
done

if [ "$USE_COQUI" = true ]; then
    # Coqui mode: all remaining args are options
    EXTRA_ARGS=("$@")
else
    # ElevenLabs mode: first arg is voice_id
    if [ $# -lt 1 ]; then
        echo "Error: voice_id required unless --coqui is specified"
        exit 1
    fi
    VOICE_ID="$1"
    shift
    EXTRA_ARGS=("$@")
fi

# Create slug from source filename for log
SOURCE_BASENAME=$(basename "$SOURCE_FILE" .txt)
SLUG=$(echo "$SOURCE_BASENAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_-')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/${SLUG}_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "=============================================="
log "Audiobook Pipeline Runner"
log "=============================================="
log "Source: $SOURCE_FILE"
if [ "$USE_COQUI" = true ]; then
    log "TTS Engine: Coqui TTS (local, free)"
else
    log "TTS Engine: ElevenLabs"
    log "Voice ID: $VOICE_ID"
fi
log "Options: ${EXTRA_ARGS[*]}"
log "Log file: $LOG_FILE"
log "=============================================="

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
if [ -f "requirements.txt" ]; then
    log "Installing dependencies from requirements.txt..."
    pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
else
    log "No requirements.txt found, installing core dependencies..."
    pip install -q requests python-dotenv 2>&1 | tee -a "$LOG_FILE"
fi

# Load secrets
if [ -f ".env.secrets" ]; then
    log "Loading environment secrets..."
    set -a
    source .env.secrets
    set +a
fi

# Run the pipeline
log ""
log "Starting audiobook pipeline..."
if [ "$USE_COQUI" = true ]; then
    python src/pipelines/audiobook_pipeline_auto.py "$SOURCE_FILE" "${EXTRA_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
else
    python src/pipelines/audiobook_pipeline_auto.py "$SOURCE_FILE" "$VOICE_ID" "${EXTRA_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
fi

EXIT_CODE=${PIPESTATUS[0]}

log ""
if [ $EXIT_CODE -eq 0 ]; then
    log "Pipeline completed successfully!"
else
    log "Pipeline failed with exit code $EXIT_CODE"
fi

log "Log saved to: $LOG_FILE"
exit $EXIT_CODE
