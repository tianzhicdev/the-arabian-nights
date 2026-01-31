#!/usr/bin/env python3
"""
Two-Phase Style-Consistent Video Generation Pipeline Test
Using GPT-Image-1.5 (OpenAI) + Sora (OpenAI)

Phase 1: Generate scene-specific images with GPT-Image-1.5 (style from reference)
Phase 2: Generate videos from those images with Sora
"""

import os
import sys
import json
import base64
import requests
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai_image_client import OpenAIImageClient
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

    # Style reference image (your watercolor.jpg)
    style_reference = project_root / "resources/style_references/watercolor_reference_1280x720.jpg"

    # Output directories
    output_dir = project_root / "output/two_phase_gpt_image"
    images_dir = output_dir / "phase1_images"
    videos_dir = output_dir / "phase2_videos"

    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Initialize clients (both use same OpenAI API key)
    image_client = OpenAIImageClient()
    sora_client = OpenAIClient()

    print("=" * 80)
    print("TWO-PHASE STYLE-CONSISTENT VIDEO GENERATION TEST")
    print("=" * 80)
    print(f"Episode: {episode['title']}")
    print(f"Style Reference: {style_reference}")
    print(f"Total Scenes: {len(scenes)}")
    print()
    print("Pipeline:")
    print("  Phase 1: GPT-Image-1.5 (OpenAI) → Scene images with watercolor style")
    print("  Phase 2: Sora (OpenAI) → Videos from styled images")
    print()
    print("API Key:")
    print(f"  ✓ OpenAI: {image_client.api_key[:10]}...")
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
    # PHASE 1: Generate Scene-Specific Image with GPT-Image-1.5
    # =========================================================================
    print("─" * 80)
    print("PHASE 1: Generating scene-specific image with watercolor style")
    print("─" * 80)

    # Build a clean prompt for image generation
    image_prompt = scene['video_description']

    # Trim if too long
    if len(image_prompt) > 1000:
        image_prompt = image_prompt[:997] + "..."

    print(f"Image Prompt: {image_prompt}")
    print()

    try:
        # Generate image with style from watercolor reference using GPT-Image-1.5
        b64_image_data = image_client.generate_with_style_reference(
            prompt=image_prompt,
            style_reference_path=str(style_reference),
            input_fidelity="high",  # Extract style from reference
            quality="high",
            size="1024x1024"  # Will resize to 1280x720 for Sora
        )

        # Save the generated image (temp)
        scene_image_path_temp = images_dir / f"{scene_id}_styled_temp.png"
        image_client.save_base64_image(b64_image_data, str(scene_image_path_temp))

        # Resize to exactly 1280x720 for Sora
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
        import traceback
        traceback.print_exc()
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
        import traceback
        traceback.print_exc()
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
    print("Compare with previous tests:")
    print(f"  Baseline (no ref):    output/style_test/scene_001_no_reference.mp4")
    print(f"  Direct ref:           output/style_test/scene_001_with_reference.mp4")
    print(f"  FLUX Redux:           output/two_phase_test/phase2_videos/scene_001_final.mp4")
    print(f"  GPT-Image-1.5 (new):  {video_path}")
    print()
    print("Cost Breakdown:")
    print("  Phase 1 (GPT-Image-1.5): ~$0.04-0.08 (high quality)")
    print("  Phase 2 (Sora):          ~$0.60 (4 seconds)")
    print("  Total:                   ~$0.64-0.68 per scene")
    print()


if __name__ == "__main__":
    main()
