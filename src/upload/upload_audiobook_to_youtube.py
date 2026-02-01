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
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from src.upload.youtube_uploader import YouTubeUploader, UploadResult


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
    privacy: str = "public"
) -> List[UploadResult]:
    """
    Upload all episode videos.

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
    print(f"{'='*80}\n")

    results = []

    # Find all episode videos
    episode_videos = sorted(video_dir.glob("episode_*_final.mp4"))

    if not episode_videos:
        print("⚠️  No episode videos found!")
        return results

    for video_path in episode_videos:
        # Extract episode number from filename
        episode_num = int(video_path.stem.split('_')[1])

        # Generate metadata
        metadata = generate_episode_metadata(audiobook, episode_num)

        print(f"\n📺 Uploading Episode {episode_num}...")
        print(f"   File: {video_path.name}")

        # Upload
        result = uploader.upload_video(
            video_path=video_path,
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
                privacy=args.privacy
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
