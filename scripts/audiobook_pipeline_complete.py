#!/usr/bin/env python3
"""
Complete audiobook-to-YouTube pipeline.

Given a TXT file (or Gutenberg URL) and a voice ID, this script will:
1. Generate audiobook JSON with promotional shorts
2. Generate episode TTS audio
3. Generate promotional short TTS audio
4. Generate abstract background images
5. Create episode videos (opening + background + audio)
6. Generate promotional short videos (Sora + vertical format + ending)
7. (Optional) Upload everything to YouTube

Usage:
    python scripts/audiobook_pipeline_complete.py <book_url_or_txt> --voice-id <voice_id>
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

def run_command(cmd: list, description: str) -> int:
    """Run a command and display its output."""
    print(f"\n{'='*80}")
    print(f"🚀 {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return result.returncode

    print(f"\n✅ {description} completed successfully")
    return 0


def main():
    """Run the complete audiobook pipeline"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Complete audiobook-to-YouTube pipeline'
    )
    parser.add_argument(
        'book_source',
        help='Path to TXT file or Gutenberg URL'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for all generated files'
    )
    parser.add_argument(
        '--voice-id',
        default='ePiPWpzcHZrcqRzFrgQg',
        help='ElevenLabs voice ID for narration'
    )
    parser.add_argument(
        '--infer-chapter',
        action='store_true',
        help='Use semantic chapter inference for books without explicit chapters'
    )
    parser.add_argument(
        '--skip-episode-audio',
        action='store_true',
        help='Skip episode audio generation (use existing)'
    )
    parser.add_argument(
        '--skip-promo-audio',
        action='store_true',
        help='Skip promotional audio generation (use existing)'
    )
    parser.add_argument(
        '--skip-backgrounds',
        action='store_true',
        help='Skip background image generation (use existing)'
    )
    parser.add_argument(
        '--skip-episode-videos',
        action='store_true',
        help='Skip episode video generation (use existing)'
    )
    parser.add_argument(
        '--skip-promo-videos',
        action='store_true',
        help='Skip promotional video generation (use existing)'
    )
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload to YouTube after generation'
    )
    parser.add_argument(
        '--upload-privacy',
        default='public',
        choices=['public', 'private', 'unlisted'],
        help='Privacy setting for YouTube uploads'
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    audiobook_json = output_dir / "audiobook.json"
    audiobook_with_timing = output_dir / "audiobook_with_timing.json"

    print(f"\n{'='*80}")
    print(f"📚 COMPLETE AUDIOBOOK PIPELINE")
    print(f"{'='*80}")
    print(f"Source: {args.book_source}")
    print(f"Output: {output_dir}")
    print(f"Voice ID: {args.voice_id}")
    print(f"Infer Chapters: {args.infer_chapter}")
    print(f"Upload to YouTube: {args.upload}")
    print(f"{'='*80}\n")

    # Step 1: Generate audiobook JSON with promotional shorts
    if not audiobook_json.exists():
        cmd = [
            'python', 'scripts/book_to_audiobook.py',
            args.book_source,
            '--output-dir', str(output_dir)
        ]
        if args.infer_chapter:
            cmd.append('--infer-chapter')

        ret = run_command(cmd, "Step 1: Generate Audiobook JSON")
        if ret != 0:
            return ret
    else:
        print(f"\n✓ Audiobook JSON already exists: {audiobook_json}")

    # Step 2: Generate episode audio
    if not args.skip_episode_audio:
        cmd = [
            'python', 'scripts/generate_audiobook_audio.py',
            str(audiobook_json),
            '--voice-id', args.voice_id
        ]

        ret = run_command(cmd, "Step 2: Generate Episode Audio (TTS)")
        if ret != 0:
            return ret
    else:
        print("\n⏭️  Skipping episode audio generation")

    # Step 3: Generate promotional audio
    if not args.skip_promo_audio:
        cmd = [
            'python', 'scripts/generate_promotional_audio.py',
            str(audiobook_json),
            '--voice-id', args.voice_id
        ]

        ret = run_command(cmd, "Step 3: Generate Promotional Audio (TTS)")
        if ret != 0:
            return ret
    else:
        print("\n⏭️  Skipping promotional audio generation")

    # Step 4: Generate background images
    if not args.skip_backgrounds:
        cmd = [
            'python', 'scripts/generate_episode_backgrounds.py',
            str(audiobook_json)
        ]

        ret = run_command(cmd, "Step 4: Generate Background Images (DALL-E)")
        if ret != 0:
            return ret
    else:
        print("\n⏭️  Skipping background image generation")

    # Step 5: Create episode videos
    if not args.skip_episode_videos:
        cmd = [
            'python', 'scripts/create_episode_videos.py',
            str(audiobook_json),
            '--voice-id', args.voice_id
        ]

        ret = run_command(cmd, "Step 5: Create Episode Videos (opening + background + audio)")
        if ret != 0:
            return ret
    else:
        print("\n⏭️  Skipping episode video generation")

    # Step 6: Generate promotional videos
    if not args.skip_promo_videos:
        cmd = [
            'python', 'scripts/generate_promotional_videos.py',
            str(audiobook_with_timing)
        ]

        ret = run_command(cmd, "Step 6: Generate Promotional Videos (Sora + vertical + ending)")
        if ret != 0:
            return ret
    else:
        print("\n⏭️  Skipping promotional video generation")

    # Step 7: Upload to YouTube (optional)
    if args.upload:
        cmd = [
            'python', 'scripts/upload_audiobook_to_youtube.py',
            str(audiobook_json),
            '--privacy', args.upload_privacy
        ]

        ret = run_command(cmd, "Step 7: Upload to YouTube")
        if ret != 0:
            print("\n⚠️  Upload failed, but files are ready")
    else:
        print("\n⏭️  Skipping YouTube upload (use --upload flag to enable)")

    # Final summary
    print(f"\n{'='*80}")
    print(f"🎉 PIPELINE COMPLETE!")
    print(f"{'='*80}")
    print(f"✅ All files generated successfully")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"   • audiobook.json - Main metadata")
    print(f"   • audiobook_with_timing.json - With timing data")
    print(f"   • episode_audio/ - Episode MP3 files")
    print(f"   • episode_backgrounds/ - Abstract background images")
    print(f"   • episode_videos/ - Final episode videos")
    print(f"   • promo_audio/ - Promotional short audio")
    print(f"   • promo_videos/ - Promotional short videos")

    if not args.upload:
        print(f"\n📺 To upload to YouTube:")
        print(f"   python scripts/upload_audiobook_to_youtube.py {audiobook_json}")

    print(f"\n💾 For Mac Mini transfer:")
    print(f"   1. Copy {output_dir} to Mac Mini")
    print(f"   2. Use scheduled upload script on Mac Mini")
    print(f"{'='*80}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
