#!/usr/bin/env python3
"""
Short Pipeline Test: 2 scenes, ~14 seconds total
Tests GPT-Image-1.5 (16:9) + Sora end-to-end pipeline
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.openai_responses_image_client import OpenAIResponsesImageClient
from openai_client import OpenAIClient


def download_video(content_url: str, output_path: str, api_key: str):
    """Download video from Sora content URL."""
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(content_url, headers=headers, timeout=120)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(response.content)


def main():
    # Load test scenes
    project_root = Path(__file__).parent.parent
    scenes_file = project_root / "short_test_scenes.json"

    with open(scenes_file, 'r') as f:
        data = json.load(f)

    episode = data['episode']
    scenes = data['scenes']

    # Style reference image
    style_reference = project_root / "resources/style_references/watercolor_reference_1280x720.jpg"

    # Output directories
    output_dir = project_root / "output/short_test"
    images_dir = output_dir / "images"
    videos_dir = output_dir / "videos"

    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Initialize clients
    image_client = OpenAIResponsesImageClient()
    sora_client = OpenAIClient()

    print("=" * 80)
    print("SHORT PIPELINE TEST - 2 SCENES (~14 SECONDS)")
    print("=" * 80)
    print(f"Episode: {episode['title']}")
    print(f"Style Reference: {style_reference}")
    print(f"Total Scenes: {len(scenes)}")
    print()

    all_videos = []

    for scene in scenes:
        scene_id = scene['scene_id']
        expected_duration = scene['expected_duration']

        print("=" * 80)
        print(f"PROCESSING: {scene_id} ({expected_duration}s)")
        print("=" * 80)
        print(f"Description: {scene['video_description'][:80]}...")
        print()

        # PHASE 1: Generate Image with Style (16:9 ratio)
        print("PHASE 1: Generating 16:9 image with watercolor style...")
        try:
            b64_image_data = image_client.generate_with_style_reference(
                prompt=scene['video_description'],
                style_reference_path=str(style_reference),
                model="gpt-4o",
                size="1536x1024"  # 3:2 ratio, will crop to 16:9
            )

            # Save and resize to exactly 1280x720
            temp_path = images_dir / f"{scene_id}_temp.png"
            final_path = images_dir / f"{scene_id}.png"

            image_client.save_base64_image(b64_image_data, str(temp_path))

            # Resize to exactly 1280x720
            subprocess.run([
                "sips", "-z", "720", "1280",
                str(temp_path), "--out", str(final_path)
            ], check=True, capture_output=True)
            temp_path.unlink()

            print(f"✓ Image ready: {final_path}")
            print()

        except Exception as e:
            print(f"✗ Phase 1 failed: {e}")
            continue

        # PHASE 2: Generate Video
        print(f"PHASE 2: Generating {int(expected_duration)}s video...")

        # Determine video duration (round to 4, 8, or 12)
        if expected_duration <= 6:
            video_duration = 4
        elif expected_duration <= 10:
            video_duration = 8
        else:
            video_duration = 12

        # Build prompt
        video_prompt = f"{scene['video_description']}. Camera: {scene['camera_style']}."
        if len(video_prompt) > 500:
            video_prompt = video_prompt[:497] + "..."

        try:
            content_url = sora_client.generate_video(
                prompt=video_prompt,
                model="sora-2",
                seconds=video_duration,
                size="1280x720",
                input_reference=str(final_path)
            )

            # Download video
            video_path = videos_dir / f"{scene_id}.mp4"
            download_video(content_url, str(video_path), sora_client.api_key)

            # Trim to expected duration if needed
            if video_duration > expected_duration:
                trimmed_path = videos_dir / f"{scene_id}_trimmed.mp4"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-t", str(expected_duration),
                    "-c", "copy",
                    str(trimmed_path)
                ], check=True, capture_output=True)
                video_path.unlink()
                trimmed_path.rename(video_path)

            all_videos.append(str(video_path))
            print(f"✓ Video ready: {video_path}")
            print()

        except Exception as e:
            print(f"✗ Phase 2 failed: {e}")
            continue

    # PHASE 3: Assemble final video
    if len(all_videos) == len(scenes):
        print("=" * 80)
        print("PHASE 3: Assembling final video...")
        print("=" * 80)

        # Create concat file
        concat_file = output_dir / "concat.txt"
        with open(concat_file, 'w') as f:
            for video in all_videos:
                f.write(f"file '{video}'\n")

        final_video = output_dir / "final_video.mp4"

        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(final_video)
            ], check=True, capture_output=True)

            concat_file.unlink()

            print(f"✓ Final video: {final_video}")
            print()

        except Exception as e:
            print(f"✗ Assembly failed: {e}")

    print("=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)
    print()
    print(f"Output: {output_dir}")
    print(f"  - Images: {len(list(images_dir.glob('*.png')))} files")
    print(f"  - Videos: {len(list(videos_dir.glob('*.mp4')))} files")
    if (output_dir / "final_video.mp4").exists():
        print(f"  - Final: final_video.mp4")
    print()


if __name__ == "__main__":
    main()
