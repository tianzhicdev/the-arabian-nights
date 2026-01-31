#!/bin/bash
source .env.secrets
export OPENROUTER_API_KEY=$OPEN_ROUTER_API
export OPENAI_API_KEY=$OPEN_AI_API
python3 scripts/generate_video.py "$@"
