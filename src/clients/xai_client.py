"""
xAI Grok API client for news search and research.
"""

import os
import requests
from typing import Dict, List, Optional
import json


class XAIClient:
    """Client for interacting with xAI Grok API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "grok-3-latest"):
        """
        Initialize xAI client.

        Args:
            api_key: xAI API key (defaults to XAI_TOKEN env var)
            model: Model to use (default: grok-3-latest)
        """
        self.api_key = api_key or os.getenv('XAI_TOKEN')
        if not self.api_key:
            raise ValueError("xAI API key not provided. Set XAI_TOKEN environment variable or pass api_key parameter.")

        self.model = model
        self.base_url = "https://api.x.ai/v1"

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        search: bool = False,
        max_retries: int = 3
    ) -> Dict:
        """
        Send a chat completion request to xAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            search: Enable real-time web search
            max_retries: Maximum number of retries

        Returns:
            Response dict with 'content', 'usage', etc.
        """
        import time
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Enable web search if requested
        if search:
            payload["search"] = True

        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()

                result = response.json()

                return {
                    "content": result["choices"][0]["message"]["content"],
                    "usage": result.get("usage", {}),
                    "model": result.get("model", self.model),
                    "finish_reason": result["choices"][0].get("finish_reason")
                }

            except requests.exceptions.HTTPError as e:
                last_error = e
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"  ⚠️  xAI 500 error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                raise Exception(f"xAI API request failed: {str(e)} - {response.text}")

            except requests.exceptions.RequestException as e:
                raise Exception(f"xAI API request failed: {str(e)}")

        raise Exception(f"xAI API request failed after {max_retries} retries: {str(last_error)}")

    def search_news(self, category: Optional[str] = None, count: int = 10) -> List[Dict]:
        """
        Search for trending news topics using Grok's web search.

        Args:
            category: Optional category hint (e.g., "geopolitics", "tech", "economics")
            count: Number of topics to return

        Returns:
            List of topic dicts with 'title', 'summary', 'relevance'
        """
        category_hint = f" in the {category} domain" if category else ""

        prompt = f"""Search the web for the most significant trending news stories{category_hint} from the past 24-48 hours.

Return exactly {count} topics as a JSON array. Each topic should be something that would make a good educational/explainer video.

Focus on:
- Geopolitical events with historical context potential
- Economic developments with broader implications
- Technology breakthroughs or controversies
- Scientific discoveries
- Major policy changes

Return ONLY valid JSON in this format:
[
  {{
    "title": "Short topic title",
    "summary": "2-3 sentence summary of what happened",
    "why_interesting": "Why this would make a good explainer video",
    "potential_angles": ["angle 1", "angle 2"]
  }}
]"""

        messages = [{"role": "user", "content": prompt}]

        result = self.chat_completion(messages, temperature=0.3, search=True)

        # Parse JSON from response
        content = result["content"]

        # Extract JSON array from response
        try:
            # Try to find JSON array in response
            start = content.find('[')
            end = content.rfind(']') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                topics = json.loads(json_str)
                return topics
            else:
                raise ValueError("No JSON array found in response")
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse news topics JSON: {e}")
            print(f"Raw response: {content[:500]}")
            return []

    def research_topic(self, topic: str, context: Optional[str] = None) -> str:
        """
        Perform deep research on a specific topic using web search.

        Args:
            topic: The topic to research
            context: Optional additional context or angle to focus on

        Returns:
            Comprehensive research notes as markdown text
        """
        context_hint = f"\n\nFocus especially on: {context}" if context else ""

        prompt = f"""Research the following topic thoroughly using web search: {topic}{context_hint}

Provide comprehensive research notes that would help create an 8-minute educational explainer video. Include:

1. **Background & Context**
   - Historical context and how we got here
   - Key players/entities involved

2. **Current Situation**
   - What exactly is happening now
   - Recent developments (with approximate dates)

3. **Key Facts & Data**
   - Important numbers, statistics, or facts
   - Verified information from reliable sources

4. **Different Perspectives**
   - Various viewpoints on this topic
   - Controversies or debates

5. **Implications & Future**
   - Why this matters
   - Potential future developments

6. **Interesting Details**
   - Lesser-known facts that would engage viewers
   - Surprising connections or context

Format as detailed markdown notes. Be thorough - this will be used to write a video script."""

        messages = [{"role": "user", "content": prompt}]

        result = self.chat_completion(messages, temperature=0.3, search=True, max_tokens=4000)

        return result["content"]


if __name__ == "__main__":
    # Test the client
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    client = XAIClient()

    print("Testing xAI client - News Search...")
    print("=" * 50)

    topics = client.search_news(category="geopolitics", count=5)

    for i, topic in enumerate(topics, 1):
        print(f"\n{i}. {topic.get('title', 'Unknown')}")
        print(f"   {topic.get('summary', '')[:100]}...")

    print("\n" + "=" * 50)
    print("xAI client test complete.")
