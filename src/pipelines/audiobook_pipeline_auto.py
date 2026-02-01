#!/usr/bin/env python3
"""
Fully automated, resumable audiobook pipeline with hash-based file naming.

Usage:
    python scripts/audiobook_pipeline_auto.py <txt_file_or_url> <voice_id>

Examples:
    python scripts/audiobook_pipeline_auto.py book.txt ePiPWpzcHZrcqRzFrgQg
    python scripts/audiobook_pipeline_auto.py https://gutenberg.net.au/ebooks02/0200141.txt ePiPWpzcHZrcqRzFrgQg
"""

import os
import sys
import hashlib
import subprocess
import requests
from pathlib import Path
from typing import Optional

# Upload queue configuration (local Mac Mini directory)
UPLOAD_QUEUE_DIR = os.getenv("UPLOAD_QUEUE_DIR", os.path.expanduser("~/upload_queue_main"))


def calculate_hash(content: str, length: int = 7) -> str:
    """Calculate hash of text content (first 7 digits)."""
    hash_obj = hashlib.sha256(content.encode('utf-8'))
    return hash_obj.hexdigest()[:length]


def download_text(url_or_path: str) -> tuple[str, str]:
    """
    Download text from URL or read from file.

    Returns:
        (text_content, source_identifier)
    """
    if url_or_path.startswith('http://') or url_or_path.startswith('https://'):
        print(f"📥 Downloading from URL: {url_or_path}")
        response = requests.get(url_or_path, timeout=60)
        response.raise_for_status()
        text = response.text
        source = url_or_path
    else:
        print(f"📖 Reading from file: {url_or_path}")
        with open(url_or_path, 'r', encoding='utf-8') as f:
            text = f.read()
        source = Path(url_or_path).name

    return text, source


def run_step(cmd: list, description: str, output_file: Optional[Path] = None) -> int:
    """
    Run a pipeline step, skipping if output already exists.

    Args:
        cmd: Command to run
        description: Step description
        output_file: If provided and exists, skip this step

    Returns:
        0 if successful or skipped, non-zero if failed
    """
    print(f"\n{'='*80}")
    print(f"📋 {description}")
    print(f"{'='*80}")

    # Check if output already exists
    if output_file and output_file.exists():
        print(f"✓ Output already exists, skipping: {output_file}")
        print(f"{'='*80}\n")
        return 0

    print(f"Command: {' '.join(str(c) for c in cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return result.returncode

    print(f"\n✅ {description} completed successfully")
    return 0


def queue_for_upload(output_dir: Path, book_hash: str, audiobook_json: Path, source_name: str) -> bool:
    """
    Queue completed audiobook for YouTube upload.

    Creates metadata.json and copies video to upload queue directory.

    Args:
        output_dir: Local directory with generated files
        book_hash: Book hash identifier
        audiobook_json: Path to audiobook JSON file
        source_name: Original source filename

    Returns:
        True if successful, False otherwise
    """
    import json
    import shutil
    import time

    print(f"\n{'='*80}")
    print(f"📤 Queuing for YouTube Upload")
    print(f"{'='*80}")

    # Find the episode video
    video_dir = output_dir / "episode_videos"
    video_files = list(video_dir.glob("episode_*_final.mp4")) if video_dir.exists() else []

    if not video_files:
        print(f"❌ No episode videos found in {video_dir}")
        return False

    # Load audiobook metadata
    try:
        with open(audiobook_json, 'r') as f:
            audiobook_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load audiobook JSON: {e}")
        return False

    book_title = audiobook_data.get('book_title', source_name.replace('.txt', '').replace('_', ' ').title())

    # Queue each episode
    queue_dir = Path(UPLOAD_QUEUE_DIR)
    queue_dir.mkdir(parents=True, exist_ok=True)

    queued_count = 0
    for video_file in sorted(video_files):
        # Extract episode number from filename
        import re
        match = re.search(r'episode_(\d+)', video_file.name)
        episode_num = int(match.group(1)) if match else 1

        # Create queue subdirectory
        episode_queue_dir = queue_dir / f"{book_hash}_ep{episode_num:02d}"
        episode_queue_dir.mkdir(parents=True, exist_ok=True)

        # Copy video file
        dest_video = episode_queue_dir / video_file.name
        if not dest_video.exists():
            print(f"  Copying {video_file.name} to queue...")
            shutil.copy2(video_file, dest_video)
        else:
            print(f"  Video already in queue: {dest_video.name}")

        # Create metadata.json
        metadata_file = episode_queue_dir / "metadata.json"
        if not metadata_file.exists():
            # Clean title for YouTube
            clean_title = book_title.replace('_', ' ').title()

            metadata = {
                "episode_number": episode_num,
                "video_filename": video_file.name,
                "title": f"{clean_title} | Classic Literature Audiobook",
                "subtitle": clean_title,
                "description": f"""Listen to {clean_title}, a classic work of literature brought to life.

This audiobook features professional narration with atmospheric visuals.

Subscribe for more classic literature audiobooks!

#audiobook #literature #classics #books""",
                "tags": [
                    clean_title.split()[0] if clean_title else "audiobook",
                    "classic literature",
                    "audiobook",
                    "education",
                    "literature",
                    "educational video",
                    "book adaptation",
                    "full audiobook"
                ],
                "category_id": "27",  # Education
                "privacy_status": "public",
                "uploaded": False,
                "creation_timestamp": time.time(),
                "book_hash": book_hash,
                "source_file": source_name
            }

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"  Created metadata.json for episode {episode_num}")

        queued_count += 1

    print(f"\n✅ Queued {queued_count} episode(s) for upload")
    print(f"   Queue directory: {queue_dir}")
    print(f"   Upload will run via: scripts/upload_next_episode.sh")
    return True


def main():
    """Run the complete automated pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fully automated audiobook pipeline with hash-based naming',
        epilog='Example: python scripts/audiobook_pipeline_auto.py book.txt ePiPWpzcHZrcqRzFrgQg'
    )
    parser.add_argument('source', help='Text file path or URL')
    parser.add_argument('voice_id', nargs='?', default=None, help='ElevenLabs voice ID (not needed with --coqui)')
    parser.add_argument('--coqui', action='store_true', help='Use Coqui TTS (local, free) instead of ElevenLabs')
    parser.add_argument('--coqui-model', default='tts_models/en/ljspeech/vits',
                       help='Coqui TTS model (default: tts_models/en/ljspeech/vits)')
    parser.add_argument('--skip-queue', action='store_true', help='Skip queueing for YouTube upload')
    parser.add_argument('--base-dir', default='output/audiobook_pipeline',
                       help='Base directory for output (default: output/audiobook_pipeline)')

    args = parser.parse_args()

    # Validate arguments
    if not args.coqui and not args.voice_id:
        parser.error("voice_id is required unless --coqui is specified")

    tts_engine = "Coqui TTS (local)" if args.coqui else "ElevenLabs"

    print(f"\n{'='*80}")
    print(f"🚀 AUTOMATED AUDIOBOOK PIPELINE")
    print(f"{'='*80}")
    print(f"Source: {args.source}")
    print(f"TTS Engine: {tts_engine}")
    if args.coqui:
        print(f"Coqui Model: {args.coqui_model}")
    else:
        print(f"Voice ID: {args.voice_id}")
    print(f"{'='*80}\n")

    # Step 1: Download/read text and calculate hash
    try:
        text_content, source_name = download_text(args.source)
    except Exception as e:
        print(f"❌ Failed to load source: {e}")
        return 1

    book_hash = calculate_hash(text_content)
    print(f"\n📊 Book hash: {book_hash}")

    # Create output directory with hash
    output_dir = Path(args.base_dir) / book_hash
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Output directory: {output_dir}")

    # Save raw text with hash
    raw_text_file = output_dir / f"book_{book_hash}.txt"
    if not raw_text_file.exists():
        with open(raw_text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"✓ Saved raw text: {raw_text_file}")

    # Define file paths with hash
    audiobook_json = output_dir / f"audiobook_{book_hash}.json"
    audiobook_with_timing = output_dir / f"audiobook_{book_hash}_timing.json"

    # Step 2: Generate audiobook JSON
    ret = run_step(
        ['python', 'src/tools/book_to_audiobook.py', args.source, '--output-dir', str(output_dir)],
        f"Step 1/7: Generate Audiobook JSON ({book_hash})",
        audiobook_json
    )
    if ret != 0:
        return ret

    # Rename output to include hash
    default_json = output_dir / "audiobook.json"
    if default_json.exists() and not audiobook_json.exists():
        default_json.rename(audiobook_json)

    # Step 3: Generate episode audio
    audio_dir = output_dir / "episode_audio"
    episode_audio = audio_dir / f"{book_hash}_episode_01.mp3"

    if args.coqui:
        # Use Coqui TTS (local, free)
        ret = run_step(
            ['python', 'src/generators/generate_audiobook_audio_coqui.py', str(audiobook_json),
             '--model', args.coqui_model],
            f"Step 2/7: Generate Episode Audio with Coqui ({book_hash})",
            None  # Check will be done by script internally
        )
    else:
        # Use ElevenLabs
        ret = run_step(
            ['python', 'src/generators/generate_audiobook_audio.py', str(audiobook_json), '--voice-id', args.voice_id],
            f"Step 2/7: Generate Episode Audio ({book_hash})",
            None  # Check will be done by script internally
        )
    if ret != 0:
        return ret

    # Step 4: Generate promotional audio
    promo_audio_dir = output_dir / "promo_audio"

    ret = run_step(
        ['python', 'src/generators/generate_promotional_audio.py', str(audiobook_json), '--voice-id', args.voice_id],
        f"Step 3/7: Generate Promotional Audio ({book_hash})",
        None  # Outputs audiobook_with_timing.json
    )
    if ret != 0:
        return ret

    # Rename timing file to include hash
    default_timing = output_dir / "audiobook_with_timing.json"
    if default_timing.exists() and not audiobook_with_timing.exists():
        default_timing.rename(audiobook_with_timing)

    # Step 5: Generate background images
    bg_dir = output_dir / "episode_backgrounds"
    bg_file = bg_dir / f"episode_01_background.png"

    ret = run_step(
        ['python', 'src/generators/generate_episode_backgrounds.py', str(audiobook_json)],
        f"Step 4/7: Generate Background Images ({book_hash})",
        bg_file
    )
    if ret != 0:
        return ret

    # Step 6: Create episode videos
    video_dir = output_dir / "episode_videos"
    episode_video = video_dir / f"episode_01_final.mp4"

    ret = run_step(
        ['python', 'src/tools/create_episode_videos.py', str(audiobook_json), '--voice-id', args.voice_id],
        f"Step 5/7: Create Episode Videos ({book_hash})",
        episode_video
    )
    if ret != 0:
        return ret

    # Step 7: Generate promotional videos (non-critical - continue even if some fail)
    promo_video_dir = output_dir / "promo_videos"

    ret = run_step(
        ['python', 'src/generators/generate_promotional_videos.py', str(audiobook_with_timing)],
        f"Step 6/7: Generate Promotional Videos ({book_hash}) [non-critical]",
        None  # Multiple outputs, script handles checking
    )
    # Don't fail pipeline if promos fail
    if ret != 0:
        print(f"⚠️  Some promotional videos may have failed, but continuing...")

    # Step 8: Verify files are queued for YouTube upload
    # Note: create_episode_videos.py already queues to ~/upload_queue_main/
    if not args.skip_queue:
        print(f"\n{'='*80}")
        print(f"📤 Files Queued for YouTube Upload")
        print(f"{'='*80}")
        queue_dir = Path(UPLOAD_QUEUE_DIR)
        if queue_dir.exists():
            queued_items = [d for d in queue_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            pending = [d for d in queued_items if not (d / ".uploaded").exists()]
            print(f"   Queue directory: {queue_dir}")
            print(f"   Total items: {len(queued_items)}")
            print(f"   Pending upload: {len(pending)}")
            if pending:
                print(f"   Next to upload: {pending[0].name}")
        print(f"   Upload via: scripts/upload_next_episode.sh")
    else:
        print(f"\n⏭️  Skipping YouTube queue (--skip-queue flag)")

    # Final summary
    print(f"\n{'='*80}")
    print(f"🎉 PIPELINE COMPLETE!")
    print(f"{'='*80}")
    print(f"Book Hash: {book_hash}")
    print(f"Output Directory: {output_dir}")
    print(f"\n📊 Generated Files:")

    # Count files
    if episode_video.exists():
        print(f"   ✅ Episode video: {episode_video.name}")

    shorts = list(promo_video_dir.glob("**/*_SHORT.mp4")) if promo_video_dir.exists() else []
    print(f"   ✅ Promotional shorts: {len(shorts)} videos")

    if bg_file.exists():
        print(f"   ✅ Background image: {bg_file.name}")

    print(f"\n📤 Next Steps:")
    if args.skip_queue:
        print(f"   Queue manually:")
        print(f"   python src/pipelines/audiobook_pipeline_auto.py {args.source} {args.voice_id}")
    else:
        print(f"   Files queued in: {UPLOAD_QUEUE_DIR}")
        print(f"   Cron will upload via: scripts/upload_next_episode.sh")

    print(f"\n   Or upload directly:")
    print(f"   python src/upload/upload_audiobook_to_youtube.py {audiobook_json} --privacy public")

    print(f"{'='*80}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
