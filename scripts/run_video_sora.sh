#!/bin/bash

# Wrapper script for Sora video generation
# Properly handles environment variables

# Load secrets
if [ -f .env.secrets ]; then
    source .env.secrets
else
    echo "Error: .env.secrets not found"
    exit 1
fi

# Export API keys
export OPENAI_API_KEY=$OPEN_AI_API
export OPENROUTER_API_KEY=$OPEN_ROUTER_API

# Verify keys are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPEN_AI_API not set in .env.secrets"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "Error: OPEN_ROUTER_API not set in .env.secrets"
    exit 1
fi

# Run the Sora video generator
python3 scripts/generate_video_sora.py "$@"
