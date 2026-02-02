"""
Explainer video script generator.
Generates scene-by-scene scripts for educational/explainer videos.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class ExplainerScriptGenerator:
    """
    Generate educational video scripts with structured scenes.

    Each scene has:
    - narration: Text to be spoken (15-30 seconds worth)
    - scene_image_description: Description for image generation
    - duration_estimate: Estimated duration in seconds
    """

    # Art style templates for image generation
    ART_STYLES = {
        "photo": (
            "Professional photograph, photorealistic. "
            "Real photo of real places, real people, real events. "
            "Documentary or news photography style. NOT illustration, NOT painting."
        ),
        "flat_vector": (
            "Clean digital illustration of a REALISTIC scene, "
            "NOT metaphorical, NOT fantasy, NOT abstract symbols. "
            "Illustrate real places, real people, real events."
        ),
        "watercolor": (
            "Soft watercolor painting of a REALISTIC scene, "
            "NOT metaphorical, NOT fantasy. "
            "Paint real places, real people, real events."
        ),
        "editorial": (
            "Cinematic digital painting of a REALISTIC scene, "
            "NOT metaphorical dragons or abstract symbols. "
            "Paint what actually exists - real factories, real politicians, real locations."
        ),
    }

    def __init__(self, openrouter_client, art_style: str = "flat_vector"):
        """
        Initialize script generator.

        Args:
            openrouter_client: OpenRouterClient instance for LLM calls
            art_style: Art style for image descriptions
        """
        self.llm = openrouter_client
        self.art_style = art_style
        self.art_style_prompt = self.ART_STYLES.get(art_style, self.ART_STYLES["flat_vector"])

    def select_topic(self, topics: List[Dict]) -> Dict:
        """
        Use LLM to select the best topic for an explainer video.

        Args:
            topics: List of topic dicts from news search

        Returns:
            Dict with selected topic and reasoning
        """
        topics_text = json.dumps(topics, indent=2)

        prompt = f"""You are selecting a topic for a 5-10 minute NEWS-DRIVEN educational explainer video.

Here are the trending topics:
{topics_text}

Select the ONE topic that would make the best explainer video. The video MUST:
1. START with the recent news event (what just happened)
2. Then explain WHY it matters using history, context, and background
3. Be like "The geo/political importance of the Strait of Hormuz" when Iran is in the news
4. Or "The history of semiconductor manufacturing" when there's chip news

Consider:
1. NEWS HOOK - Is there a specific recent event we can open with?
2. Educational depth - Can we explain history, context, implications in detail?
3. Visual storytelling - Can we create evocative artistic illustrations (NOT technical diagrams)?
4. Broader significance - Why should viewers care about understanding this?

Return your selection as JSON:
{{
  "selected_topic": "The topic title",
  "selected_index": 0,
  "news_hook": "The specific recent event to open with (1-2 sentences)",
  "educational_angle": "The deeper topic to explain (e.g., 'History of X', 'Geopolitics of Y')",
  "reasoning": "Why this combination of news + education works",
  "suggested_title": "A compelling video title that hints at both news and education"
}}

Return ONLY the JSON, no other text."""

        messages = [{"role": "user", "content": prompt}]
        result = self.llm.chat_completion(messages, temperature=0.3)

        # Parse response
        content = result["content"]
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback
        return {
            "selected_topic": topics[0].get("title", "Unknown"),
            "selected_index": 0,
            "reasoning": "Default selection",
            "suggested_angle": topics[0].get("potential_angles", ["general overview"])[0],
            "suggested_title": topics[0].get("title", "Explainer Video")
        }

    def generate_script(
        self,
        research_notes: str,
        topic_title: str,
        angle: str,
        news_hook: str = "",
        target_minutes: int = 8,
        scene_duration: tuple = (3, 10)
    ) -> Dict:
        """
        Generate a complete video script with scenes.

        Args:
            research_notes: Comprehensive research on the topic
            topic_title: Title of the topic
            angle: Educational angle (e.g., "History of X")
            news_hook: Recent news event to open with
            target_minutes: Target video length in minutes (5-10)
            scene_duration: (min, max) duration per scene in seconds

        Returns:
            Dict with title, description, and scenes list
        """
        min_scenes = (target_minutes * 60) // scene_duration[1]
        max_scenes = (target_minutes * 60) // scene_duration[0]
        target_scenes = (min_scenes + max_scenes) // 2

        prompt = f"""You are writing a script for a {target_minutes}-minute NEWS-DRIVEN educational explainer video.

TOPIC: {topic_title}
NEWS HOOK (recent event to open with): {news_hook}
EDUCATIONAL ANGLE: {angle}

RESEARCH NOTES:
{research_notes}

MANDATORY REQUIREMENT - SCENE COUNT:
You MUST generate EXACTLY {target_scenes} scenes.
The minimum acceptable is {min_scenes} scenes. The maximum is {max_scenes} scenes.
Each scene = ~10-25 words = ~{scene_duration[0]}-{scene_duration[1]} seconds of narration (SHORT scenes!).
Total: {target_minutes} minutes = {target_minutes * 60} seconds = {target_scenes} scenes.

IMPORTANT: Keep each scene's narration SHORT (10-25 words only). These are quick visual cuts.
IF YOU GENERATE FEWER THAN {min_scenes} SCENES, THE SCRIPT WILL BE REJECTED.

STRUCTURE (adapt scene numbers to your total of {target_scenes}):
- First 10%: Open with the RECENT NEWS EVENT
- Next 20%: Historical context - "But to understand why this matters..."
- Middle 40%: Deep dive - explain the topic with specific facts
- Next 20%: Current implications, different perspectives
- Last 10%: What this means for the future

Each scene is ONE short thought (10-25 words). Cut frequently between visual topics.

NARRATION STYLE:
- Conversational, like a knowledgeable friend explaining
- Use specific details, names, dates, numbers
- NOT generic or surface-level
- Each scene should teach something specific

IMAGE SEARCH KEYWORD - CRITICAL:
- Provide ONE simple search keyword (1-3 words) to find a relevant stock photo
- The keyword should be specific enough to find relevant images but general enough to have results
- Focus on the main visual subject of the scene
- Examples: "semiconductor factory", "oil tanker ship", "European parliament", "cargo port cranes"
- Do NOT use full sentences, just 1-3 word search terms
- Do NOT use abstract concepts - use concrete, photographable subjects

Art style to use: {self.art_style_prompt}

Return ONLY valid JSON in this exact format:
{{
  "title": "Compelling video title",
  "description": "YouTube description (2-3 sentences mentioning the news hook)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Short narration, 10-25 words only. One quick thought per scene.",
      "image_keyword": "search keyword",
      "duration_estimate": 6
    }}
  ]
}}

Remember: This is NEWS-DRIVEN education. Start with what happened, then explain why it matters."""

        messages = [{"role": "user", "content": prompt}]

        # Retry logic for scene count enforcement
        max_retries = 3
        for attempt in range(max_retries):
            result = self.llm.chat_completion(messages, temperature=0.7, max_tokens=12000)

            # Parse response
            content = result["content"]
            try:
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end > start:
                    script = json.loads(content[start:end])
                    scene_count = len(script.get("scenes", []))

                    if scene_count >= min_scenes:
                        return script
                    else:
                        print(f"  Attempt {attempt+1}: Only {scene_count} scenes (need {min_scenes}+), retrying...")
                        # Add feedback to prompt for retry
                        if attempt < max_retries - 1:
                            messages.append({"role": "assistant", "content": content})
                            messages.append({"role": "user", "content": f"ERROR: You only generated {scene_count} scenes. I need AT LEAST {min_scenes} scenes for a {target_minutes}-minute video. Please regenerate with exactly {target_scenes} scenes. Each scene should be 50-75 words. Generate the COMPLETE JSON with ALL {target_scenes} scenes."})
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse script JSON (attempt {attempt+1}): {e}")
                print(f"Raw response (first 500 chars): {content[:500]}")

        # Return error structure
        return {
            "title": topic_title,
            "description": "Generated explainer video",
            "tags": ["explainer", "education"],
            "scenes": [],
            "error": "Failed to parse LLM response"
        }

    def validate_script(self, script: Dict) -> Dict:
        """
        Validate and fix common issues in generated scripts.

        Args:
            script: Generated script dict

        Returns:
            Validated/fixed script dict
        """
        if "scenes" not in script:
            script["scenes"] = []

        for i, scene in enumerate(script["scenes"]):
            # Ensure scene_number
            if "scene_number" not in scene:
                scene["scene_number"] = i + 1

            # Ensure narration exists
            if "narration" not in scene or not scene["narration"]:
                scene["narration"] = f"[Scene {i+1} narration missing]"

            # Ensure image description exists
            if "scene_image_description" not in scene or not scene["scene_image_description"]:
                scene["scene_image_description"] = (
                    f"{self.art_style_prompt}. "
                    f"Abstract illustration representing scene {i+1}."
                )

            # Estimate duration if missing
            if "duration_estimate" not in scene:
                words = len(scene["narration"].split())
                # ~150 words/min at normal pace, slower for narration
                scene["duration_estimate"] = int((words / 120) * 60)

        return script

    def estimate_total_duration(self, script: Dict) -> int:
        """
        Estimate total video duration from script.

        Args:
            script: Script dict with scenes

        Returns:
            Total estimated duration in seconds
        """
        return sum(scene.get("duration_estimate", 20) for scene in script.get("scenes", []))


if __name__ == "__main__":
    # Test with mock client
    class MockLLM:
        def chat_completion(self, messages, **kwargs):
            return {"content": '{"title": "Test", "description": "Test video", "tags": [], "scenes": []}'}

    generator = ExplainerScriptGenerator(MockLLM())

    # Test topic selection
    test_topics = [
        {"title": "Topic 1", "summary": "Summary 1", "potential_angles": ["angle 1"]},
        {"title": "Topic 2", "summary": "Summary 2", "potential_angles": ["angle 2"]},
    ]

    print("Testing topic selection...")
    selection = generator.select_topic(test_topics)
    print(f"Selected: {selection}")
