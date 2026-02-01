#!/bin/bash
#
# Wrapper script for running video generation with optimized Ollama settings
# Automatically ensures Ollama is running with parallel processing enabled
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Arabian Nights Video Generation ===${NC}"
echo "Ensuring Ollama is configured with optimal settings..."

# Add ollama to PATH
export PATH=$HOME/bin:$PATH

# Optimized Ollama environment variables
export OLLAMA_NUM_PARALLEL=8          # Allow 8 concurrent requests (default is 1-4)
export OLLAMA_MAX_LOADED_MODELS=1      # Keep only one model in memory for consistency

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Starting Ollama server with optimized settings...${NC}"
    echo "  OLLAMA_NUM_PARALLEL=8 (8x parallel processing)"
    echo "  OLLAMA_MAX_LOADED_MODELS=1 (single model for consistency)"

    # Start Ollama in background
    OLLAMA_NUM_PARALLEL=8 OLLAMA_MAX_LOADED_MODELS=1 nohup ollama serve > ~/ollama.log 2>&1 &

    # Wait for Ollama to be ready
    echo "Waiting for Ollama to start..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama is ready${NC}"
            break
        fi
        sleep 1
    done
else
    echo -e "${GREEN}✓ Ollama is already running${NC}"

    # Check if it has the right environment (best effort - can't change running process)
    if [ ! -z "$1" ] && [ "$1" != "--help" ]; then
        echo -e "${YELLOW}Note: Ollama was already running. Optimized settings may not be applied.${NC}"
        echo "  To ensure optimal performance, restart Ollama:"
        echo "  killall ollama && OLLAMA_NUM_PARALLEL=8 OLLAMA_MAX_LOADED_MODELS=1 ollama serve &"
    fi
fi

# Check GPU availability (for monitoring purposes)
echo ""
echo "GPU Information:"
if command -v system_profiler &> /dev/null; then
    # macOS
    system_profiler SPDisplaysDataType | grep -E "Chipset Model|VRAM|Metal" | head -3
elif command -v nvidia-smi &> /dev/null; then
    # Linux with NVIDIA
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "  GPU detection not available"
fi

echo ""
echo -e "${GREEN}=== Running Video Generation ===${NC}"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the actual command
if [ "$1" == "--help" ] || [ -z "$1" ]; then
    python generate_video.py --help
else
    # Run with all passed arguments
    python generate_video.py "$@"
fi
