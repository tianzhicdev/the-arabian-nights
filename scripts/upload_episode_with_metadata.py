#!/usr/bin/env python3
"""
Upload Animal Farm episodes with metadata tracking.
Automatically skips already-uploaded episodes.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from youtube_uploader import YouTubeUploader


def load_metadata(metadata_file: Path) -> dict:
    """Load episode metadata."""
    if not metadata_file.exists():
        print(f"❌ Metadata file not found: {metadata_file}")
        sys.exit(1)

    with open(metadata_file, 'r') as f:
        return json.load(f)


def save_metadata(metadata_file: Path, metadata: dict):
    """Save updated metadata."""
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata updated: {metadata_file}")


def upload_episode(episode_dir: Path, force: bool = False) -> bool:
    """
    Upload episode if not already uploaded.

    Args:
        episode_dir: Directory containing episode video and metadata
        force: Force upload even if already uploaded

    Returns:
        True if upload successful, False otherwise
    """
    # Find metadata file
    metadata_file = episode_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"❌ No metadata.json found in {episode_dir}")
        return False

    # Load metadata
    metadata = load_metadata(metadata_file)

    # Check if already uploaded
    if metadata.get('uploaded') and not force:
        print(f"✓ Episode already uploaded: {metadata.get('youtube_url')}")
        print(f"  Uploaded: {metadata.get('upload_date')}")
        return True

    if force and metadata.get('uploaded'):
        print(f"⚠️  Force re-upload enabled. Previous upload: {metadata.get('youtube_url')}")

    # Find video file
    video_file = episode_dir / metadata['video_filename']
    if not video_file.exists():
        print(f"❌ Video file not found: {video_file}")
        return False

    print(f"\n{'='*60}")
    print(f"Uploading: {metadata['title']}")
    print(f"File: {video_file.name}")
    print(f"{'='*60}\n")

    # Upload video
    try:
        uploader = YouTubeUploader()
        result = uploader.upload_video(
            video_path=video_file,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            category_id=metadata.get('category_id', '27'),  # Education
            privacy_status=metadata.get('privacy_status', 'public'),
            made_for_kids=False
        )

        if result.success:
            # Update metadata
            metadata['uploaded'] = True
            metadata['upload_date'] = datetime.now().isoformat()
            metadata['youtube_video_id'] = result.video_id
            metadata['youtube_url'] = result.video_url
            metadata['upload_time_seconds'] = result.upload_time

            # Save updated metadata
            save_metadata(metadata_file, metadata)

            # Create .uploaded marker file
            uploaded_marker = episode_dir / ".uploaded"
            uploaded_marker.write_text(f"{result.video_url}\n{datetime.now().isoformat()}\n")
            print(f"✓ Created upload marker: {uploaded_marker}")

            print(f"\n{'='*60}")
            print(f"✅ UPLOAD SUCCESSFUL")
            print(f"{'='*60}")
            print(f"Video URL: {result.video_url}")
            print(f"Video ID: {result.video_id}")
            print(f"Upload time: {result.upload_time:.1f}s")
            print(f"{'='*60}\n")

            return True
        else:
            print(f"\n{'='*60}")
            print(f"❌ UPLOAD FAILED")
            print(f"{'='*60}")
            print(f"Error: {result.error}")
            print(f"{'='*60}\n")
            return False

    except Exception as e:
        print(f"\n❌ Upload error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Upload Animal Farm episode with metadata tracking'
    )
    parser.add_argument(
        'episode_dir',
        type=str,
        help='Directory containing episode and metadata.json'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force upload even if already uploaded'
    )

    args = parser.parse_args()

    episode_dir = Path(args.episode_dir)
    if not episode_dir.exists():
        print(f"❌ Directory not found: {episode_dir}")
        sys.exit(1)

    success = upload_episode(episode_dir, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
