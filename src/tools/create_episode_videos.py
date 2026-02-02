#!/usr/bin/env python3
"""
Create complete episode videos: opening + (background + audio).

Combines:
1. Opening segment (logo + narration)
2. Main content (background image + episode audio)
3. Outputs to upload queue at ~/upload_queue_main/

Usage:
    python scripts/create_episode_videos.py <audiobook.json>
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('.env.secrets')

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_KEY")
DEFAULT_VOICE_ID = "ePiPWpzcHZrcqRzFrgQg"  # Default narrator voice
LOGO_PATH = Path("resources/wornhole-logo.png")  # Note: typo in original filename
VIDEO_SIZE = "1280x720"  # Horizontal format for main audiobook
UPLOAD_QUEUE_BASE = Path.home() / "upload_queue_main"


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def generate_opening_audio(
    book_title: str,
    author: str,
    episode_number: int,
    voice_id: str,
    api_key: str,
    output_path: Path,
    is_single_episode: bool = False
) -> float:
    """Generate opening narration using ElevenLabs."""
    import requests

    # For single-episode books, don't include episode number
    if is_single_episode:
        text = f"{book_title} by {author}. Narrated by Wormhole Podcast."
    else:
        # Convert episode number to word
        episode_words = {
            1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
            6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
            11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen",
            16: "Sixteen", 17: "Seventeen", 18: "Eighteen", 19: "Nineteen", 20: "Twenty"
        }
        episode_word = episode_words.get(episode_number, str(episode_number))
        text = f"{book_title} by {author}. Episode {episode_word}. Narrated by Wormhole Podcast."

    print(f"       Generating opening narration...")
    print(f"         Text: {text}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    # Save MP3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(response.content)

    duration = get_audio_duration(output_path)
    print(f"         ✓ Opening audio: {duration:.2f}s")

    return duration


def create_opening_video(
    logo_path: Path,
    audio_path: Path,
    output_path: Path,
    silence_duration: float = 1.5
) -> Path:
    """Create opening video with logo and audio."""
    audio_duration = get_audio_duration(audio_path)
    total_duration = audio_duration + silence_duration

    print(f"       Creating opening video...")
    print(f"         Duration: {total_duration:.2f}s")

    if logo_path.exists():
        # Create video with logo centered on black background
        filter_complex = (
            f"color=c=black:s={VIDEO_SIZE}:d={total_duration}:r=30[bg];"
            f"[1:v]scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease[logo];"
            f"[bg][logo]overlay=(W-w)/2:(H-h)/2[v]"
        )

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s={VIDEO_SIZE}:d={total_duration}:r=30',
            '-i', str(logo_path),
            '-i', str(audio_path),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-map', '2:a',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-t', str(total_duration),
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
    else:
        print(f"         Warning: Logo not found at {logo_path}, using black background")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s={VIDEO_SIZE}:d={total_duration}:r=30',
            '-i', str(audio_path),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    print(f"         ✓ Opening video created")
    return output_path


def create_background_video(
    background_image: Path,
    audio_path: Path,
    output_path: Path
) -> Path:
    """Create video from background image + audio."""
    audio_duration = get_audio_duration(audio_path)

    print(f"       Creating main video from background + audio...")
    print(f"         Duration: {audio_duration:.2f}s")

    # Create video: loop background image for audio duration
    # Scale background image to match opening video resolution (1280x720)
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', str(background_image),
        '-i', str(audio_path),
        '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-t', str(audio_duration),
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    print(f"         ✓ Main video created")
    return output_path


def concatenate_videos(video_files: List[Path], output_path: Path) -> Path:
    """Concatenate opening + main video."""
    print(f"       Concatenating opening + main video...")

    # Create concat list
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video in video_files:
            f.write(f"file '{video.absolute()}'\n")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink()  # Clean up

    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    print(f"         ✓ Final video created")
    return output_path


def create_upload_metadata(
    audiobook: Dict,
    episode_number: int,
    video_filename: str,
    subtitle: str,
    is_single_episode: bool = False
) -> Dict:
    """Create metadata.json for upload queue."""
    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']

    # Get episode info if available
    episodes = audiobook.get('episodes', [])
    episode_info = None
    for ep in episodes:
        if ep.get('episode_number') == episode_number:
            episode_info = ep
            break

    # For single-episode books, don't include episode number in title
    if is_single_episode:
        title = f"{book_title} | {author} | Classics Retold"
        desc_header = f"{book_title}"
    else:
        title = f"{book_title} Episode {episode_number}: {subtitle} | Classics Retold"
        desc_header = f"Episode {episode_number}: {subtitle}"

    # Build description
    description = f"""{desc_header}

📚 About {book_title}:
{audiobook['metadata'].get('description', f'{book_title} by {author}')}

🎓 Educational Value:
• Understand key themes and literary techniques
• Explore character development and plot structure
• Analyze historical and cultural context

📖 This is part of a complete audiovisual adaptation, bringing the classic to life with AI-generated narration and artistic visualizations.

🎬 Narrated by Wormhole Podcast
🎨 Visual adaptation using AI-generated art

#{book_title.replace(' ', '')} #{author.replace(' ', '')} #ClassicLiterature #Education #Audiobook #Literature"""

    return {
        "episode_number": episode_number,
        "video_filename": video_filename,
        "title": title,
        "subtitle": subtitle if not is_single_episode else book_title,
        "description": description,
        "tags": [
            book_title,
            author,
            "classic literature",
            "audiobook",
            "education",
            "literature",
            "educational video",
            "book adaptation",
            "full audiobook" if is_single_episode else "narration"
        ],
        "category_id": "27",  # Education
        "privacy_status": "public",
        "uploaded": False,
        "youtube_video_id": None,
        "youtube_url": None,
        "upload_date": None,
        "creation_date": datetime.now().isoformat(),
        "creation_timestamp": datetime.now().timestamp()
    }


def process_episode(
    audiobook: Dict,
    episode_number: int,
    audio_dir: Path,
    bg_dir: Path,
    queue_base: Path,
    voice_id: str,
    api_key: str,
    is_single_episode: bool = False,
    skip_opening: bool = False
) -> Optional[Path]:
    """
    Create complete video for one episode and place in upload queue.

    Returns:
        Path to final video in queue or None if failed
    """
    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']

    # Create sanitized name for queue directory
    book_slug = book_title.lower().replace(' ', '_').replace("'", "")
    if is_single_episode:
        queue_name = book_slug  # No episode suffix for single-episode books
    else:
        queue_name = f"{book_slug}_ep{episode_number:02d}"
    queue_dir = queue_base / queue_name
    queue_dir.mkdir(parents=True, exist_ok=True)

    if is_single_episode:
        print(f"\n  Full Audiobook:")
    else:
        print(f"\n  Episode {episode_number}:")
    print(f"    Queue: {queue_name}")

    # Find episode audio file
    # Try multiple formats: episode-based, chapter-based, and wildcard
    episode_audio = audio_dir / f"episode_{episode_number:02d}.mp3"
    if not episode_audio.exists():
        # Try chapter format
        episode_audio = audio_dir / f"chapter_{episode_number:02d}.mp3"

    if not episode_audio.exists():
        # Try wildcard pattern (e.g., unknown_episode_01.mp3 or title_episode_01.mp3)
        pattern = f"*_episode_{episode_number:02d}.mp3"
        matches = list(audio_dir.glob(pattern))
        if matches:
            episode_audio = matches[0]

    if not episode_audio.exists():
        print(f"    ✗ Audio file not found: {episode_audio}")
        return None

    # Find background image
    background_image = bg_dir / f"episode_{episode_number:02d}_background.png"
    if not background_image.exists():
        print(f"    ✗ Background image not found: {background_image}")
        return None

    # Get episode subtitle
    episodes = audiobook.get('episodes', [])
    if is_single_episode:
        subtitle = book_title  # Use book title for single-episode
    else:
        subtitle = f"Episode {episode_number}"
        for ep in episodes:
            if ep.get('episode_number') == episode_number:
                subtitle = ep.get('subtitle', subtitle)
                break

    # Output paths
    temp_dir = queue_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    opening_audio = temp_dir / "opening_audio.mp3"
    opening_video = temp_dir / "opening_video.mp4"
    main_video = temp_dir / "main_video.mp4"

    # Final video filename
    if is_single_episode:
        video_filename = f"{queue_name}.mp4"  # Simple name for single episode
    else:
        subtitle_slug = subtitle.replace(' ', '_').replace("'", "")
        video_filename = f"{queue_name}_{subtitle_slug}.mp4"
    final_video = queue_dir / video_filename
    metadata_file = queue_dir / "metadata.json"

    # Skip if final video and metadata exist
    if final_video.exists() and metadata_file.exists():
        print(f"    ⏭️  Video exists in queue, skipping")
        return final_video

    try:
        if skip_opening:
            # Skip opening - just create main video directly
            print(f"    Step 1: Create main content (no opening)...")
            create_background_video(
                background_image=background_image,
                audio_path=episode_audio,
                output_path=final_video  # Output directly to final path
            )
            print(f"    Step 2: Create metadata...")
        else:
            # Step 1: Generate opening audio
            print(f"    Step 1: Generate opening...")
            generate_opening_audio(
                book_title=book_title,
                author=author,
                episode_number=episode_number,
                voice_id=voice_id,
                api_key=api_key,
                output_path=opening_audio,
                is_single_episode=is_single_episode
            )

            # Step 2: Create opening video
            create_opening_video(
                logo_path=LOGO_PATH,
                audio_path=opening_audio,
                output_path=opening_video
            )

            # Step 3: Create main video (background + episode audio)
            print(f"    Step 2: Create main content...")
            create_background_video(
                background_image=background_image,
                audio_path=episode_audio,
                output_path=main_video
            )

            # Step 4: Concatenate opening + main
            print(f"    Step 3: Combine opening + main...")
            concatenate_videos(
                video_files=[opening_video, main_video],
                output_path=final_video
            )

            print(f"    Step 4: Create metadata...")

        # Create metadata.json
        metadata = create_upload_metadata(
            audiobook=audiobook,
            episode_number=episode_number,
            video_filename=video_filename,
            subtitle=subtitle,
            is_single_episode=is_single_episode
        )

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        if is_single_episode:
            print(f"    ✓ Full audiobook complete!")
        else:
            print(f"    ✓ Episode {episode_number} complete!")
        print(f"      Duration: {get_audio_duration(final_video):.1f}s")
        print(f"      Queue: {queue_dir}")
        print(f"      Video: {video_filename}")

        return final_video

    except Exception as e:
        print(f"    ✗ Episode {episode_number} failed: {e}")
        return None


def process_audiobook(
    audiobook_path: Path,
    audio_dir: Path,
    bg_dir: Path,
    queue_base: Path,
    voice_id: str,
    api_key: str,
    skip_opening: bool = False
) -> int:
    """
    Create episode videos for all episodes in audiobook.
    Videos are placed in upload queue at ~/upload_queue_main/

    Returns:
        Number of videos created
    """
    # Load audiobook
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"🎬 Creating Episode Videos")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    print(f"Format: Opening (logo + narration) + Main (background + audio)")
    print(f"Upload Queue: {queue_base}")
    print(f"{'='*80}")

    created_count = 0

    # Get episodes or chapters
    episodes = audiobook.get('episodes', [])
    if not episodes:
        # Fallback to chapters
        print("\n⚠️  No episodes found, using chapters instead...")
        episodes = [{'episode_number': i + 1} for i in range(len(audiobook['chapters']))]

    # Detect single-episode books
    is_single_episode = len(episodes) == 1

    for episode in episodes:
        episode_num = episode['episode_number']

        result = process_episode(
            audiobook=audiobook,
            episode_number=episode_num,
            audio_dir=audio_dir,
            bg_dir=bg_dir,
            queue_base=queue_base,
            voice_id=voice_id,
            api_key=api_key,
            is_single_episode=is_single_episode,
            skip_opening=skip_opening
        )

        if result:
            created_count += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"✅ Episode Video Creation Complete")
    print(f"{'='*80}")
    if is_single_episode:
        print(f"Created: {created_count}/1 full audiobook video")
    else:
        print(f"Created: {created_count}/{len(episodes)} episode videos")
    print(f"Upload Queue: {queue_base}")
    print(f"{'='*80}\n")

    return created_count


def main():
    """Create episode videos for audiobook"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Create complete episode videos with opening and background'
    )
    parser.add_argument(
        'audiobook_json',
        help='Path to audiobook.json file'
    )
    parser.add_argument(
        '--audio-dir',
        help='Directory with episode audio files (default: same dir + /episode_audio)'
    )
    parser.add_argument(
        '--bg-dir',
        help='Directory with background images (default: same dir + /episode_backgrounds)'
    )
    parser.add_argument(
        '--queue-dir',
        help=f'Upload queue directory (default: {UPLOAD_QUEUE_BASE})'
    )
    parser.add_argument(
        '--voice-id',
        default=DEFAULT_VOICE_ID,
        help=f'ElevenLabs voice ID for opening narration (default: {DEFAULT_VOICE_ID})'
    )
    parser.add_argument(
        '--api-key',
        help='ElevenLabs API key (or set ELEVEN_LABS_KEY env var)'
    )
    parser.add_argument(
        '--skip-opening',
        action='store_true',
        help='Skip opening narration (use when no ElevenLabs API key available)'
    )

    args = parser.parse_args()

    # Get API key (not required if --skip-opening)
    api_key = args.api_key or ELEVENLABS_API_KEY
    if not api_key and not args.skip_opening:
        print("Error: No API key provided. Use --api-key, set ELEVEN_LABS_KEY, or use --skip-opening")
        return 1

    # Load audiobook
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine directories
    audio_dir = Path(args.audio_dir) if args.audio_dir else audiobook_path.parent / "episode_audio"
    bg_dir = Path(args.bg_dir) if args.bg_dir else audiobook_path.parent / "episode_backgrounds"
    queue_dir = Path(args.queue_dir) if args.queue_dir else UPLOAD_QUEUE_BASE

    if not audio_dir.exists():
        print(f"Error: Audio directory not found: {audio_dir}")
        print("Run generate_audiobook_audio.py first!")
        return 1

    if not bg_dir.exists():
        print(f"Error: Background directory not found: {bg_dir}")
        print("Run generate_episode_backgrounds.py first!")
        return 1

    queue_dir.mkdir(parents=True, exist_ok=True)

    # Create videos
    count = process_audiobook(
        audiobook_path=audiobook_path,
        audio_dir=audio_dir,
        bg_dir=bg_dir,
        queue_base=queue_dir,
        voice_id=args.voice_id,
        api_key=api_key,
        skip_opening=args.skip_opening
    )

    return 0 if count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
