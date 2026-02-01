"""
Content segmenter: Divides long-form text into podcast episodes.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
from src.clients.openrouter_client import OpenRouterClient


class ContentSegmenter:
    """Segments long-form content into podcast episodes using LLM."""

    def __init__(
        self,
        client: OpenRouterClient,
        prompts_path: str = "templates/prompts.yaml"
    ):
        """
        Initialize content segmenter.

        Args:
            client: OpenRouter client instance
            prompts_path: Path to prompts YAML file
        """
        self.client = client
        self.prompts = self._load_prompts(prompts_path)

    def _load_prompts(self, prompts_path: str) -> Dict:
        """Load prompt templates from YAML file."""
        with open(prompts_path, 'r') as f:
            return yaml.safe_load(f)

    def segment_content(
        self,
        content: str,
        title: str,
        num_episodes: Union[int, str] = "auto",
        custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """
        Segment content into episodes.

        Args:
            content: Raw text content to segment
            title: Title of the work
            num_episodes: Number of episodes (or "auto" to let LLM decide)
            custom_prompt: Optional custom user prompt override

        Returns:
            List of episode dicts with keys: episode_number, title, content, word_count
        """
        # Get prompts
        system_prompt = self.prompts['segmentation']['system']
        user_prompt = custom_prompt or self.prompts['segmentation']['user']

        # Format user prompt with variables
        user_prompt_formatted = user_prompt.format(
            title=title,
            num_episodes=num_episodes,
            content=content
        )

        print(f"Segmenting content into episodes...")
        print(f"  Title: {title}")
        print(f"  Content length: {len(content)} characters")
        print(f"  Requested episodes: {num_episodes}")
        print()

        # Estimate cost
        input_tokens = self.client.estimate_tokens(system_prompt + user_prompt_formatted)
        output_tokens = 10000  # Rough estimate for episode segmentation
        estimated_cost = self.client.estimate_cost(input_tokens, output_tokens)
        print(f"Estimated cost: ${estimated_cost:.4f}")
        print()

        # Make API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_formatted}
        ]

        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=16000  # Allow for detailed segmentation
            )

            print(f"API call completed")
            print(f"  Input tokens: {response['usage'].get('prompt_tokens', 'N/A')}")
            print(f"  Output tokens: {response['usage'].get('completion_tokens', 'N/A')}")
            print(f"  Total tokens: {response['usage'].get('total_tokens', 'N/A')}")
            print()

            # Parse JSON response
            content_response = response['content'].strip()

            # Try to extract JSON if there's extra text
            if not content_response.startswith('['):
                # Look for JSON array in the response
                start = content_response.find('[')
                end = content_response.rfind(']') + 1
                if start != -1 and end != 0:
                    content_response = content_response[start:end]

            episodes = json.loads(content_response)

            # Validate structure
            required_keys = {'episode_number', 'title', 'content', 'word_count'}
            for i, episode in enumerate(episodes):
                if not all(key in episode for key in required_keys):
                    raise ValueError(f"Episode {i+1} missing required keys. Has: {episode.keys()}")

            print(f"Successfully segmented into {len(episodes)} episodes:")
            for ep in episodes:
                print(f"  Episode {ep['episode_number']}: {ep['title']} ({ep['word_count']} words)")
            print()

            return episodes

        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON response from LLM")
            print(f"Response content: {response['content'][:500]}...")
            raise Exception(f"Invalid JSON in segmentation response: {str(e)}")

        except Exception as e:
            raise Exception(f"Segmentation failed: {str(e)}")


if __name__ == "__main__":
    # Test the segmenter
    import sys

    if len(sys.argv) < 3:
        print("Usage: python content_segmenter.py <input_file> <title> [num_episodes]")
        sys.exit(1)

    input_file = sys.argv[1]
    title = sys.argv[2]
    num_episodes = sys.argv[3] if len(sys.argv) > 3 else "auto"

    with open(input_file, 'r') as f:
        content = f.read()

    client = OpenRouterClient()
    segmenter = ContentSegmenter(client)

    episodes = segmenter.segment_content(content, title, num_episodes)

    # Save output
    output_file = Path(input_file).stem + "_episodes.json"
    with open(output_file, 'w') as f:
        json.dump(episodes, f, indent=2)

    print(f"Saved episodes to {output_file}")
