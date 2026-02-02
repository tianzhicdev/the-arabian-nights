#!/usr/bin/env python3
"""
Convert a Gutenberg book to an audiobook-ready format with simplified storytelling.

Pipeline:
1. Download/load book from Gutenberg
2. Detect and chunk by chapters (with validation)
3. Create hierarchical summarization -> Story Bible
4. Simplify each chapter using LLM
5. Output JSON + save original text separately

Usage:
    python scripts/book_to_audiobook.py <gutenberg_url> [output_dir] [book_slug]

Examples:
    python scripts/book_to_audiobook.py https://www.gutenberg.org/cache/epub/215/pg215.txt
    python scripts/book_to_audiobook.py https://www.gutenberg.org/cache/epub/84/pg84.txt output/audiobooks/frankenstein frankenstein
"""

import os
import sys
import re
import json
import requests
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env.secrets
load_dotenv('.env.secrets')

# Configuration
OPENAI_API_KEY = os.getenv("OPEN_AI_API")  # Load from .env.secrets
MODEL = "gpt-4o-mini"  # Fast and cost-effective
MAX_TOKENS_PER_CHAPTER = 8000  # Conservative estimate for context window

# Multiple chapter detection patterns with fallback
CHAPTER_PATTERNS = [
    # Pattern 1: Numbered ALL CAPS titles (e.g., "1.  THE END OF AN AGE")
    r'\n\n(\d+\.\s+[A-Z][A-Z\s\-\':]+)\n\n',

    # Pattern 2: "Chapter I. Title" or "Chapter II. Title" (Roman numerals)
    r'\n\n(Chapter\s+[IVXLCDM]+\.?\s+.+?)\n\n',

    # Pattern 3: "Chapter 1" or "CHAPTER 1" (Arabic numerals)
    r'\n\n((?:CHAPTER|Chapter)\s+\d+\.?\s*(?:.+)?)\n\n',

    # Pattern 4: "PART I" or "Part One"
    r'\n\n((?:PART|Part)\s+(?:[IVXLCDM]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\.?\s*(?:.+)?)\n\n',

    # Pattern 5: Just Roman numerals
    r'\n\n([IVXLCDM]+\.?)\n\n',
]


def download_gutenberg_book(url: str, output_path: str) -> str:
    """Download book from Project Gutenberg or read from local file"""
    # Check if it's a URL or local file
    if url.startswith('http://') or url.startswith('https://'):
        print(f"Downloading from {url}...")
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    else:
        print(f"Reading from local file: {url}...")
        with open(url, 'r', encoding='utf-8') as f:
            content = f.read()

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ Saved to {output_path}")
    return output_path


def extract_metadata(text: str) -> Dict[str, str]:
    """Extract title, author from Gutenberg header"""
    metadata = {
        "title": "Unknown",
        "author": "Unknown",
        "source": "Project Gutenberg"
    }

    # Extract title
    title_match = re.search(r'Title:\s*(.+)', text)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # Extract author
    author_match = re.search(r'Author:\s*(.+)', text)
    if author_match:
        metadata["author"] = author_match.group(1).strip()

    return metadata


def clean_gutenberg_text(text: str) -> str:
    """Remove Gutenberg header and footer"""
    # Find start of actual content
    start_markers = [
        r'\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .+ \*\*\*',
        r'^\s*Chapter\s+[IVXLCDM]+',
    ]

    start_pos = 0
    for marker in start_markers:
        match = re.search(marker, text, re.MULTILINE | re.IGNORECASE)
        if match:
            start_pos = match.end()
            break

    # Find end of actual content
    end_markers = [
        r'\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK',
        r'End of (?:the )?Project Gutenberg',
    ]

    end_pos = len(text)
    for marker in end_markers:
        match = re.search(marker, text, re.IGNORECASE)
        if match:
            end_pos = match.start()
            break

    cleaned_text = text[start_pos:end_pos].strip()

    # Remove CONTENTS/TABLE OF CONTENTS section
    # Look for patterns like "CONTENTS" or "TABLE OF CONTENTS" followed by numbered entries
    contents_pattern = r'(?:CONTENTS|TABLE OF CONTENTS)\s*\n\n(?:\d+\..*?\n)+\n'
    cleaned_text = re.sub(contents_pattern, '', cleaned_text, flags=re.IGNORECASE)

    return cleaned_text


def detect_manual_chapters(text: str) -> Tuple[List[Dict], str]:
    """
    Detect manually marked chapters using special markers.

    Markers:
        =.start.= - Beginning of main content
        =.chapter.= - Beginning of each chapter
        =.end.= - End of main content

    Returns: (chapters, "Manual Markers") if found, else (None, "")
    """
    # Check for manual markers
    if '=.start.=' not in text or '=.chapter.=' not in text or '=.end.=' not in text:
        return None, ""

    print("\n✓ Manual chapter markers detected!")

    # Extract content between start and end markers
    start_marker = '=.start.='
    end_marker = '=.end.='

    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return None, ""

    # Get main content
    main_content = text[start_idx + len(start_marker):end_idx].strip()

    # Split by chapter markers
    chapter_marker = '=.chapter.='
    chapter_parts = main_content.split(chapter_marker)

    # Remove empty parts
    chapter_parts = [part.strip() for part in chapter_parts if part.strip()]

    chapters = []
    for i, chapter_text in enumerate(chapter_parts):
        # Extract title from first line
        lines = chapter_text.split('\n', 1)
        if len(lines) >= 2:
            title = lines[0].strip()
            content = lines[1].strip()
        else:
            title = f"Chapter {i + 1}"
            content = chapter_text.strip()

        word_count = len(content.split())

        chapters.append({
            "number": i + 1,
            "title": title,
            "text": content,
            "word_count": word_count
        })

    total_words = sum(c["word_count"] for c in chapters)
    avg_words = total_words / len(chapters) if chapters else 0

    print(f"  ✓ Found {len(chapters)} manually marked chapters")
    print(f"  ✓ Total words: {total_words:,}")
    print(f"  ✓ Average words/chapter: {avg_words:,.0f}")

    return chapters, "Manual Markers"


def detect_chapters(text: str) -> Tuple[List[Dict], str]:
    """
    Detect chapters using multiple patterns with fallback.
    Returns: (chapters, pattern_used)
    """
    # First, try manual markers
    manual_chapters, marker_type = detect_manual_chapters(text)
    if manual_chapters:
        return manual_chapters, marker_type

    for pattern_idx, pattern in enumerate(CHAPTER_PATTERNS):
        print(f"\nTrying pattern {pattern_idx + 1}: {pattern[:50]}...")

        # Find all chapter markers
        matches = list(re.finditer(pattern, text))

        if not matches:
            print(f"  ❌ No matches found")
            continue

        # Extract chapters
        chapters = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            chapter_title = match.group(1).strip()
            chapter_text = text[start:end].strip()

            # Remove the title from the text
            chapter_text = chapter_text[len(chapter_title):].strip()

            # Count words
            word_count = len(chapter_text.split())

            chapters.append({
                "number": i + 1,
                "title": chapter_title,
                "text": chapter_text,
                "word_count": word_count
            })

        # Validation: check if word counts seem reasonable
        total_words = sum(c["word_count"] for c in chapters)
        avg_words = total_words / len(chapters) if chapters else 0

        print(f"  ✓ Found {len(chapters)} chapters")
        print(f"  ✓ Total words: {total_words:,}")
        print(f"  ✓ Average words/chapter: {avg_words:,.0f}")

        # Reject if chapters are too small (likely false matches)
        if avg_words < 500:
            print(f"  ❌ Chapters too small (avg < 500 words), trying next pattern...")
            continue

        # Reject if we have too many chapters (likely false matches)
        if len(chapters) > 100:
            print(f"  ❌ Too many chapters ({len(chapters)} > 100), trying next pattern...")
            continue

        return chapters, f"Pattern {pattern_idx + 1}"

    raise ValueError("Could not detect chapters with any pattern!")


def infer_chapters_semantic(text: str, client: OpenAI, target_words: int = 2000) -> List[Dict]:
    """
    Infer chapter breaks using semantic chunking with LLM.

    Args:
        text: Full book text
        client: OpenAI client
        target_words: Target words per chapter (~2000)

    Returns:
        List of chapter dictionaries
    """
    print(f"\n🔍 Inferring chapter breaks semantically (target: ~{target_words} words/chapter)...")

    total_words = len(text.split())
    estimated_chapters = max(1, total_words // target_words)

    print(f"  Total words: {total_words:,}")
    print(f"  Estimated chapters: {estimated_chapters}")

    prompt = f"""Analyze this text and divide it into {estimated_chapters} logical chapters based on semantic boundaries.

Each chapter should be approximately {target_words} words, but prioritize natural breaks:
- Scene changes
- Time shifts
- Location changes
- Major topic/theme transitions

Text length: {total_words:,} words

Provide chapter break points as a JSON array of objects with:
- chapter_number: 1, 2, 3...
- title: Brief descriptive title (5-10 words)
- start_marker: First 10-15 words of the chapter (for exact matching)

Example output:
[
  {{"chapter_number": 1, "title": "The Beginning", "start_marker": "In the beginning there was..."}},
  {{"chapter_number": 2, "title": "The Journey", "start_marker": "As dawn broke the next..."}}
]

TEXT TO ANALYZE:
{text[:50000]}... [text truncated for analysis]

Generate the chapter structure:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()

        # Extract JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        chapter_breaks = json.loads(content)

        print(f"  ✓ LLM suggested {len(chapter_breaks)} chapters")

        # Now split the actual text using the start markers
        chapters = []
        words_list = text.split()

        for i, break_point in enumerate(chapter_breaks):
            # Find start position using marker
            marker = break_point['start_marker'].strip()
            marker_words = marker.split()[:10]  # Use first 10 words

            # Search for marker in text
            start_idx = 0
            if i > 0:
                # Start from previous chapter's end
                start_idx = sum(chapters[j]['word_count'] for j in range(i))

            # Find exact chapter end
            if i + 1 < len(chapter_breaks):
                next_marker = chapter_breaks[i + 1]['start_marker'].strip().split()[:10]
                end_idx = start_idx

                # Search for next marker
                for j in range(start_idx, min(start_idx + target_words * 2, len(words_list) - 10)):
                    if words_list[j:j+len(next_marker)] == next_marker:
                        end_idx = j
                        break
                else:
                    # Fallback: use estimated position
                    end_idx = min(start_idx + target_words, len(words_list))
            else:
                # Last chapter: take everything remaining
                end_idx = len(words_list)

            chapter_text = ' '.join(words_list[start_idx:end_idx])
            word_count = end_idx - start_idx

            chapters.append({
                "number": i + 1,
                "title": break_point['title'],
                "text": chapter_text,
                "word_count": word_count
            })

        # Validation
        total_detected = sum(c['word_count'] for c in chapters)
        print(f"  ✓ Created {len(chapters)} chapters")
        print(f"  ✓ Total words: {total_detected:,}")
        print(f"  ✓ Average words/chapter: {total_detected // len(chapters):,}")

        return chapters

    except Exception as e:
        print(f"  ❌ Semantic inference failed: {e}")
        print(f"  ⚠️  Falling back to word-count division...")
        return infer_chapters_wordcount(text, target_words)


def infer_chapters_wordcount(text: str, target_words: int = 2000) -> List[Dict]:
    """
    Fallback: Simple word-count based chapter division.

    Args:
        text: Full book text
        target_words: Target words per chapter

    Returns:
        List of chapter dictionaries
    """
    print(f"\n📏 Using word-count division (target: {target_words} words/chapter)...")

    words = text.split()
    total_words = len(words)
    num_chapters = max(1, (total_words + target_words - 1) // target_words)

    print(f"  Total words: {total_words:,}")
    print(f"  Creating {num_chapters} chapters")

    chapters = []
    words_per_chapter = total_words // num_chapters

    for i in range(num_chapters):
        start = i * words_per_chapter
        end = start + words_per_chapter if i < num_chapters - 1 else total_words

        chapter_words = words[start:end]
        chapter_text = ' '.join(chapter_words)

        chapters.append({
            "number": i + 1,
            "title": f"Chapter {i + 1}",
            "text": chapter_text,
            "word_count": len(chapter_words)
        })

    print(f"  ✓ Created {num_chapters} chapters")
    print(f"  ✓ Average words/chapter: {words_per_chapter:,}")

    return chapters


def create_story_bible_hierarchical(chapters: List[Dict], client: OpenAI) -> str:
    """
    Create story bible using hierarchical summarization.
    For small books (< 20 chapters), summarize all at once.
    For large books, use multi-level summarization.
    """
    num_chapters = len(chapters)

    print(f"\n📖 Creating Story Bible from {num_chapters} chapters...")

    # For <= 20 chapters, summarize all at once
    if num_chapters <= 20:
        return create_story_bible_direct(chapters, client)

    # For larger books, use hierarchical approach
    # Not needed for Call of the Wild (7 chapters), but implemented for extensibility
    return create_story_bible_layered(chapters, client)


def create_story_bible_direct(chapters: List[Dict], client: OpenAI) -> str:
    """Create story bible by summarizing all chapters at once"""
    chapter_summaries = "\n\n".join([
        f"Chapter {c['number']}: {c['title']}\n{c['text'][:1000]}..."  # First 1000 chars
        for c in chapters
    ])

    prompt = f"""You are creating a "Story Bible" - a concise reference document (max 1000 words) for a novel.

The story bible should include:
- Main characters (names, roles, key traits)
- Central conflict/plot
- Key story beats
- Setting and world
- Themes

Here are the chapters:

{chapter_summaries}

Create a comprehensive yet concise Story Bible (max 1000 words):"""

    print("  Generating Story Bible with LLM...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a professional story analyst creating reference documents for audiobook production."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )

    story_bible = response.choices[0].message.content.strip()
    print(f"  ✓ Story Bible created ({len(story_bible.split())} words)")

    return story_bible


def create_story_bible_layered(chapters: List[Dict], client: OpenAI) -> str:
    """Create story bible using multi-level hierarchical summarization"""
    # This would implement the 1024 -> 128 -> 16 -> 1 strategy
    # Not needed for Call of the Wild, but stub for future use
    print("  Using layered summarization strategy...")
    # TODO: Implement if needed for very large books
    return create_story_bible_direct(chapters, client)


def group_chapters_into_episodes(chapters: List[Dict], target_minutes: int = 60, min_last_episode_minutes: int = 40) -> List[Dict]:
    """
    Group chapters into episodes based on estimated narration time.

    Rules:
    - Try to fit as many chapters as possible into ~1 hour (target_minutes)
    - If adding a chapter would exceed the target, start a new episode
    - If the last episode is less than min_last_episode_minutes, merge it with the previous one

    Assumes average reading speed of 150 words per minute.
    """
    WORDS_PER_MINUTE = 150
    target_words = target_minutes * WORDS_PER_MINUTE
    min_last_words = min_last_episode_minutes * WORDS_PER_MINUTE

    episodes = []
    current_episode_chapters = []
    current_word_count = 0

    for chapter in chapters:
        chapter_words = chapter['narrated_word_count']

        # If adding this chapter exceeds target and we have content, start new episode
        if current_word_count > 0 and current_word_count + chapter_words > target_words:
            # Save current episode
            episodes.append({
                "episode_number": len(episodes) + 1,
                "chapters": current_episode_chapters,
                "total_words": current_word_count,
                "estimated_minutes": round(current_word_count / WORDS_PER_MINUTE, 1)
            })

            # Start new episode with this chapter
            current_episode_chapters = [chapter]
            current_word_count = chapter_words
        else:
            # Add to current episode
            current_episode_chapters.append(chapter)
            current_word_count += chapter_words

    # Add final episode
    if current_episode_chapters:
        episodes.append({
            "episode_number": len(episodes) + 1,
            "chapters": current_episode_chapters,
            "total_words": current_word_count,
            "estimated_minutes": round(current_word_count / WORDS_PER_MINUTE, 1)
        })

    # If last episode is too short, merge with previous
    if len(episodes) > 1 and episodes[-1]['total_words'] < min_last_words:
        last_episode = episodes.pop()
        episodes[-1]['chapters'].extend(last_episode['chapters'])
        episodes[-1]['total_words'] += last_episode['total_words']
        episodes[-1]['estimated_minutes'] = round(episodes[-1]['total_words'] / WORDS_PER_MINUTE, 1)

    # Renumber episodes after potential merge
    for i, ep in enumerate(episodes):
        ep['episode_number'] = i + 1

    return episodes


def simplify_chapter(chapter: Dict, story_bible: str, client: OpenAI) -> str:
    """
    Create narrated version of a chapter for audiobook with emotion tags.

    Style: Conversational storytelling with emotion tags for expressive narration.
    """
    prompt = f"""You are adapting a classic novel for audiobook narration with emotion tags.

STORY BIBLE (for context):
{story_bible}

CHAPTER TO ADAPT:
{chapter['title']}

{chapter['text']}

Your task:
- Rewrite this chapter in a conversational, storytelling voice (like a friend telling you the story)
- Keep it simple and clear for passive listening
- Maintain ALL key plot points, character development, and important details
- Remove overly complex descriptions and literary flourishes
- Use short, punchy sentences that flow well when spoken aloud

CRITICAL: Add emotion tags throughout to guide the narrator's voice. Be EXTRAVAGANT with these tags!
Use tags like: [happily], [excited], [sad], [worried], [angry], [mysterious], [whispering], [dramatic],
[tense], [calm], [triumphant], [fearful], [playful], [serious], [gentle], [urgent], [hopeful], [dejected]

Example:
"[excited] Buck couldn't believe his eyes! [happily] The snow fell softly around him. [mysterious] But something felt... different."

Add emotion tags liberally - at least one every 2-3 sentences. This will make the narration much more engaging!

IMPORTANT: Output ONLY the narrated chapter text. Do NOT include any preamble like "Sure", "Here is", "Certainly", or any explanation. Start directly with the story content."""

    print(f"  Simplifying Chapter {chapter['number']}: {chapter['title']}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a professional audiobook adapter. Output ONLY the narrated text - never include preambles, explanations, or meta-commentary. Start directly with the story."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,  # Balanced creativity and consistency
    )

    simplified = response.choices[0].message.content.strip()
    word_count = len(simplified.split())

    print(f"    ✓ Simplified ({chapter['word_count']} -> {word_count} words)")

    return simplified


# Video Style Guide Configuration
# Each style defines consistent visual characteristics for Sora video generation
VIDEO_STYLE_GUIDES = {
    "film_noir": {
        "name": "Film Noir",
        "description": "High-contrast black and white cinematography with dramatic shadows, moody lighting, and mysterious atmosphere",
        "style": "Film noir style: High-contrast black and white, dramatic shadows, venetian blind lighting patterns, moody atmosphere",
        "camera": "Classic noir cinematography: Dutch angles, low-key lighting, deep focus, dramatic close-ups",
        "lighting": "Chiaroscuro lighting with stark contrast between light and shadow, rim lighting, hard shadows",
        "mood": "Mysterious, dramatic, tense"
    },
    "studio_ghibli": {
        "name": "Studio Ghibli",
        "description": "Hand-drawn animation style with soft watercolor backgrounds, expressive characters, and magical realism",
        "style": "Studio Ghibli anime style: Hand-drawn animation, soft watercolor backgrounds, detailed character expressions, magical realism",
        "camera": "Classic anime cinematography: Wide establishing shots, character close-ups, flowing camera movements",
        "lighting": "Soft natural lighting with warm tones, dappled sunlight, glowing magical elements",
        "mood": "Whimsical, emotional, atmospheric"
    },
    "impressionist": {
        "name": "Impressionist",
        "description": "Painterly style with visible brushstrokes, vibrant colors, emphasis on light and movement",
        "style": "Impressionist painting style: Visible brushstrokes, vibrant color palette, emphasis on light effects and movement, like Monet or Renoir",
        "camera": "Painterly composition: Balanced framing, emphasis on color and light over sharp details",
        "lighting": "Natural outdoor lighting with emphasis on changing light conditions, dappled sunlight, golden hour effects",
        "mood": "Vibrant, atmospheric, emotional"
    },
    "vintage_illustration": {
        "name": "Vintage Illustration",
        "description": "Classic book illustration style with detailed line work and limited color palette",
        "style": "Vintage book illustration style: Detailed pen and ink line work, limited color palette, cross-hatching, like Arthur Rackham or N.C. Wyeth",
        "camera": "Classic illustration composition: Centered subjects, ornate framing, storybook perspective",
        "lighting": "Dramatic lighting with strong directional sources, rim lighting on subjects, atmospheric shadows",
        "mood": "Timeless, dramatic, storybook"
    },
    "abstract_expressionist": {
        "name": "Abstract Expressionist",
        "description": "Bold colors, dynamic shapes, emotional expression through non-representational forms",
        "style": "Abstract expressionist style: Bold colors, dynamic shapes, gestural brushwork, emotional expression through abstract forms, like Kandinsky or Rothko",
        "camera": "Dynamic composition: Movement through color and form, layered visual elements, rhythmic patterns",
        "lighting": "Color-based lighting with vibrant hues, overlapping transparent layers, glowing forms",
        "mood": "Emotional, dynamic, interpretive"
    }
}

# Default style for all promotional videos
DEFAULT_VIDEO_STYLE = "film_noir"


def generate_promotional_shorts(chapter: Dict, narrated_text: str, story_bible: str, client: OpenAI) -> List[Dict]:
    """
    Generate 2-3 promotional shorts for a chapter with consistent visual style.

    Each short is ~30 seconds with 4-5 scenes (one sentence each).
    Focus on the most dramatic/exciting/emotional moments.
    Uses structured prompts with explicit style, setting, character, camera, and lighting descriptions.

    Args:
        chapter: Original chapter data
        narrated_text: The narrated version with emotion tags
        story_bible: Story context
        client: OpenAI client

    Returns:
        List of promotional short dictionaries
    """
    # Get style guide
    style_guide = VIDEO_STYLE_GUIDES[DEFAULT_VIDEO_STYLE]

    prompt = f"""You are creating PROMOTIONAL SHORT VIDEOS for an audiobook chapter.

STORY CONTEXT:
{story_bible}

CHAPTER:
{chapter['title']}

NARRATED TEXT (with emotion tags):
{narrated_text}

VIDEO STYLE GUIDE:
All videos MUST use the {style_guide['name']} style with these characteristics:
- Visual Style: {style_guide['style']}
- Camera Work: {style_guide['camera']}
- Lighting: {style_guide['lighting']}
- Mood: {style_guide['mood']}

Your task: Identify the 2-3 most DRAMATIC, EXCITING, or EMOTIONAL moments in this chapter.

Each promotional short should be:
- ~30 seconds total
- 4-5 scenes (one sentence per scene)
- Absolute HIGHLIGHTS that make viewers want to listen to the full chapter

For each short, provide:
1. name: Catchy, marketing-focused title (e.g., "EPIC SHOWDOWN", "Heart-Stopping Reveal")
2. scenes: Array of 4-5 scenes, each with STRUCTURED scene descriptions:
   - scene_id: 1, 2, 3...
   - promotional_narrated_text: ONE sentence excerpt from narrated text (with emotion tag)
   - scene_description: MUST include ALL of these elements in order:
     a) STYLE: Explicit style reference from the guide above
     b) SETTING: Specific environment/location details
     c) SUBJECT: What/who is in the scene with specific visual details
     d) CAMERA: Shot type and angle (e.g., "Close-up", "Wide shot", "Over-the-shoulder")
     e) LIGHTING: Specific lighting setup and mood
     f) ACTION/EMOTION: What's happening or the emotional beat

Example structure: "[STYLE] {style_guide['name']} style. [SETTING] Specific location details. [SUBJECT] Character/object with visual details. [CAMERA] Shot type and angle. [LIGHTING] Lighting description. [ACTION] What's happening."

IMPORTANT: Each scene description should be 2-3 sentences following the structure above. Maintain visual consistency across all scenes using the {style_guide['name']} style guide.

Generate 2-3 promotional shorts (pick the absolute BEST moments from this chapter).

Return your response as a JSON array of short objects:"""

    try:
        # Use response_format to force JSON output
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8,  # Higher temp for creative marketing
            max_tokens=3000
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON - should be clean since we used response_format
        data = json.loads(content)

        # Handle different possible JSON structures
        if isinstance(data, list):
            shorts = data
        elif 'shorts' in data:
            shorts = data['shorts']
        elif 'promotional_shorts' in data:
            shorts = data['promotional_shorts']
        else:
            # Assume the entire object is a single short wrapped in a dict
            shorts = [data] if isinstance(data, dict) and 'scenes' in data else []

        print(f"    ✓ Generated {len(shorts)} promotional shorts (Style: {style_guide['name']})")
        for short in shorts:
            print(f"      - {short['name']}: {len(short['scenes'])} scenes")

        return shorts

    except Exception as e:
        print(f"    ⚠️  Promotional shorts generation failed: {e}")
        return []


def process_book_to_audiobook(
    gutenberg_url: str,
    output_dir: str,
    infer_chapter: bool = False,
    openai_api_key: Optional[str] = None
):
    """Main pipeline to convert book to audiobook format"""

    # Setup
    os.makedirs(output_dir, exist_ok=True)
    client = OpenAI(api_key=openai_api_key or OPENAI_API_KEY)

    # 1. Download book
    raw_path = os.path.join(output_dir, "book_raw.txt")
    download_gutenberg_book(gutenberg_url, raw_path)

    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 2. Extract metadata
    metadata = extract_metadata(raw_text)
    print(f"\n📚 Book: {metadata['title']} by {metadata['author']}")

    # 3. Clean text
    clean_text = clean_gutenberg_text(raw_text)
    print(f"\n✓ Cleaned text ({len(clean_text.split()):,} words)")

    # 4. Detect or infer chapters
    if infer_chapter:
        print(f"\n📖 Inferring chapters (--infer-chapter flag enabled)...")
        try:
            chapters = infer_chapters_semantic(clean_text, client, target_words=2000)
            pattern_used = "Semantic Inference"
        except Exception as e:
            print(f"⚠️  Semantic inference failed: {e}")
            print(f"Falling back to pattern detection...")
            chapters, pattern_used = detect_chapters(clean_text)
    else:
        try:
            chapters, pattern_used = detect_chapters(clean_text)
        except ValueError:
            print(f"\n⚠️  Pattern detection failed. Enabling semantic inference...")
            chapters = infer_chapters_semantic(clean_text, client, target_words=2000)
            pattern_used = "Semantic Inference (fallback)"

    print(f"\n✓ Detected {len(chapters)} chapters using {pattern_used}")

    # 5. Save original chapters for debugging
    originals_dir = os.path.join(output_dir, "original_chapters")
    os.makedirs(originals_dir, exist_ok=True)

    for chapter in chapters:
        filename = f"chapter_{chapter['number']:02d}_{chapter['title'][:30].replace('/', '-')}.txt"
        filepath = os.path.join(originals_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{chapter['title']}\n\n{chapter['text']}")

    print(f"✓ Saved {len(chapters)} original chapters to {originals_dir}")

    # 6. Create Story Bible
    story_bible = create_story_bible_hierarchical(chapters, client)

    # 6b. Extract title/author from story bible if metadata is "Unknown"
    if metadata['title'] == "Unknown" or metadata['author'] == "Unknown":
        print("  Extracting title/author from story bible...")
        # Try to extract from story bible header (e.g., "Story Bible for \"The Fall of the House of Usher\"")
        import re
        title_match = re.search(r'Story Bible for ["\']([^"\']+)["\']', story_bible)
        if title_match and metadata['title'] == "Unknown":
            metadata['title'] = title_match.group(1)
            print(f"  ✓ Extracted title: {metadata['title']}")

        # Try to extract author from story bible content
        author_match = re.search(r'(?:by|Author[:\s]+)([A-Z][a-z]+ [A-Z][a-z]+)', story_bible)
        if author_match and metadata['author'] == "Unknown":
            metadata['author'] = author_match.group(1)
            print(f"  ✓ Extracted author: {metadata['author']}")

        # If still unknown, use LLM to extract
        if metadata['title'] == "Unknown" or metadata['author'] == "Unknown":
            try:
                extract_response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "Extract the book title and author from this story bible. Return ONLY a JSON object like: {\"title\": \"Book Title\", \"author\": \"Author Name\"}"},
                        {"role": "user", "content": story_bible[:2000]}
                    ],
                    temperature=0,
                )
                extracted = json.loads(extract_response.choices[0].message.content.strip())
                if metadata['title'] == "Unknown" and extracted.get('title'):
                    metadata['title'] = extracted['title']
                    print(f"  ✓ LLM extracted title: {metadata['title']}")
                if metadata['author'] == "Unknown" and extracted.get('author'):
                    metadata['author'] = extracted['author']
                    print(f"  ✓ LLM extracted author: {metadata['author']}")
            except Exception as e:
                print(f"  ⚠️ Could not extract metadata via LLM: {e}")

    # 7. Create narrated version of each chapter with promotional shorts
    narrated_chapters = []

    for chapter in chapters:
        narrated_text = simplify_chapter(chapter, story_bible, client)

        # Generate promotional shorts for this chapter
        print(f"  Generating promotional shorts for Chapter {chapter['number']}...")
        promotional_shorts = generate_promotional_shorts(chapter, narrated_text, story_bible, client)

        narrated_chapters.append({
            "chapter_number": chapter['number'],
            "title": chapter['title'],
            "narrated_text": narrated_text,
            "promotional_shorts": promotional_shorts,  # NEW: Promotional content
            "original_word_count": chapter['word_count'],
            "narrated_word_count": len(narrated_text.split())
        })

    # 8. Group chapters into episodes
    print(f"\n📺 Grouping chapters into episodes...")
    episodes = group_chapters_into_episodes(narrated_chapters)

    print(f"  ✓ Created {len(episodes)} episodes")
    for ep in episodes:
        chapter_nums = [c['chapter_number'] for c in ep['chapters']]
        print(f"    Episode {ep['episode_number']}: Chapters {chapter_nums} ({ep['estimated_minutes']} min)")

    # 9. Create output JSON
    output = {
        "metadata": metadata,
        "story_bible": story_bible,
        "chapters": narrated_chapters,
        "episodes": episodes,
        "stats": {
            "total_chapters": len(chapters),
            "total_episodes": len(episodes),
            "original_total_words": sum(c['word_count'] for c in chapters),
            "narrated_total_words": sum(c['narrated_word_count'] for c in narrated_chapters),
            "compression_ratio": round(
                sum(c['narrated_word_count'] for c in narrated_chapters) /
                sum(c['word_count'] for c in chapters),
                2
            ),
            "estimated_total_minutes": round(sum(ep['estimated_minutes'] for ep in episodes), 1)
        }
    }

    # 10. Save JSON
    json_path = os.path.join(output_dir, "audiobook.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ COMPLETE!")
    print(f"   📄 Audiobook JSON: {json_path}")
    print(f"   📁 Original chapters: {originals_dir}")
    print(f"   📊 Stats: {output['stats']}")

    return json_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert a Gutenberg book to an audiobook-ready format with simplified storytelling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/book_to_audiobook.py https://www.gutenberg.org/cache/epub/215/pg215.txt
  python scripts/book_to_audiobook.py https://www.gutenberg.org/cache/epub/84/pg84.txt --output-dir output/audiobooks/frankenstein
  python scripts/book_to_audiobook.py https://gutenberg.net.au/ebooks02/0200991.txt --infer-chapter
        """
    )

    parser.add_argument('gutenberg_url', help='URL to Gutenberg book (txt format)')
    parser.add_argument('--output-dir', help='Output directory (default: auto-generated from URL)')
    parser.add_argument('--infer-chapter', action='store_true',
                        help='Infer chapter breaks using semantic chunking for books without explicit chapter markers')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPEN_AI_API env var)')

    args = parser.parse_args()

    # Auto-generate output dir from URL if not provided
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Extract book ID from URL (e.g., 215 from /epub/215/)
        book_id_match = re.search(r'/epub/(\d+)/', args.gutenberg_url)
        if not book_id_match:
            # Try alternate format (e.g., 0200991 from /ebooks02/0200991.txt)
            book_id_match = re.search(r'/ebooks\d+/(\d+)', args.gutenberg_url)
        book_id = book_id_match.group(1) if book_id_match else "book"
        output_dir = f"output/audiobooks/book_{book_id}"

    print(f"\n🎧 Book to Audiobook Converter")
    print(f"=" * 80)
    print(f"📖 Source: {args.gutenberg_url}")
    print(f"📁 Output: {output_dir}")
    print(f"🔧 Infer chapters: {args.infer_chapter}")
    print(f"=" * 80)

    process_book_to_audiobook(
        gutenberg_url=args.gutenberg_url,
        output_dir=output_dir,
        infer_chapter=args.infer_chapter,
        openai_api_key=args.api_key
    )
