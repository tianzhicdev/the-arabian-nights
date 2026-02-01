#!/usr/bin/env python3
"""
Test script for comparing video generation with and without style reference images.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai_client import OpenAIClient


def download_video(content_url: str, output_path: str, api_key: str):
    """Download video from Sora content URL."""
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(content_url, headers=headers, timeout=120)
    response.raise_for_status()

    with open(output_path, 'wb') as f:
        f.write(response.content)
    print(f"    Downloaded to: {output_path}")


def main():
    # Load test scenes
    project_root = Path(__file__).parent.parent
    scenes_file = project_root / "test_style_consistency.json"

    with open(scenes_file, 'r') as f:
        data = json.load(f)

    episode = data['episode']
    scenes = data['scenes']

    # Reference image path
    reference_image = project_root / "resources/style_references/watercolor_reference_1280x720.jpg"

    # Output directory
    output_dir = project_root / "output/style_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize client
    client = OpenAIClient()

    print("=" * 80)
    print("STYLE REFERENCE TEST")
    print("=" * 80)
    print(f"Episode: {episode['title']}")
    print(f"Art Style: {episode['art_style']}")
    print(f"Reference Image: {reference_image}")
    print(f"Total Scenes: {len(scenes)}")
    print("=" * 80)

    # Test with first scene only (for quick testing)
    scene = scenes[0]

    # Build prompt
    prompt = f"{scene['video_description']}. Camera: {scene['camera_style']}. Style: {episode['art_style']}"
    # Trim to 500 chars max
    if len(prompt) > 500:
        prompt = prompt[:497] + "..."

    print(f"\nScene: {scene['scene_id']}")
    print(f"Prompt ({len(prompt)} chars): {prompt}")
    print()

    # TEST 1: Generate WITHOUT reference image
    print("=" * 80)
    print("TEST 1: Generating video WITHOUT reference image (baseline)")
    print("=" * 80)
    try:
        content_url = client.generate_video(
            prompt=prompt,
            model="sora-2",
            seconds=4,
            size="1280x720",
            input_reference=None
        )

        # Download video
        output_file = output_dir / f"{scene['scene_id']}_no_reference.mp4"
        download_video(content_url, str(output_file), client.api_key)
        print(f"✓ Test 1 completed: {output_file}")

    except Exception as e:
        print(f"✗ Test 1 failed: {e}")

    print()

    # TEST 2: Generate WITH reference image
    print("=" * 80)
    print("TEST 2: Generating video WITH reference image")
    print("=" * 80)
    print(f"Reference: {reference_image}")
    print()
    try:
        content_url = client.generate_video(
            prompt=prompt,
            model="sora-2",
            seconds=4,
            size="1280x720",
            input_reference=str(reference_image)
        )

        # Download video
        output_file = output_dir / f"{scene['scene_id']}_with_reference.mp4"
        download_video(content_url, str(output_file), client.api_key)
        print(f"✓ Test 2 completed: {output_file}")

    except Exception as e:
        print(f"✗ Test 2 failed: {e}")

    print()
    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print()
    print("Compare the videos:")
    print(f"  - {output_dir}/scene_001_no_reference.mp4 (baseline)")
    print(f"  - {output_dir}/scene_001_with_reference.mp4 (with style reference)")
    print()


if __name__ == "__main__":
    main()
