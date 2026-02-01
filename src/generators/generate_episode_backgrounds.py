#!/usr/bin/env python3
"""
Generate abstract background images for audiobook episodes using DALL-E.

Uses Van Gogh impressionist style (reference: resources/styles/vg_converted.jpg)
to create consistent, artistic backgrounds for static audiobook videos.

Usage:
    python scripts/generate_episode_backgrounds.py <audiobook.json>
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.clients.openai_client import OpenAIClient

# Load environment variables
load_dotenv('.env.secrets')

# Configuration
OPENAI_API_KEY = os.getenv("OPEN_AI_API")
DALLE_MODEL = "dall-e-3"
IMAGE_SIZE = "1792x1024"  # Landscape format for horizontal videos
IMAGE_QUALITY = "standard"  # or "hd" for higher quality


def generate_episode_background(
    book_title: str,
    author: str,
    episode_number: int,
    episode_title: str,
    story_summary: str,
    output_path: Path,
    client: OpenAIClient
) -> Path:
    """
    Generate abstract background image for an audiobook episode.

    Args:
        book_title: Title of the book
        author: Author name
        episode_number: Episode number
        episode_title: Episode title
        story_summary: Brief summary of the story for context
        output_path: Where to save the generated image
        client: OpenAIClient instance

    Returns:
        Path to generated image
    """
    print(f"    🎨 Generating background for Episode {episode_number}: {episode_title}...")

    # Create prompt using Van Gogh impressionist style
    prompt = f"""Abstract impressionist painting in the style of Vincent van Gogh for an audiobook episode background.

Book: {book_title} by {author}
Episode: {episode_number} - {episode_title}

Style characteristics:
- Visible, energetic brushstrokes like van Gogh
- Rich, vibrant color palette with golden yellows, deep blues, earth tones
- Swirling, dynamic patterns suggesting movement and emotion
- Impressionistic rather than literal representation
- Atmospheric and moody, evoking the story's themes

Create an abstract background that captures the MOOD and ATMOSPHERE of this literary work.
Focus on: color, texture, movement, emotion
Avoid: specific characters, literal scenes, text, recognizable objects

The image should work as a static background for an audio-focused video."""

    try:
        # Generate image using DALL-E
        print(f"       Calling DALL-E 3...")

        image_url = client.generate_image(
            prompt=prompt,
            model=DALLE_MODEL,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY
        )

        # Download image
        print(f"       Downloading image...")
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        # Save image
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(img_response.content)

        print(f"       ✓ Background saved: {output_path.name}")
        return output_path

    except Exception as e:
        raise Exception(f"Background generation failed: {e}")


def process_audiobook(audiobook_path: Path, bg_dir: Path, client: OpenAIClient) -> int:
    """
    Generate background images for all episodes in audiobook.

    Args:
        audiobook_path: Path to audiobook.json
        bg_dir: Directory to save background images
        client: OpenAIClient instance

    Returns:
        Number of backgrounds generated
    """
    # Load audiobook
    with open(audiobook_path) as f:
        audiobook = json.load(f)

    print(f"\n{'='*80}")
    print(f"🎨 Generating Episode Backgrounds")
    print(f"{'='*80}")
    print(f"Book: {audiobook['metadata']['title']}")
    print(f"Author: {audiobook['metadata']['author']}")
    print(f"Episodes: {len(audiobook.get('episodes', []))}")
    print(f"Style: Van Gogh Impressionist")
    print(f"Output: {bg_dir}")
    print(f"{'='*80}\n")

    # Get story summary
    story_bible = audiobook.get('story_bible', '')
    book_title = audiobook['metadata']['title']
    author = audiobook['metadata']['author']

    generated_count = 0
    episodes = audiobook.get('episodes', [])

    if not episodes:
        print("⚠️  No episodes found. Generating one background per chapter instead...")
        # Fallback: generate one background per chapter
        episodes = [
            {
                "episode_number": i + 1,
                "title": f"Chapter {chapter['chapter_number']}",
                "chapters": [chapter['chapter_number']]
            }
            for i, chapter in enumerate(audiobook['chapters'])
        ]

    for episode in episodes:
        episode_num = episode['episode_number']
        # Get title from episode or from first chapter
        if 'title' in episode:
            episode_title = episode['title']
        elif 'chapters' in episode and len(episode['chapters']) > 0:
            # Get title from first chapter
            episode_title = episode['chapters'][0].get('title', f'Episode {episode_num}')
        else:
            episode_title = f'Episode {episode_num}'

        output_path = bg_dir / f"episode_{episode_num:02d}_background.png"

        # Skip if already exists
        if output_path.exists():
            print(f"  Episode {episode_num}: {episode_title}")
            print(f"    ⏭️  Background already exists, skipping")
            generated_count += 1
            continue

        print(f"  Episode {episode_num}: {episode_title}")

        try:
            generate_episode_background(
                book_title=book_title,
                author=author,
                episode_number=episode_num,
                episode_title=episode_title,
                story_summary=story_bible[:500],  # First 500 chars for context
                output_path=output_path,
                client=client
            )
            generated_count += 1

        except Exception as e:
            print(f"    ✗ Background generation failed: {e}")

    # Summary
    print(f"\n{'='*80}")
    print(f"✅ Background Generation Complete")
    print(f"{'='*80}")
    print(f"Generated: {generated_count}/{len(episodes)} backgrounds")
    print(f"Saved to: {bg_dir}")
    print(f"{'='*80}\n")

    return generated_count


def main():
    """Generate background images for audiobook episodes"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate abstract background images for audiobook episodes'
    )
    parser.add_argument(
        'audiobook_json',
        help='Path to audiobook.json file'
    )
    parser.add_argument(
        '--bg-dir',
        help='Output directory for backgrounds (default: same dir as JSON + /episode_backgrounds)'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key (or set OPEN_AI_API env var)'
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or OPENAI_API_KEY
    if not api_key:
        print("Error: No API key provided. Use --api-key or set OPEN_AI_API environment variable")
        return 1

    # Load audiobook
    audiobook_path = Path(args.audiobook_json)
    if not audiobook_path.exists():
        print(f"Error: Audiobook file not found: {audiobook_path}")
        return 1

    # Determine background directory
    if args.bg_dir:
        bg_dir = Path(args.bg_dir)
    else:
        bg_dir = audiobook_path.parent / "episode_backgrounds"

    bg_dir.mkdir(parents=True, exist_ok=True)

    # Create OpenAI client
    client = OpenAIClient(api_key=api_key)

    # Generate backgrounds
    count = process_audiobook(
        audiobook_path=audiobook_path,
        bg_dir=bg_dir,
        client=client
    )

    return 0 if count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
