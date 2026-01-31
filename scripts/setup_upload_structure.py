#!/usr/bin/env python3
"""
Set up directory structure and metadata for scheduled uploads.
Creates metadata.json for each episode.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

# Episode metadata
EPISODES = [
    {
        "episode_number": 1,
        "video_filename": "Episode_01_Old_Majors_Dream.mp4",
        "title": "Animal Farm Episode 1: Old Major's Dream | George Orwell Classic",
        "subtitle": "Old Major's Dream",
        "description": """In this first episode of George Orwell's timeless allegory, the wise boar Old Major gathers the animals of Manor Farm to share his revolutionary vision of a world free from human oppression. His powerful dream of animal equality and freedom plants the seeds of rebellion.

📚 About Animal Farm:
Animal Farm is George Orwell's 1945 allegorical novella about a group of farm animals who rebel against their human farmer, hoping to create a society where animals can be equal, free, and happy. The story is a brilliant critique of totalitarianism and a warning about the corruption of revolutionary ideals.

🎓 Educational Value:
• Understand political allegory and symbolism
• Explore themes of power, corruption, and propaganda
• Analyze historical parallels to the Russian Revolution
• Examine leadership and social structures

📖 This is part of a complete audiovisual adaptation of Animal Farm, bringing Orwell's classic to life with AI-generated narration and artistic visualizations.

🎬 Narrated by Wormhole Podcast
🎨 Visual adaptation using AI-generated art

#AnimalFarm #GeorgeOrwell #ClassicLiterature #Education #Audiobook #Literature #PoliticalAllegory""",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "dystopian", "Manor Farm", "Old Major", "educational video", "book adaptation", "narration"],
        "uploaded": True,  # Already uploaded
        "youtube_video_id": "G-ASPOL4_6E",
        "youtube_url": "https://www.youtube.com/watch?v=G-ASPOL4_6E",
        "upload_date": "2026-01-30"
    },
    {
        "episode_number": 2,
        "video_filename": "Episode_02_The_Rebellion_Begins.mp4",
        "title": "Animal Farm Episode 2: The Rebellion Begins | George Orwell Classic",
        "subtitle": "The Rebellion Begins",
        "description": """Following Old Major's death, the animals of Manor Farm rise up in a spontaneous rebellion against Mr. Jones. The revolution succeeds beyond their wildest dreams, and they rename the farm "Animal Farm." The Seven Commandments are established, and a new era of animal rule begins with hope and optimism.

📚 About Animal Farm:
Animal Farm is George Orwell's 1945 allegorical novella about a group of farm animals who rebel against their human farmer, hoping to create a society where animals can be equal, free, and happy. The story is a brilliant critique of totalitarianism and a warning about the corruption of revolutionary ideals.

🎓 Educational Value:
• Understand political allegory and symbolism
• Explore themes of power, corruption, and propaganda
• Analyze historical parallels to the Russian Revolution
• Examine leadership and social structures

📖 This is part of a complete audiovisual adaptation of Animal Farm, bringing Orwell's classic to life with AI-generated narration and artistic visualizations.

🎬 Narrated by Wormhole Podcast
🎨 Visual adaptation using AI-generated art

Previous Episode: https://www.youtube.com/watch?v=G-ASPOL4_6E

#AnimalFarm #GeorgeOrwell #ClassicLiterature #Education #Audiobook #Literature #PoliticalAllegory""",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "dystopian", "Manor Farm", "Rebellion", "educational video", "book adaptation", "narration"]
    },
    {
        "episode_number": 3,
        "video_filename": "Episode_03_The_Summer_of_Hope.mp4",
        "title": "Animal Farm Episode 3: The Summer of Hope | George Orwell Classic",
        "subtitle": "The Summer of Hope",
        "description": """The animals work together to bring in the harvest, which proves to be the most successful in the farm's history. Snowball and Napoleon begin to emerge as leaders, establishing Sunday meetings and committees. The pigs start to consolidate their power as the brains of the farm, while Boxer's dedication becomes legendary.

📚 About Animal Farm:
Animal Farm is George Orwell's 1945 allegorical novella about a group of farm animals who rebel against their human farmer, hoping to create a society where animals can be equal, free, and happy. The story is a brilliant critique of totalitarianism and a warning about the corruption of revolutionary ideals.

🎓 Educational Value:
• Understand political allegory and symbolism
• Explore themes of power, corruption, and propaganda
• Analyze historical parallels to the Russian Revolution
• Examine leadership and social structures

📖 This is part of a complete audiovisual adaptation of Animal Farm, bringing Orwell's classic to life with AI-generated narration and artistic visualizations.

🎬 Narrated by Wormhole Podcast
🎨 Visual adaptation using AI-generated art

#AnimalFarm #GeorgeOrwell #ClassicLiterature #Education #Audiobook #Literature #PoliticalAllegory""",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "dystopian", "Snowball", "Napoleon", "Boxer", "educational video", "book adaptation", "narration"]
    },
    # Episodes 4-10 with similar structure
]

# Add episodes 4-10
EPISODES.extend([
    {
        "episode_number": 4,
        "video_filename": "Episode_04_The_Battle_of_the_Cowshed.mp4",
        "title": "Animal Farm Episode 4: The Battle of the Cowshed | George Orwell Classic",
        "subtitle": "The Battle of the Cowshed",
        "description": "Mr. Jones and his men attempt to reclaim the farm... [Same educational content structure]",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "Battle of Cowshed", "educational video", "book adaptation"]
    },
    {
        "episode_number": 5,
        "video_filename": "Episode_05_The_Rise_of_Napoleon.mp4",
        "title": "Animal Farm Episode 5: The Rise of Napoleon | George Orwell Classic",
        "subtitle": "The Rise of Napoleon",
        "description": "The conflict between Snowball and Napoleon reaches its climax...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "Napoleon", "dictatorship"]
    },
    {
        "episode_number": 6,
        "video_filename": "Episode_06_The_Price_of_Progress.mp4",
        "title": "Animal Farm Episode 6: The Price of Progress | George Orwell Classic",
        "subtitle": "The Price of Progress",
        "description": "The animals work harder than ever to build Napoleon's windmill...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "windmill"]
    },
    {
        "episode_number": 7,
        "video_filename": "Episode_07_The_Bitter_Winter.mp4",
        "title": "Animal Farm Episode 7: The Bitter Winter | George Orwell Classic",
        "subtitle": "The Bitter Winter",
        "description": "A harsh winter brings famine to Animal Farm...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "famine", "purges"]
    },
    {
        "episode_number": 8,
        "video_filename": "Episode_08_The_Battle_of_the_Windmill.mp4",
        "title": "Animal Farm Episode 8: The Battle of the Windmill | George Orwell Classic",
        "subtitle": "The Battle of the Windmill",
        "description": "Frederick and his men attack Animal Farm with explosives...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "Battle of Windmill"]
    },
    {
        "episode_number": 9,
        "video_filename": "Episode_09_The_Fate_of_Boxer.mp4",
        "title": "Animal Farm Episode 9: The Fate of Boxer | George Orwell Classic",
        "subtitle": "The Fate of Boxer",
        "description": "The loyal and hardworking Boxer collapses from exhaustion...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "Boxer", "betrayal"]
    },
    {
        "episode_number": 10,
        "video_filename": "Episode_10_The_Final_Betrayal.mp4",
        "title": "Animal Farm Episode 10: The Final Betrayal | George Orwell Classic",
        "subtitle": "The Final Betrayal",
        "description": "Years pass, and the farm prospers under Napoleon's rule, but only the pigs benefit...",
        "tags": ["Animal Farm", "George Orwell", "classic literature", "audiobook", "education", "literature", "political allegory", "finale", "conclusion"]
    }
])


def setup_upload_directory():
    """Set up organized directory structure for uploads."""

    # Source and destination directories
    source_dir = Path("production_ready/animal_farm/with-openning")
    dest_base = Path("production_ready/animal_farm_uploads")

    print(f"Setting up upload directory structure...")
    print(f"Source: {source_dir}")
    print(f"Destination: {dest_base}")

    # Create base directory
    dest_base.mkdir(parents=True, exist_ok=True)

    for episode in EPISODES:
        ep_num = episode['episode_number']
        ep_dir = dest_base / f"episode_{ep_num:02d}"
        ep_dir.mkdir(exist_ok=True)

        # Create metadata.json
        metadata = {
            "episode_number": ep_num,
            "video_filename": episode['video_filename'],
            "title": episode['title'],
            "subtitle": episode['subtitle'],
            "description": episode['description'],
            "tags": episode['tags'],
            "category_id": "27",  # Education
            "privacy_status": "public",
            "uploaded": episode.get('uploaded', False),
            "youtube_video_id": episode.get('youtube_video_id', None),
            "youtube_url": episode.get('youtube_url', None),
            "upload_date": episode.get('upload_date', None)
        }

        metadata_file = ep_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Created metadata: {metadata_file}")

        # Copy or link video file
        source_video = source_dir / episode['video_filename']
        dest_video = ep_dir / episode['video_filename']

        if source_video.exists() and not dest_video.exists():
            # Create hard link (saves space)
            try:
                dest_video.hardlink_to(source_video)
                print(f"✓ Linked video: {dest_video.name}")
            except:
                # Fallback to copy
                shutil.copy2(source_video, dest_video)
                print(f"✓ Copied video: {dest_video.name}")
        elif dest_video.exists():
            print(f"  Video already exists: {dest_video.name}")
        else:
            print(f"⚠️  Source video not found: {source_video}")

        # Create .uploaded marker if already uploaded
        if episode.get('uploaded'):
            uploaded_marker = ep_dir / ".uploaded"
            uploaded_marker.write_text(f"{episode['youtube_url']}\n{episode['upload_date']}\n")
            print(f"✓ Created upload marker (already uploaded)")

        print()

    print(f"✅ Setup complete!")
    print(f"Upload directory: {dest_base.absolute()}")
    print(f"\nReady to sync to Mac Mini with:")
    print(f"rsync -avz {dest_base}/ macmini:~/animal_farm_uploads/")


if __name__ == '__main__':
    setup_upload_directory()
