"""
Delete videos from YouTube by video ID.
"""

import sys
import argparse
from pathlib import Path
from typing import List
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_FILE = PROJECT_ROOT / 'credentials' / 'youtube_token.pickle'


def delete_video(youtube, video_id: str) -> bool:
    """
    Delete a video from YouTube.

    Args:
        youtube: YouTube API service
        video_id: Video ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        youtube.videos().delete(id=video_id).execute()
        return True
    except HttpError as e:
        print(f"  ✗ Error: {e}")
        return False


def delete_videos(video_ids: List[str]):
    """Delete multiple videos."""

    # Load credentials
    if not TOKEN_FILE.exists():
        print("❌ No credentials found. Run test_youtube_auth.py first.")
        return

    with open(TOKEN_FILE, 'rb') as token:
        credentials = pickle.load(token)

    # Build YouTube service
    youtube = build('youtube', 'v3', credentials=credentials)

    print(f"🗑️  Deleting {len(video_ids)} videos from YouTube")
    print()

    success_count = 0
    failed_count = 0

    for i, video_id in enumerate(video_ids, 1):
        print(f"[{i}/{len(video_ids)}] Deleting video: {video_id}")
        print(f"   URL: https://www.youtube.com/watch?v={video_id}")

        if delete_video(youtube, video_id):
            print(f"   ✓ Deleted successfully")
            success_count += 1
        else:
            print(f"   ✗ Failed to delete")
            failed_count += 1

        print()

    print("=" * 60)
    print("📊 DELETION SUMMARY")
    print("=" * 60)
    print(f"Total: {len(video_ids)}")
    print(f"Deleted: {success_count} ✓")
    print(f"Failed: {failed_count} ✗")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Delete videos from YouTube"
    )
    parser.add_argument(
        '--video-ids',
        required=True,
        help="Comma-separated video IDs to delete"
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Parse video IDs
    video_ids = [vid.strip() for vid in args.video_ids.split(',') if vid.strip()]

    if not video_ids:
        print("❌ No video IDs provided")
        return 1

    # Show what will be deleted
    print(f"⚠️  WARNING: About to delete {len(video_ids)} videos:")
    print()
    for i, video_id in enumerate(video_ids, 1):
        print(f"  {i}. https://www.youtube.com/watch?v={video_id}")
    print()

    # Confirm deletion
    if not args.confirm:
        response = input("Are you sure you want to delete these videos? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Deletion cancelled")
            return 0

    # Delete videos
    delete_videos(video_ids)
    return 0


if __name__ == '__main__':
    sys.exit(main())
