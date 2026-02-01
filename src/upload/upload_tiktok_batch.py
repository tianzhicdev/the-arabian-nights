"""
Batch upload TikTok shorts to YouTube.

Features:
- Auto-generate titles from episode/story name
- Add main video link to all clips
- Track upload progress
- Resume on failure
- Generate upload report
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import argparse

from src.upload.youtube_uploader import YouTubeUploader, UploadResult


@dataclass
class BatchUploadConfig:
    """Configuration for batch upload."""
    tiktok_dir: Path
    episode_title: str
    main_video_url: Optional[str] = None
    privacy_status: str = "public"
    tags: List[str] = None
    description_template: str = "Part {clip_num} of {total_clips}\n\n{episode_title}"
    title_template: str = "{episode_title} - Part {clip_num}"


@dataclass
class BatchUploadProgress:
    """Track batch upload progress."""
    total_clips: int
    uploaded: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[Dict] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []


class TikTokBatchUploader:
    """Batch upload TikTok clips to YouTube."""

    def __init__(self, config: BatchUploadConfig):
        """
        Initialize batch uploader.

        Args:
            config: Upload configuration
        """
        self.config = config
        self.uploader = YouTubeUploader()
        self.progress_file = config.tiktok_dir / ".upload_progress.json"

    def upload_all(self, resume: bool = True) -> BatchUploadProgress:
        """
        Upload all clips in TikTok directory.

        Args:
            resume: Resume from previous progress if available

        Returns:
            BatchUploadProgress object
        """
        # Find all clips
        clips = self._find_clips()
        if not clips:
            print("❌ No clips found in directory")
            return BatchUploadProgress(total_clips=0)

        print(f"📹 Found {len(clips)} clips to upload")
        print(f"📂 Directory: {self.config.tiktok_dir}")
        print(f"🎬 Episode: {self.config.episode_title}")
        if self.config.main_video_url:
            print(f"🔗 Main video: {self.config.main_video_url}")
        print()

        # Load previous progress if resuming
        progress = self._load_progress() if resume else None
        if progress is None:
            progress = BatchUploadProgress(total_clips=len(clips))

        # Get already uploaded clip IDs
        uploaded_clips = set()
        if progress.results:
            uploaded_clips = {
                r['clip_id'] for r in progress.results
                if r.get('success', False)
            }

        # Upload each clip
        for i, clip_path in enumerate(clips, 1):
            clip_id = clip_path.stem  # e.g., "clip_001"

            # Skip if already uploaded
            if clip_id in uploaded_clips:
                print(f"⏭️  Skipping {clip_id} (already uploaded)")
                progress.skipped += 1
                continue

            print(f"\n[{i}/{len(clips)}] Uploading {clip_id}")

            # Generate title and description
            title = self._generate_title(i, len(clips))
            description = self._generate_description(i, len(clips))

            # Upload
            result = self.uploader.upload_video(
                video_path=clip_path,
                title=title,
                description=description,
                tags=self.config.tags or ['shorts'],
                privacy_status=self.config.privacy_status,
                main_video_url=self.config.main_video_url
            )

            # Track result
            result_dict = asdict(result)
            result_dict['clip_id'] = clip_id
            result_dict['clip_path'] = str(clip_path)
            progress.results.append(result_dict)

            if result.success:
                progress.uploaded += 1
                uploaded_clips.add(clip_id)
            else:
                progress.failed += 1

            # Save progress after each upload
            self._save_progress(progress)

            # Rate limiting (avoid hitting quota)
            if i < len(clips):
                time.sleep(2)

        # Print summary
        self._print_summary(progress)

        return progress

    def _find_clips(self) -> List[Path]:
        """Find all clip MP4 files."""
        clips = sorted(self.config.tiktok_dir.glob("clip_*.mp4"))
        return clips

    def _generate_title(self, clip_num: int, total_clips: int) -> str:
        """Generate video title."""
        return self.config.title_template.format(
            episode_title=self.config.episode_title,
            clip_num=clip_num,
            total_clips=total_clips
        )

    def _generate_description(self, clip_num: int, total_clips: int) -> str:
        """Generate video description."""
        return self.config.description_template.format(
            episode_title=self.config.episode_title,
            clip_num=clip_num,
            total_clips=total_clips
        )

    def _load_progress(self) -> Optional[BatchUploadProgress]:
        """Load previous upload progress."""
        if not self.progress_file.exists():
            return None

        try:
            with open(self.progress_file) as f:
                data = json.load(f)
            return BatchUploadProgress(**data)
        except Exception as e:
            print(f"⚠️  Could not load progress: {e}")
            return None

    def _save_progress(self, progress: BatchUploadProgress):
        """Save upload progress."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(asdict(progress), f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save progress: {e}")

    def _print_summary(self, progress: BatchUploadProgress):
        """Print upload summary."""
        print("\n" + "=" * 60)
        print("📊 UPLOAD SUMMARY")
        print("=" * 60)
        print(f"Total clips: {progress.total_clips}")
        print(f"Uploaded: {progress.uploaded} ✓")
        print(f"Failed: {progress.failed} ✗")
        print(f"Skipped: {progress.skipped} ⏭️")

        if progress.results:
            print("\n📝 Uploaded videos:")
            for result in progress.results:
                if result.get('success'):
                    print(f"   ✓ {result['title']}")
                    print(f"     {result['video_url']}")

        if progress.failed > 0:
            print("\n⚠️  Failed uploads:")
            for result in progress.results:
                if not result.get('success'):
                    print(f"   ✗ {result['title']}")
                    print(f"     Error: {result.get('error', 'Unknown')}")

        print("=" * 60)


def main():
    """CLI for batch uploading TikTok clips."""
    parser = argparse.ArgumentParser(
        description="Batch upload TikTok shorts to YouTube"
    )
    parser.add_argument(
        '--tiktok-dir',
        required=True,
        help="Directory with TikTok clips (e.g., output/tiktok/animal_farm_e1)"
    )
    parser.add_argument(
        '--episode-title',
        required=True,
        help="Episode title (e.g., 'Animal Farm Episode 1')"
    )
    parser.add_argument(
        '--main-video-url',
        help="URL to main video on YouTube"
    )
    parser.add_argument(
        '--privacy',
        default='public',
        choices=['public', 'private', 'unlisted'],
        help="Privacy status (default: public)"
    )
    parser.add_argument(
        '--tags',
        default='shorts,animation,story',
        help="Comma-separated tags"
    )
    parser.add_argument(
        '--title-template',
        default='{episode_title} - Part {clip_num}',
        help="Title template (default: '{episode_title} - Part {clip_num}')"
    )
    parser.add_argument(
        '--description-template',
        default='Part {clip_num} of {total_clips}\n\n{episode_title}',
        help="Description template"
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help="Don't resume from previous progress"
    )

    args = parser.parse_args()

    # Parse tags
    tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    # Create config
    config = BatchUploadConfig(
        tiktok_dir=Path(args.tiktok_dir),
        episode_title=args.episode_title,
        main_video_url=args.main_video_url,
        privacy_status=args.privacy,
        tags=tags,
        title_template=args.title_template,
        description_template=args.description_template
    )

    # Upload
    uploader = TikTokBatchUploader(config)
    progress = uploader.upload_all(resume=not args.no_resume)

    if progress.failed == 0:
        print("\n✅ All clips uploaded successfully!")
        return 0
    else:
        print(f"\n⚠️  {progress.failed} clips failed to upload")
        return 1


if __name__ == '__main__':
    sys.exit(main())
