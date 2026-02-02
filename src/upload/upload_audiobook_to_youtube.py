#!/usr/bin/env python3
"""
Upload complete audiobook to YouTube: episode videos + promotional shorts.

Uses existing youtube_uploader.py to upload all generated content with proper metadata.

Usage:
    python scripts/upload_audiobook_to_youtube.py <audiobook.json>
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.upload.youtube_uploader import YouTubeUploader, UploadResult


def generate_scattered_schedule(
    num_videos: int,
    start_date: Optional[datetime] = None,
    min_hours_between: int = 4,
    max_hours_between: int = 12,
    preferred_hours: Optional[List[int]] = None
) -> List[datetime]:
    """
    Generate scattered publish times for videos.

    Args:
        num_videos: Number of videos to schedule
        start_date: When to start scheduling (default: tomorrow 9 AM)
        min_hours_between: Minimum hours between uploads
        max_hours_between: Maximum hours between uploads
        preferred_hours: List of preferred hours (0-23) for publishing

    Returns:
        List of datetime objects for scheduled publishing
    """
    if preferred_hours is None:
        # Default: morning, afternoon, evening slots (good for engagement)
        preferred_hours = [9, 11, 14, 16, 18, 20]

    if start_date is None:
        # Start tomorrow at a preferred hour
        start_date = datetime.now() + timedelta(days=1)
        start_date = start_date.replace(
            hour=random.choice(preferred_hours),
            minute=random.randint(0, 30),
            second=0,
            microsecond=0
        )

    schedule = []
    current_time = start_date

    for i in range(num_videos):
        schedule.append(current_time)

        # Add random interval for next video
        hours_gap = random.randint(min_hours_between, max_hours_between)
        current_time = current_time + timedelta(hours=hours_gap)

        # Try to align to a preferred hour
        if preferred_hours:
            closest_preferred = min(
                preferred_hours,
                key=lambda h: abs(current_time.hour - h)
            )
            current_time = current_time.replace(hour=closest_preferred)

        # Add some randomness to minutes
        current_time = current_time.replace(minute=random.randint(0, 45))

    return schedule


def generate_episode_metadata(
    audiobook: Dict,
    episode_number: int
) -> Dict[str, str]:
    """Generate YouTube metadata for an episode."""
    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']

    # Get episode info
    episodes = audiobook.get('episodes', [])
    episode_title = f"Episode {episode_number}"
    if episodes and episode_number <= len(episodes):
        episode_title = episodes[episode_number - 1].get('title', episode_title)

    # Create title
    title = f"{book_title} - Episode {episode_number}: {episode_title} | {author} Audiobook"

    # Create description
    description = f"""Episode {episode_number} of {book_title} by {author}.

📚 About this audiobook:
{audiobook.get('story_bible', '')[:500]}...

🎧 This is an AI-narrated audiobook adaptation of the classic work "{book_title}" by {author}.

🎬 Produced by Wormhole Podcast
🎨 Visual design features abstract impressionist artwork

#audiobook #literature #classicbooks #{author.replace(' ', '')} #{book_title.replace(' ', '')} #education"""

    # Tags
    tags = [
        book_title,
        author,
        "audiobook",
        "classic literature",
        "education",
        "literature",
        "narration",
        "full audiobook",
        "book",
        "educational video"
    ]

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category": "27"  # Education
    }


def generate_short_metadata(
    audiobook: Dict,
    chapter_num: int,
    short_name: str
) -> Dict[str, str]:
    """Generate YouTube metadata for a promotional short."""
    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']

    # Create title
    title = f"{short_name} | {book_title} by {author} #shorts"

    # Create description (will auto-add #shorts tag)
    description = f"""{short_name} from {book_title} by {author}.

📚 A powerful moment from this classic work of literature.

🎧 Listen to the full audiobook on our channel!
🎬 Wormhole Podcast

#shorts #audiobook #literature #{author.replace(' ', '')} #{book_title.replace(' ', '')}"""

    # Tags
    tags = [
        book_title,
        author,
        "shorts",
        "audiobook",
        "classic literature",
        "literature",
        "book clips",
        "educational"
    ]

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category": "27"  # Education
    }


def upload_episode_videos(
    audiobook_path: Path,
    video_dir: Path,
    uploader: YouTubeUploader,
    privacy: str = "public",
    schedule_scattered: bool = False,
    min_hours_between: int = 4,
    max_hours_between: int = 12
) -> List[UploadResult]:
    """
    Upload all episode videos.

    Args:
        audiobook_path: Path to audiobook JSON
        video_dir: Directory containing episode videos
        uploader: YouTubeUploader instance
        privacy: Privacy status (public, private, unlisted)
        schedule_scattered: If True, schedule videos with scattered publish times
        min_hours_between: Minimum hours between scheduled videos
        max_hours_between: Maximum hours between scheduled videos

    Returns:
        List of upload results
    """
    # Load audiobook
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"📺 Uploading Episode Videos to YouTube")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    if schedule_scattered:
        print(f"Scheduling: Scattered ({min_hours_between}-{max_hours_between}h between videos)")
    print(f"{'='*80}\n")

    results = []

    # Find all episode videos
    episode_videos = sorted(video_dir.glob("episode_*_final.mp4"))

    if not episode_videos:
        print("⚠️  No episode videos found!")
        return results

    # Generate schedule if needed
    schedule = None
    if schedule_scattered:
        schedule = generate_scattered_schedule(
            num_videos=len(episode_videos),
            min_hours_between=min_hours_between,
            max_hours_between=max_hours_between
        )
        print("📅 Scheduled publish times:")
        for i, dt in enumerate(schedule):
            print(f"   Episode {i+1}: {dt.strftime('%Y-%m-%d %H:%M')}")
        print()

    for idx, video_path in enumerate(episode_videos):
        # Extract episode number from filename
        episode_num = int(video_path.stem.split('_')[1])

        # Generate metadata
        metadata = generate_episode_metadata(audiobook, episode_num)

        # Get publish time if scheduling
        publish_at = None
        if schedule and idx < len(schedule):
            publish_at = schedule[idx].strftime('%Y-%m-%dT%H:%M:%S.000Z')

        print(f"\n📺 Uploading Episode {episode_num}...")
        print(f"   File: {video_path.name}")
        if publish_at:
            print(f"   Scheduled: {schedule[idx].strftime('%Y-%m-%d %H:%M')}")

        # Upload
        result = uploader.upload_video(
            video_path=video_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            category_id=metadata["category"],
            privacy_status=privacy,
            publish_at=publish_at
        )

        results.append(result)

        if result.success:
            print(f"   ✅ Uploaded successfully!")
            print(f"   URL: {result.video_url}")
        else:
            print(f"   ❌ Upload failed: {result.error}")

    return results


def upload_promotional_shorts(
    audiobook_path: Path,
    video_dir: Path,
    uploader: YouTubeUploader,
    privacy: str = "public"
) -> List[UploadResult]:
    """
    Upload all promotional short videos.

    Returns:
        List of upload results
    """
    # Load audiobook
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"📺 Uploading Promotional Shorts to YouTube")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"{'='*80}\n")

    results = []

    # Find all shorts
    for chapter_dir in sorted(video_dir.glob("chapter_*")):
        if not chapter_dir.is_dir():
            continue

        chapter_num = int(chapter_dir.name.split('_')[1])

        # Find shorts in this chapter
        shorts = sorted(chapter_dir.glob("*_SHORT.mp4"))

        for short_path in shorts:
            # Extract short name
            short_name = short_path.stem.replace('_SHORT', '').replace('_', ' ')

            # Generate metadata
            metadata = generate_short_metadata(audiobook, chapter_num, short_name)

            print(f"\n🎬 Uploading Short: {short_name} (Chapter {chapter_num})...")
            print(f"   File: {short_path.name}")

            # Upload
            result = uploader.upload_video(
                video_path=short_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category_id=metadata["category"],
                privacy_status=privacy
            )

            results.append(result)

            if result.success:
                print(f"   ✅ Uploaded successfully!")
                print(f"   URL: {result.video_url}")
            else:
                print(f"   ❌ Upload failed: {result.error}")

    return results


def main():
    """Upload audiobook videos to YouTube"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Upload audiobook episode videos and promotional shorts to YouTube'
    )
    parser.add_argument(
        'audiobook_json',
        help='Path to audiobook.json file'
    )
    parser.add_argument(
        '--episode-videos-dir',
        help='Directory with episode videos (default: same dir + /episode_videos)'
    )
    parser.add_argument(
        '--promo-videos-dir',
        help='Directory with promotional videos (default: same dir + /promo_videos)'
    )
    parser.add_argument(
        '--privacy',
        default="public",
        choices=['public', 'private', 'unlisted'],
        help='Privacy status for videos (default: public)'
    )
    parser.add_argument(
        '--episodes-only',
        action='store_true',
        help='Upload only episode videos (not shorts)'
    )
    parser.add_argument(
        '--shorts-only',
        action='store_true',
        help='Upload only promotional shorts (not episodes)'
    )
    parser.add_argument(
        '--schedule-scattered',
        action='store_true',
        help='Schedule videos with scattered publish times (starts tomorrow)'
    )
    parser.add_argument(
        '--min-hours-between',
        type=int,
        default=4,
        help='Minimum hours between scheduled videos (default: 4)'
    )
    parser.add_argument(
        '--max-hours-between',
        type=int,
        default=12,
        help='Maximum hours between scheduled videos (default: 12)'
    )

    args = parser.parse_args()

    # Load audiobook
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine directories
    episode_videos_dir = (Path(args.episode_videos_dir) if args.episode_videos_dir
                         else audiobook_path.parent / "episode_videos")
    promo_videos_dir = (Path(args.promo_videos_dir) if args.promo_videos_dir
                       else audiobook_path.parent / "promo_videos")

    # Create uploader
    print("\n🔐 Authenticating with YouTube...")
    uploader = YouTubeUploader()
    print("✓ Authenticated\n")

    all_results = []

    # Upload episodes
    if not args.shorts_only:
        if episode_videos_dir.exists():
            episode_results = upload_episode_videos(
                audiobook_path=audiobook_path,
                video_dir=episode_videos_dir,
                uploader=uploader,
                privacy=args.privacy,
                schedule_scattered=args.schedule_scattered,
                min_hours_between=args.min_hours_between,
                max_hours_between=args.max_hours_between
            )
            all_results.extend(episode_results)
        else:
            print(f"⚠️  Episode videos directory not found: {episode_videos_dir}")

    # Upload shorts
    if not args.episodes_only:
        if promo_videos_dir.exists():
            short_results = upload_promotional_shorts(
                audiobook_path=audiobook_path,
                video_dir=promo_videos_dir,
                uploader=uploader,
                privacy=args.privacy
            )
            all_results.extend(short_results)
        else:
            print(f"⚠️  Promotional videos directory not found: {promo_videos_dir}")

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 Upload Summary")
    print(f"{'='*80}")
    successful = len([r for r in all_results if r.success])
    failed = len([r for r in all_results if not r.success])
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📺 Total: {len(all_results)}")
    print(f"{'='*80}\n")

    # List successful uploads
    if successful > 0:
        print("✅ Successfully uploaded videos:")
        for result in all_results:
            if result.success:
                print(f"   • {result.title}")
                print(f"     {result.video_url}")
        print()

    # List failed uploads
    if failed > 0:
        print("❌ Failed uploads:")
        for result in all_results:
            if not result.success:
                print(f"   • {result.title}")
                print(f"     Error: {result.error}")
        print()

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
