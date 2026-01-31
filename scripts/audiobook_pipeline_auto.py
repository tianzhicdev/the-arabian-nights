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

# Mac Mini transfer configuration
MAC_MINI_HOST = os.getenv("MAC_MINI_HOST", "macmini.local")
MAC_MINI_USER = os.getenv("MAC_MINI_USER", "user")
MAC_MINI_UPLOAD_DIR = os.getenv("MAC_MINI_UPLOAD_DIR", "/Users/user/youtube_upload_queue")


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


def transfer_to_mac_mini(local_dir: Path, book_hash: str) -> bool:
    """
    Transfer completed audiobook to Mac Mini upload queue.

    Args:
        local_dir: Local directory with generated files
        book_hash: Book hash identifier

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"📤 Transferring to Mac Mini")
    print(f"{'='*80}")

    # Create remote directory name
    remote_dir = f"{MAC_MINI_UPLOAD_DIR}/{book_hash}"

    # Check if Mac Mini is accessible
    print(f"Checking Mac Mini accessibility...")
    check_cmd = ['ssh', f'{MAC_MINI_USER}@{MAC_MINI_HOST}', 'echo "Connected"']
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"⚠️  Mac Mini not accessible at {MAC_MINI_USER}@{MAC_MINI_HOST}")
        print(f"   Skipping transfer. Files remain at: {local_dir}")
        print(f"   Manual transfer command:")
        print(f"   scp -r {local_dir} {MAC_MINI_USER}@{MAC_MINI_HOST}:{remote_dir}")
        return False

    print(f"✓ Mac Mini accessible")

    # Create remote directory
    print(f"Creating remote directory: {remote_dir}")
    mkdir_cmd = ['ssh', f'{MAC_MINI_USER}@{MAC_MINI_HOST}', f'mkdir -p {remote_dir}']
    subprocess.run(mkdir_cmd)

    # Transfer files
    print(f"Transferring files from {local_dir}...")
    transfer_cmd = ['scp', '-r', str(local_dir) + '/', f'{MAC_MINI_USER}@{MAC_MINI_HOST}:{remote_dir}/']
    result = subprocess.run(transfer_cmd)

    if result.returncode == 0:
        print(f"✅ Files transferred successfully to Mac Mini")
        print(f"   Remote location: {MAC_MINI_USER}@{MAC_MINI_HOST}:{remote_dir}")
        return True
    else:
        print(f"❌ Transfer failed")
        return False


def main():
    """Run the complete automated pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fully automated audiobook pipeline with hash-based naming',
        epilog='Example: python scripts/audiobook_pipeline_auto.py book.txt ePiPWpzcHZrcqRzFrgQg'
    )
    parser.add_argument('source', help='Text file path or URL')
    parser.add_argument('voice_id', help='ElevenLabs voice ID')
    parser.add_argument('--no-transfer', action='store_true', help='Skip Mac Mini transfer')
    parser.add_argument('--base-dir', default='experiments/audiobook_pipeline',
                       help='Base directory for output (default: experiments/audiobook_pipeline)')

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"🚀 AUTOMATED AUDIOBOOK PIPELINE")
    print(f"{'='*80}")
    print(f"Source: {args.source}")
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
        ['python', 'scripts/book_to_audiobook.py', args.source, '--output-dir', str(output_dir)],
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
    audio_dir = output_dir / "audio"
    episode_audio = audio_dir / f"{book_hash}_episode_01.mp3"

    ret = run_step(
        ['python', 'scripts/generate_audiobook_audio.py', str(audiobook_json), '--voice-id', args.voice_id],
        f"Step 2/7: Generate Episode Audio ({book_hash})",
        None  # Check will be done by script internally
    )
    if ret != 0:
        return ret

    # Step 4: Generate promotional audio
    promo_audio_dir = output_dir / "promo_audio"

    ret = run_step(
        ['python', 'scripts/generate_promotional_audio.py', str(audiobook_json), '--voice-id', args.voice_id],
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
        ['python', 'scripts/generate_episode_backgrounds.py', str(audiobook_json)],
        f"Step 4/7: Generate Background Images ({book_hash})",
        bg_file
    )
    if ret != 0:
        return ret

    # Step 6: Create episode videos
    video_dir = output_dir / "episode_videos"
    episode_video = video_dir / f"episode_01_final.mp4"

    ret = run_step(
        ['python', 'scripts/create_episode_videos.py', str(audiobook_json), '--voice-id', args.voice_id],
        f"Step 5/7: Create Episode Videos ({book_hash})",
        episode_video
    )
    if ret != 0:
        return ret

    # Step 7: Generate promotional videos (non-critical - continue even if some fail)
    promo_video_dir = output_dir / "promo_videos"

    ret = run_step(
        ['python', 'scripts/generate_promotional_videos.py', str(audiobook_with_timing)],
        f"Step 6/7: Generate Promotional Videos ({book_hash}) [non-critical]",
        None  # Multiple outputs, script handles checking
    )
    # Don't fail pipeline if promos fail
    if ret != 0:
        print(f"⚠️  Some promotional videos may have failed, but continuing...")

    # Step 8: Transfer to Mac Mini (optional)
    if not args.no_transfer:
        transfer_to_mac_mini(output_dir, book_hash)
    else:
        print(f"\n⏭️  Skipping Mac Mini transfer (--no-transfer flag)")

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
    if args.no_transfer:
        print(f"   Manual transfer to Mac Mini:")
        print(f"   scp -r {output_dir} {MAC_MINI_USER}@{MAC_MINI_HOST}:{MAC_MINI_UPLOAD_DIR}/{book_hash}")
    else:
        print(f"   Files are ready for Mac Mini scheduled upload")

    print(f"\n   Or upload directly:")
    print(f"   python scripts/upload_audiobook_to_youtube.py {audiobook_json} --privacy public")

    print(f"{'='*80}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
