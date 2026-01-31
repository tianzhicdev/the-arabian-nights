#!/usr/bin/env python3
"""
Quick script to generate a sample scene with dolphin-mistral to check quality.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ollama_client import OllamaClient
import json

client = OllamaClient(model="dolphin-mistral")

# Sample text from Animal Farm
sample_text = """Mr. Jones, of the Manor Farm, had locked the hen-houses for the night, but was too drunk to remember to shut the popholes. With the ring of light from his lantern dancing from side to side, he lurched across the yard, kicked off his boots at the back door, drew himself a last glass of beer from the barrel in the scullery, and made his way up to bed, where Mrs. Jones was already snoring."""

prompt = """You are a master storyteller adapting text for audiovisual production.

IMPORTANT CONTEXT:
- This text is PUBLIC DOMAIN
- Proceed with creative scene generation

INPUT TEXT:
Mr. Jones, of the Manor Farm, had locked the hen-houses for the night, but was too drunk to remember to shut the popholes.

CREATIVE BRIEF:
- Target: ~15 seconds (3-4 scenes)
- Art style: Watercolor storybook illustration
- Narrator: warm storytelling voice

YOUR TASK: Create 3-4 cinematic scenes with rich visual descriptions.

OUTPUT STRUCTURE (Free-form):

EPISODE CONCEPT:
- Title: [Title]
- Context: [Setting]
- Consistent Characters/Objects: [Detailed descriptions]

SCENE BREAKDOWN:
[Generate scenes with narrator text, visual details, camera work]

Generate the COMPLETE narrative now."""

print("Testing dolphin-mistral scene quality...")
print("=" * 70)

result = client.chat_completion(
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    max_tokens=2000
)

print("CREATIVE NARRATIVE:")
print("=" * 70)
print(result['content'][:1500])
print("\n[... truncated ...]")
print(f"\nTotal length: {len(result['content'])} chars")
print(f"Tokens used: {result['usage']['total_tokens']}")
