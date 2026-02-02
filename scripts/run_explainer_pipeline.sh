#!/bin/bash
# Run Explainer Video Pipeline
# Creates educational explainer videos from trending news topics

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/.deps_installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    # Install additional deps for explainer pipeline
    pip install kokoro-onnx soundfile
    touch .venv/.deps_installed
fi

# Load environment
if [ -f ".env.secrets" ]; then
    export $(grep -v '^#' .env.secrets | xargs)
fi

# Show help
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Explainer Video Pipeline"
    echo ""
    echo "Usage:"
    echo "  $0                          # Run with topic approval"
    echo "  $0 --auto-approve           # Run fully automatic"
    echo "  $0 --continue <hash>        # Continue from approval"
    echo "  $0 --category geopolitics   # Search specific category"
    echo ""
    echo "Options:"
    echo "  -c, --category   News category (geopolitics, tech, economics)"
    echo "  -m, --minutes    Target video length (default: 8)"
    echo "  -a, --auto-approve  Skip topic approval step"
    echo "  -k, --continue   Continue from topic hash"
    echo "  --voice          Kokoro voice ID (default: am_onyx)"
    echo "  --speed          Voice speed (default: 0.75)"
    echo ""
    exit 0
fi

# Run pipeline
echo "Starting Explainer Video Pipeline..."
python -m src.pipelines.explainer_pipeline "$@"
