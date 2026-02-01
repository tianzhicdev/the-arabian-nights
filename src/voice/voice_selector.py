#!/usr/bin/env python3
"""
Voice Selector for ElevenLabs
Automatically selects appropriate voices based on character descriptions
"""

import os
import sys
import json
import requests
import random
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.secrets")

API_KEY = os.getenv("ELEVEN_LABS_KEY")
API_URL = "https://api.elevenlabs.io/v1/voices"


def fetch_available_voices() -> List[Dict]:
    """Fetch all available voices from ElevenLabs API"""
    headers = {"xi-api-key": API_KEY}

    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("voices", [])
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return []


def filter_voices(voices: List[Dict],
                  gender: Optional[str] = None,
                  age: Optional[str] = None,
                  accent: Optional[str] = None,
                  descriptive: Optional[str] = None) -> List[Dict]:
    """
    Filter voices by criteria

    Args:
        gender: "male", "female", "neutral"
        age: "young", "middle_aged", "old"
        accent: "american", "british", etc.
        descriptive: any descriptive tag like "casual", "warm", "energetic"
    """
    filtered = voices

    if gender:
        filtered = [v for v in filtered if v.get("labels", {}).get("gender") == gender]

    if age:
        filtered = [v for v in filtered if v.get("labels", {}).get("age") == age]

    if accent:
        filtered = [v for v in filtered if v.get("labels", {}).get("accent") == accent]

    if descriptive:
        filtered = [v for v in filtered
                   if descriptive.lower() in v.get("labels", {}).get("descriptive", "").lower()]

    return filtered


def select_voice_for_character(character_description: str,
                               avoid_voice_ids: List[str] = None) -> Optional[Dict]:
    """
    Automatically select a voice based on character description

    Args:
        character_description: Text describing the character (e.g., "male, middle-aged, warm")
        avoid_voice_ids: List of voice IDs to avoid (for ensuring different voices)

    Returns:
        Dict with voice info or None
    """
    voices = fetch_available_voices()
    if not voices:
        return None

    avoid_voice_ids = avoid_voice_ids or []
    desc_lower = character_description.lower()

    # Detect gender
    gender = None
    if "male" in desc_lower and "female" not in desc_lower:
        gender = "male"
    elif "female" in desc_lower:
        gender = "female"

    # Detect age
    age = None
    if "young" in desc_lower:
        age = "young"
    elif "middle" in desc_lower or "middle-aged" in desc_lower:
        age = "middle_aged"
    elif "old" in desc_lower:
        age = "old"

    # Detect accent
    accent = None
    if "american" in desc_lower:
        accent = "american"
    elif "british" in desc_lower or "british" in desc_lower:
        accent = "british"

    # Filter voices
    filtered = filter_voices(voices, gender=gender, age=age, accent=accent)

    # Exclude already used voices
    filtered = [v for v in filtered if v["voice_id"] not in avoid_voice_ids]

    if not filtered:
        # Fallback: use any voice not in avoid list
        filtered = [v for v in voices if v["voice_id"] not in avoid_voice_ids]

    if not filtered:
        return None

    # Randomly select from filtered voices
    return random.choice(filtered)


def list_voices(gender: Optional[str] = None,
                age: Optional[str] = None,
                detailed: bool = False):
    """List available voices with optional filtering"""
    voices = fetch_available_voices()

    if gender or age:
        voices = filter_voices(voices, gender=gender, age=age)

    print(f"\n{'='*70}")
    print(f"AVAILABLE ELEVENLABS VOICES ({len(voices)} found)")
    print(f"{'='*70}\n")

    for voice in voices:
        labels = voice.get("labels", {})
        name = voice.get("name", "Unknown")
        voice_id = voice.get("voice_id", "")

        gender_label = labels.get("gender", "?")
        age_label = labels.get("age", "?")
        accent_label = labels.get("accent", "?")

        print(f"  {name}")
        print(f"    ID: {voice_id}")
        print(f"    Gender: {gender_label}, Age: {age_label}, Accent: {accent_label}")

        if detailed:
            desc = voice.get("description", "")
            if desc:
                print(f"    Description: {desc}")

        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ElevenLabs Voice Selector")
    parser.add_argument('--list', action='store_true', help='List all available voices')
    parser.add_argument('--gender', choices=['male', 'female', 'neutral'], help='Filter by gender')
    parser.add_argument('--age', choices=['young', 'middle_aged', 'old'], help='Filter by age')
    parser.add_argument('--detailed', action='store_true', help='Show detailed info')
    parser.add_argument('--select', type=str, help='Auto-select voice for character description')
    parser.add_argument('--avoid', type=str, help='Comma-separated voice IDs to avoid')

    args = parser.parse_args()

    if args.list:
        list_voices(gender=args.gender, age=args.age, detailed=args.detailed)

    elif args.select:
        avoid_ids = args.avoid.split(',') if args.avoid else []
        voice = select_voice_for_character(args.select, avoid_voice_ids=avoid_ids)

        if voice:
            print(f"\n✓ Selected voice: {voice['name']}")
            print(f"  Voice ID: {voice['voice_id']}")
            print(f"  Gender: {voice['labels'].get('gender', '?')}")
            print(f"  Age: {voice['labels'].get('age', '?')}")
            print(f"  Description: {voice.get('description', 'N/A')}\n")
        else:
            print("✗ No suitable voice found\n")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
