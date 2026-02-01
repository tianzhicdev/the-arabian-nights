#!/usr/bin/env python3
"""
Two-Phase Style-Consistent Video Generation Pipeline Test

Phase 1: Generate scene-specific images with FLUX Redux (style from reference)
Phase 2: Generate videos from those images with Sora
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.flux_client import FluxReduxClient
from openai_client import OpenAIClient


def download_image(url: str, output_path: str):
    """Download image from URL to local file."""
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(response.content)
    print(f"    Downloaded to: {output_path}")


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

    # Style reference image (your watercolor.jpg)
    style_reference = project_root / "resources/style_references/watercolor_reference_1280x720.jpg"

    # Output directories
    output_dir = project_root / "output/two_phase_test"
    images_dir = output_dir / "phase1_images"
    videos_dir = output_dir / "phase2_videos"

    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Initialize clients
    flux_client = FluxReduxClient()
    sora_client = OpenAIClient()

    print("=" * 80)
    print("TWO-PHASE STYLE-CONSISTENT VIDEO GENERATION TEST")
    print("=" * 80)
    print(f"Episode: {episode['title']}")
    print(f"Style Reference: {style_reference}")
    print(f"Total Scenes: {len(scenes)}")
    print()
    print("Pipeline:")
    print("  Phase 1: FLUX Redux → Generate scene images with watercolor style")
    print("  Phase 2: Sora → Generate videos from styled images")
    print("=" * 80)
    print()

    # Test with first scene only for quick validation
    scene = scenes[0]
    scene_id = scene['scene_id']

    print("=" * 80)
    print(f"PROCESSING SCENE: {scene_id}")
    print("=" * 80)
    print(f"Description: {scene['video_description'][:100]}...")
    print()

    # =========================================================================
    # PHASE 1: Generate Scene-Specific Image with FLUX Redux
    # =========================================================================
    print("─" * 80)
    print("PHASE 1: Generating scene-specific image with watercolor style")
    print("─" * 80)

    # Build a clean prompt for image generation (content only, style handled by reference)
    image_prompt = scene['video_description']

    # Trim if too long (FLUX can handle longer prompts than Sora)
    if len(image_prompt) > 1000:
        image_prompt = image_prompt[:997] + "..."

    print(f"Image Prompt: {image_prompt}")
    print()

    try:
        # Generate image with style from watercolor reference
        scene_image_url = flux_client.generate_with_style_reference(
            prompt=image_prompt,
            style_reference_url=str(style_reference),
            aspect_ratio="16:9",  # Matches 1280x720
            num_inference_steps=28,
            guidance=3.0
        )

        # Download the generated image
        scene_image_path_temp = images_dir / f"{scene_id}_styled_temp.png"
        download_image(scene_image_url, str(scene_image_path_temp))

        # Resize to exactly 1280x720 for Sora (FLUX may generate at slightly different resolution)
        scene_image_path = images_dir / f"{scene_id}_styled.png"
        import subprocess
        subprocess.run([
            "sips", "-z", "720", "1280",
            str(scene_image_path_temp),
            "--out", str(scene_image_path)
        ], check=True, capture_output=True)

        # Remove temp file
        scene_image_path_temp.unlink()

        print(f"✓ Phase 1 Complete: {scene_image_path} (resized to 1280x720)")
        print()

    except Exception as e:
        print(f"✗ Phase 1 Failed: {e}")
        return

    # =========================================================================
    # PHASE 2: Generate Video from Styled Image with Sora
    # =========================================================================
    print("─" * 80)
    print("PHASE 2: Generating video from styled image")
    print("─" * 80)

    # Build video prompt (scene description + camera + style hints)
    video_prompt = f"{scene['video_description']}. Camera: {scene['camera_style']}."

    # Add style hints (even though we have visual reference)
    video_prompt += f" Style: {episode['art_style'][:200]}"

    # Trim to 500 chars max for Sora
    if len(video_prompt) > 500:
        video_prompt = video_prompt[:497] + "..."

    print(f"Video Prompt ({len(video_prompt)} chars): {video_prompt}")
    print(f"Input Reference: {scene_image_path}")
    print()

    try:
        # Generate video using styled image as reference
        content_url = sora_client.generate_video(
            prompt=video_prompt,
            model="sora-2",
            seconds=4,
            size="1280x720",
            input_reference=str(scene_image_path)
        )

        # Download video
        video_path = videos_dir / f"{scene_id}_final.mp4"
        download_video(content_url, str(video_path), sora_client.api_key)

        print(f"✓ Phase 2 Complete: {video_path}")
        print()

    except Exception as e:
        print(f"✗ Phase 2 Failed: {e}")
        return

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)
    print()
    print("Output Files:")
    print(f"  Phase 1 Image: {scene_image_path}")
    print(f"  Phase 2 Video: {video_path}")
    print()
    print("What to Check:")
    print("  1. Does the Phase 1 image show the fox scene in watercolor style?")
    print("     (NOT the child from reference image)")
    print("  2. Does the Phase 2 video maintain the watercolor aesthetic?")
    print("  3. Does the video start with the fox (not morph from child)?")
    print()
    print("Compare with previous test:")
    print(f"  Old (no reference): output/style_test/scene_001_no_reference.mp4")
    print(f"  Old (direct ref):   output/style_test/scene_001_with_reference.mp4")
    print(f"  New (two-phase):    {video_path}")
    print()


if __name__ == "__main__":
    main()
