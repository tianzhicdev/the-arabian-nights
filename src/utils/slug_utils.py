#!/usr/bin/env python3
"""
Slug and filename utilities for video generation.
"""

import re
import unicodedata


def generate_slug(text: str) -> str:
    """
    Generate a URL-safe slug from text.

    Examples:
        "Crime and Punishment: Episode 1" -> "crime-and-punishment-episode-1"
        "The Midnight Garden!" -> "the-midnight-garden"
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for all filesystems.

    Examples:
        "episode: part 1/2" -> "episode-part-1-2"
        "file<name>.txt" -> "file-name-.txt"
    """
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '-', filename)
    filename = filename.strip('-')

    return filename


def create_output_filename(slug: str, suffix: str) -> str:
    """
    Create an output filename with slug and suffix.

    Examples:
        create_output_filename("crime-and-punishment", "final_video.mp4")
        -> "crime-and-punishment_final_video.mp4"
    """
    return f"{slug}_{suffix}"


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "Crime and Punishment: Episode 1",
        "The Midnight Garden - A Test Episode",
        "1984 by George Orwell!",
        "Test   Multiple   Spaces",
        "Spëcîål Çhàráctërs",
    ]

    print("Testing slug generation:\n")
    for text in test_cases:
        slug = generate_slug(text)
        print(f"  {text:45} -> {slug}")

    print("\n" + "=" * 70)
    print("\nTesting filename creation:\n")
    for text in test_cases[:3]:
        slug = generate_slug(text)
        filename = create_output_filename(slug, "final_video.mp4")
        print(f"  {filename}")
