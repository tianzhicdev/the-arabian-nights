#!/bin/bash

# Podcast Audio Generator - Setup and Run Script

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
GENERATOR_SCRIPT="$PROJECT_ROOT/scripts/generate_podcast_audio.py"

echo "=== Podcast Audio Generator Setup ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing dependencies..."
pip install --quiet requests python-dotenv

echo "✓ All dependencies installed"
echo ""

# Run the audio generator
echo "=== Running Audio Generator ==="
python "$GENERATOR_SCRIPT" "$@"

echo ""
echo "=== Done ==="
