#!/usr/bin/env python3
"""
Upload episodes with metadata tracking and scheduled publishing.
Uploads ALL pending videos, scheduling them 24 hours apart.
First video publishes at 2pm NY time the next day if no prior schedule exists.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from zoneinfo import ZoneInfo

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.upload.youtube_uploader import YouTubeUploader

# Default upload queue directory
UPLOAD_QUEUE_DIR = Path.home() / "upload_queue_main"

# NY timezone for scheduling
NY_TZ = ZoneInfo("America/New_York")


def find_latest_publish_at(queue_dir: Path = UPLOAD_QUEUE_DIR) -> Optional[datetime]:
    """
    Scan all metadata.json files to find the latest publish_at time.

    Returns:
        datetime of latest publish_at, or None if no scheduled videos exist
    """
    latest = None

    for metadata_file in queue_dir.glob("*/metadata.json"):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            publish_at = metadata.get('publish_at')
            if publish_at:
                # Parse ISO 8601 format
                dt = datetime.fromisoformat(publish_at.replace('Z', '+00:00'))
                if latest is None or dt > latest:
                    latest = dt
        except Exception as e:
            print(f"  Warning: Could not read {metadata_file}: {e}")

    return latest


def get_initial_publish_time() -> datetime:
    """
    Get initial publish time: 2pm NY time the next day.

    Returns:
        datetime in UTC
    """
    # Get tomorrow at 2pm NY time
    now_ny = datetime.now(NY_TZ)
    tomorrow_2pm_ny = now_ny.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # Convert to UTC
    return tomorrow_2pm_ny.astimezone(timezone.utc)


def format_publish_time(dt: datetime) -> str:
    """Format datetime for YouTube API (ISO 8601 with Z suffix)."""
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def calculate_next_publish_time(
    queue_dir: Path = UPLOAD_QUEUE_DIR,
    after: Optional[datetime] = None
) -> Tuple[str, datetime]:
    """
    Calculate the next publish time.

    Args:
        queue_dir: Directory to scan for existing schedules
        after: If provided, use this as the base time instead of scanning

    Returns:
        Tuple of (ISO 8601 string for API, datetime object for chaining)
    """
    if after:
        # Use provided time + 24h
        next_time = after + timedelta(hours=24)
    else:
        # Scan for latest scheduled time
        latest = find_latest_publish_at(queue_dir)

        if latest:
            next_time = latest + timedelta(hours=24)
            print(f"  Latest scheduled: {latest.isoformat()}")
        else:
            # No scheduled videos, use 2pm NY time tomorrow
            next_time = get_initial_publish_time()
            print(f"  No scheduled videos found, using 2pm NY tomorrow")

    publish_at_str = format_publish_time(next_time)
    print(f"  Publish time: {publish_at_str}")

    return publish_at_str, next_time


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


def upload_episode(
    episode_dir: Path,
    force: bool = False,
    publish_at: Optional[str] = None,
    publish_at_dt: Optional[datetime] = None,
    token_file: Optional[Path] = None
) -> Tuple[bool, Optional[datetime]]:
    """
    Upload episode if not already uploaded.

    Args:
        episode_dir: Directory containing episode video and metadata
        force: Force upload even if already uploaded
        publish_at: Pre-calculated publish time (ISO 8601 string)
        publish_at_dt: datetime object for chaining to next upload

    Returns:
        Tuple of (success, publish_at_dt for chaining)
    """
    # Find metadata file
    metadata_file = episode_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"❌ No metadata.json found in {episode_dir}")
        return False, None

    # Load metadata
    metadata = load_metadata(metadata_file)

    # Check if already uploaded
    if metadata.get('uploaded') and not force:
        print(f"✓ Episode already uploaded: {metadata.get('youtube_url')}")
        print(f"  Uploaded: {metadata.get('upload_date')}")
        return True, None

    if force and metadata.get('uploaded'):
        print(f"⚠️  Force re-upload enabled. Previous upload: {metadata.get('youtube_url')}")

    # Find video file
    video_file = episode_dir / metadata['video_filename']
    if not video_file.exists():
        print(f"❌ Video file not found: {video_file}")
        return False, None

    print(f"\n{'='*60}")
    print(f"Uploading: {metadata['title']}")
    print(f"File: {video_file.name}")
    print(f"{'='*60}\n")

    # Use provided publish time or calculate it
    if publish_at is None:
        print("Calculating publish schedule...")
        publish_at, publish_at_dt = calculate_next_publish_time()

    # Upload video
    try:
        uploader = YouTubeUploader(token_path=token_file)
        result = uploader.upload_video(
            video_path=video_file,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            category_id=metadata.get('category_id', '27'),  # Education
            privacy_status='private',  # Will be set to private for scheduled publishing
            made_for_kids=False,
            publish_at=publish_at
        )

        if result.success:
            # Update metadata
            metadata['uploaded'] = True
            metadata['upload_date'] = datetime.now().isoformat()
            metadata['youtube_video_id'] = result.video_id
            metadata['youtube_url'] = result.video_url
            metadata['upload_time_seconds'] = result.upload_time
            metadata['publish_at'] = publish_at  # Save scheduled publish time

            # Save updated metadata
            save_metadata(metadata_file, metadata)

            # Create .uploaded marker file
            uploaded_marker = episode_dir / ".uploaded"
            uploaded_marker.write_text(f"{result.video_url}\n{datetime.now().isoformat()}\npublish_at: {publish_at}\n")
            print(f"✓ Created upload marker: {uploaded_marker}")

            print(f"\n{'='*60}")
            print(f"✅ UPLOAD SUCCESSFUL")
            print(f"{'='*60}")
            print(f"Video URL: {result.video_url}")
            print(f"Video ID: {result.video_id}")
            print(f"Upload time: {result.upload_time:.1f}s")
            print(f"Scheduled publish: {publish_at}")
            print(f"{'='*60}\n")

            return True, publish_at_dt
        else:
            print(f"\n{'='*60}")
            print(f"❌ UPLOAD FAILED")
            print(f"{'='*60}")
            print(f"Error: {result.error}")
            print(f"{'='*60}\n")
            return False, None

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Upload error: {error_msg}")

        # Check for daily upload limit
        if 'uploadLimitExceeded' in error_msg or 'quota' in error_msg.lower():
            print("\n⚠️  YouTube daily upload limit reached (6 videos/day)")
            print("   Remaining videos will be uploaded on next cron run.")
            return False, "DAILY_LIMIT_REACHED"

        return False, None


def find_pending_episodes(queue_dir: Path = UPLOAD_QUEUE_DIR) -> List[Tuple[float, Path]]:
    """
    Find all episodes pending upload, sorted by creation timestamp (oldest first).

    Returns:
        List of (timestamp, episode_dir) tuples
    """
    pending = []

    for metadata_file in queue_dir.glob("*/metadata.json"):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            if not metadata.get('uploaded', False):
                timestamp = metadata.get('creation_timestamp', 0)
                pending.append((timestamp, metadata_file.parent))
        except Exception as e:
            print(f"  Warning: Could not read {metadata_file}: {e}")

    # Sort by timestamp (oldest first)
    pending.sort(key=lambda x: x[0])
    return pending


def upload_all_pending(
    queue_dir: Path = UPLOAD_QUEUE_DIR,
    force: bool = False,
    token_file: Optional[Path] = None
) -> int:
    """
    Upload all pending episodes with scheduled publishing.
    Each video is scheduled 24 hours after the previous one.

    Args:
        queue_dir: Upload queue directory
        force: Force re-upload of already uploaded videos
        token_file: Optional path to YouTube token file (for different channels)

    Returns:
        Number of videos successfully uploaded
    """
    print(f"\n{'='*60}")
    print(f"📤 Uploading All Pending Videos")
    print(f"{'='*60}")
    print(f"Queue: {queue_dir}")
    print(f"{'='*60}\n")

    # Find all pending episodes
    pending = find_pending_episodes(queue_dir)

    if not pending:
        print("No videos pending upload.")
        return 0

    print(f"Found {len(pending)} video(s) pending upload:\n")
    for _, episode_dir in pending:
        print(f"  - {episode_dir.name}")
    print()

    # Calculate initial publish time
    print("Calculating publish schedule...")
    publish_at_str, publish_at_dt = calculate_next_publish_time(queue_dir)

    success_count = 0

    for i, (_, episode_dir) in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] Processing: {episode_dir.name}")

        # For subsequent videos, add 24h to previous publish time
        if i > 0:
            publish_at_str, publish_at_dt = calculate_next_publish_time(after=publish_at_dt)

        success, new_dt = upload_episode(
            episode_dir,
            force=force,
            publish_at=publish_at_str,
            publish_at_dt=publish_at_dt,
            token_file=token_file
        )

        if success:
            success_count += 1
            # Use the returned datetime for next iteration
            if new_dt:
                publish_at_dt = new_dt
        elif new_dt == "DAILY_LIMIT_REACHED":
            # YouTube daily limit hit, stop and let cron retry tomorrow
            print(f"\n⏸️  Stopping due to daily limit. {len(pending) - i - 1} videos remaining.")
            break

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary")
    print(f"{'='*60}")
    print(f"Total pending: {len(pending)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(pending) - success_count}")
    print(f"{'='*60}\n")

    return success_count


def main():
    parser = argparse.ArgumentParser(
        description='Upload episodes with metadata tracking and scheduled publishing'
    )
    parser.add_argument(
        'episode_dir',
        type=str,
        nargs='?',
        default=None,
        help='Directory containing episode and metadata.json (optional, uploads all if not specified)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Upload all pending videos in the queue'
    )
    parser.add_argument(
        '--queue-dir',
        type=str,
        default=str(UPLOAD_QUEUE_DIR),
        help=f'Upload queue directory (default: {UPLOAD_QUEUE_DIR})'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force upload even if already uploaded'
    )
    parser.add_argument(
        '--token-file',
        type=str,
        default=None,
        help='Path to YouTube token file (for uploading to different channels)'
    )

    args = parser.parse_args()

    queue_dir = Path(args.queue_dir)
    token_file = Path(args.token_file) if args.token_file else None

    # If --all or no episode_dir specified, upload all pending
    if args.all or args.episode_dir is None:
        count = upload_all_pending(queue_dir, force=args.force, token_file=token_file)
        sys.exit(0 if count > 0 else 1)

    # Upload single episode
    episode_dir = Path(args.episode_dir)
    if not episode_dir.exists():
        print(f"❌ Directory not found: {episode_dir}")
        sys.exit(1)

    success, _ = upload_episode(episode_dir, force=args.force, token_file=token_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
