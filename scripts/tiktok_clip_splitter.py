"""
TikTok Clip Splitter - Split stories into TikTok-optimized short clips

Features:
- Identify natural breakpoints (dramatic moments)
- Generate hooks and cliffhangers
- Optimize for 30-60 second clips
- Vertical format optimization hints
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TikTokClip:
    """Represents a single TikTok short clip."""

    clip_id: int                    # 1-10
    text: str                       # Full narrative content
    hook: str                       # Opening hook (first 3s)
    body: str                       # Main content
    cliffhanger: str                # Ending (drives to next clip)

    # Visual hints
    video_description: str          # Scene description for image gen
    vertical_composition: str       # Composition hints for 9:16

    # Metadata
    expected_duration: int          # Target seconds (30-60)
    keywords: List[str]             # For categorization

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class TikTokClipSplitter:
    """Splits stories into TikTok-optimized clips."""

    def __init__(self, target_count: int = 10, target_duration: int = 40):
        """
        Initialize splitter.

        Args:
            target_count: Number of clips to generate
            target_duration: Target duration per clip in seconds
        """
        self.target_count = target_count
        self.target_duration = target_duration

    def split_story(self, text: str, narration_style: str) -> List[TikTokClip]:
        """
        Split story into TikTok clips.

        Strategy:
        1. Use AI to identify dramatic breakpoints
        2. Generate hooks and cliffhangers
        3. Create 30-60 second narratives
        4. Optimize for vertical viewing

        Args:
            text: Story text
            narration_style: Voice/narration style

        Returns:
            List of TikTokClip objects
        """

        # Call AI to split story
        clips_data = self._generate_clips_with_ai(text, narration_style)

        # Convert to TikTokClip objects
        clips = []
        for i, clip_data in enumerate(clips_data, 1):
            clip = TikTokClip(
                clip_id=i,
                text=clip_data['text'],
                hook=clip_data['hook'],
                body=clip_data['body'],
                cliffhanger=clip_data['cliffhanger'],
                video_description=clip_data['video_description'],
                vertical_composition=clip_data.get('vertical_composition', 'center_focused'),
                expected_duration=clip_data.get('duration', self.target_duration),
                keywords=clip_data.get('keywords', [])
            )
            clips.append(clip)

        return clips

    def _generate_clips_with_ai(self, text: str, narration_style: str) -> List[Dict]:
        """
        Use AI to generate clip breakdowns.

        This calls OpenRouter/Claude to intelligently split the story.

        Returns:
            List of clip data dictionaries
        """

        prompt = f"""
Split this story into {self.target_count} TikTok short clips (~{self.target_duration} seconds each).

STORY:
{text}

REQUIREMENTS:
1. Each clip should be 30-60 seconds when narrated
2. Each clip needs:
   - HOOK: Compelling 3-second opening (question, shock, or mystery)
   - BODY: Main narrative content
   - CLIFFHANGER: Ending that drives viewer to next clip
3. Optimize for vertical mobile viewing (9:16)
4. Include visual description for each clip

NARRATION STYLE: {narration_style}

FORMAT (JSON):
{{
  "clips": [
    {{
      "clip_id": 1,
      "hook": "What if everything you knew was a lie?",
      "body": "In the shadows of the ancient city...",
      "cliffhanger": "But what she discovered next changed everything.",
      "video_description": "Dark ancient city streets at night, mysterious figure in shadows",
      "vertical_composition": "figure_center_upper, text_space_bottom",
      "duration": 35,
      "keywords": ["mystery", "ancient", "discovery"]
    }},
    ...
  ]
}}

Focus on:
- Natural dramatic breakpoints
- Cliffhangers that make viewers want the next clip
- Hooks that grab attention in first 3 seconds
- Vertical-friendly visual compositions
"""

        # Call AI (placeholder - integrate with your OpenRouter client)
        # In real implementation:
        # response = openrouter_client.call(prompt)
        # return json.loads(response)['clips']

        # For now, return mock data
        return self._generate_mock_clips()

    def _generate_mock_clips(self) -> List[Dict]:
        """Generate mock clips for testing."""
        clips = []
        for i in range(1, self.target_count + 1):
            clips.append({
                'clip_id': i,
                'text': f'Full narrative text for clip {i}...',
                'hook': f'Hook for clip {i}: What happens next will shock you...',
                'body': f'Main content of clip {i}. This is where the story unfolds...',
                'cliffhanger': f'Cliffhanger for clip {i}: But then something unexpected happened...',
                'video_description': f'Visual scene for clip {i}',
                'vertical_composition': 'center_focused',
                'duration': self.target_duration,
                'keywords': ['drama', 'mystery']
            })
        return clips

    def save_clips(self, clips: List[TikTokClip], output_file: Path):
        """Save clips to JSON file."""
        data = {
            'version': '1.0',
            'clip_count': len(clips),
            'target_duration': self.target_duration,
            'clips': [clip.to_dict() for clip in clips]
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_clips(self, input_file: Path) -> List[TikTokClip]:
        """Load clips from JSON file."""
        with open(input_file, 'r') as f:
            data = json.load(f)

        clips = []
        for clip_data in data['clips']:
            clip = TikTokClip(**clip_data)
            clips.append(clip)

        return clips


# Example usage
if __name__ == '__main__':
    # Test clip splitting
    sample_text = """
    In the ancient city, shadows moved with purpose. Dr. Elena discovered something
    that would change everything. The artifact pulsed with an otherworldly energy.
    But she wasn't alone. Someone was watching. The truth was far more terrifying
    than she could have imagined. What came next would test everything she believed.
    """

    splitter = TikTokClipSplitter(target_count=5, target_duration=30)
    clips = splitter.split_story(sample_text, "dramatic suspenseful narrator")

    print(f"Generated {len(clips)} clips:")
    print()

    for clip in clips:
        print(f"Clip {clip.clip_id}:")
        print(f"  Hook: {clip.hook}")
        print(f"  Body: {clip.body[:50]}...")
        print(f"  Cliffhanger: {clip.cliffhanger}")
        print(f"  Duration: {clip.expected_duration}s")
        print()

    # Save to file
    output = Path('tiktok_clips_test.json')
    splitter.save_clips(clips, output)
    print(f"Saved clips to {output}")
