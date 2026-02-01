#!/usr/bin/env python3
"""
Prompt Builder - Combines podcast-level + episode-level + research into final prompts
"""

from pathlib import Path
from typing import Dict, Optional


class PromptBuilder:
    """Build two-layer prompts: podcast-level + episode-level + research"""

    def __init__(self, podcast_prompt_path: str = "wormhole_fireside_instructions_final.md"):
        self.podcast_prompt_path = Path(podcast_prompt_path)

    def build_system_prompt(self,
                           host1: str,
                           host2: str,
                           topic: str,
                           notes: str,
                           duration_minutes: int = 15,
                           host1_notes: str = "",
                           host2_notes: str = "",
                           research: Optional[Dict[str, str]] = None) -> str:
        """
        Combine podcast-level instructions + episode-specific + research

        Args:
            host1: First host's full name
            host2: Second host's full name
            topic: Episode topic/theme
            notes: Episode discussion notes
            duration_minutes: Target duration in minutes
            host1_notes: Character notes for host 1
            host2_notes: Character notes for host 2
            research: Research findings dict

        Returns:
            Complete system prompt
        """
        # Load podcast-level instructions
        with open(self.podcast_prompt_path, 'r') as f:
            podcast_prompt = f.read()

        # Calculate target word count based on duration
        # Speaking rate: ~150 words per minute at natural conversational pace
        target_words = duration_minutes * 150
        min_words = int(target_words * 0.85)
        max_words = int(target_words * 1.15)

        # Build episode-specific section
        episode_section = f"""

## EPISODE-SPECIFIC REQUIREMENTS

**Topic:** {topic}

**Speakers:**
- **{host1}**{f": {host1_notes}" if host1_notes else ""}
- **{host2}**{f": {host2_notes}" if host2_notes else ""}

**Episode Notes:** {notes}

## 🚨 CRITICAL LENGTH REQUIREMENT 🚨

You MUST generate between {min_words}-{max_words} words (target: {target_words} words).

- This will be approximately {duration_minutes} minutes when spoken at natural pace
- Count dialogue words as you write
- Stop when you reach the target range
- DO NOT go significantly over or under

## 🚨 CRITICAL OUTPUT FORMAT RULES 🚨

Your output must be PURE DIALOGUE ONLY:

✅ CORRECT FORMAT using the ACTUAL speaker names from above:
```
{host1}: [emotion tag] Dialogue text here.

{host2}: More dialogue without tag.

{host1}: [another tag] Final dialogue.
```

❌ ABSOLUTELY FORBIDDEN - DO NOT USE GENERIC PLACEHOLDERS:
```
Speaker A: Some dialogue here.
Speaker B: More dialogue here.

Host 1: Some dialogue here.
Host 2: More dialogue here.

Person A: Some dialogue here.
Person B: More dialogue here.
```
**These are WRONG. You MUST use the actual names: {host1} and {host2}**

❌ NEVER INCLUDE:
- Markdown code blocks (no ``` delimiters)
- JSON wrappers or metadata
- Headers like "SCRIPT:", "DIALOGUE:", "PODCAST:"
- Explanatory text like "Here's the script" or "END OF SCRIPT"
- Config blocks or file metadata
- Stage directions outside emotion tags
- Generic speaker names (Speaker A/B, Host 1/2, Person A/B)

✅ REQUIREMENTS:
- Start IMMEDIATELY with first speaker's line
- Use ONLY these exact names: "{host1}" and "{host2}"
- Do NOT shorten names (use full name always)
- Emotion tags in [square brackets] when needed
- Blank line between speaker turns
- NOTHING else
"""

        # Add research if available
        if research:
            research_section = f"""

## RESEARCH FINDINGS

Use these facts to ground the conversation in historical reality. Reference specific events, dates, and quotes.

### {host1} Background:
{research['host_1_bio']}

### {host2} Background:
{research['host_2_bio']}

### Topic Context:
{research['topic_context']}

### Relationship Between Speakers:
{research['relationship']}

**IMPORTANT:** Weave these facts naturally into the dialogue. Reference specific events, use actual quotes, mention real dates and places.
"""
            episode_section += research_section

        # Combine everything
        final_prompt = f"""{podcast_prompt}

{episode_section}

---

Now generate the dialogue. Start directly with the first speaker's line. No headers, no metadata, just the conversation."""

        return final_prompt

    def parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to minutes

        Examples: "10m" -> 10, "15min" -> 15, "20" -> 20
        """
        duration_str = duration_str.lower().strip()

        # Remove common suffixes
        for suffix in ['min', 'mins', 'minute', 'minutes', 'm']:
            if duration_str.endswith(suffix):
                duration_str = duration_str[:-len(suffix)].strip()
                break

        try:
            return int(duration_str)
        except ValueError:
            print(f"Warning: Could not parse duration '{duration_str}', defaulting to 15 minutes")
            return 15
