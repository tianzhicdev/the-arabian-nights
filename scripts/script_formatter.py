"""
Script formatter: Converts episode content into narration scripts with pause tags.
"""

import yaml
from typing import Dict, Optional
from openrouter_client import OpenRouterClient


class ScriptFormatter:
    """Formats episode content into narration scripts using LLM."""

    def __init__(
        self,
        client: OpenRouterClient,
        prompts_path: str = "templates/prompts.yaml"
    ):
        """
        Initialize script formatter.

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

    def format_episode(
        self,
        episode_content: str,
        episode_title: str,
        episode_number: int,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Format episode content into narration script.

        Args:
            episode_content: Raw episode content
            episode_title: Title of the episode
            episode_number: Episode number
            custom_prompt: Optional custom user prompt override

        Returns:
            Formatted script with pause tags
        """
        # Get prompts
        system_prompt = self.prompts['formatting']['system']
        user_prompt = custom_prompt or self.prompts['formatting']['user']

        # Format user prompt with variables
        user_prompt_formatted = user_prompt.format(
            episode_title=episode_title,
            episode_number=episode_number,
            content=episode_content
        )

        print(f"Formatting Episode {episode_number}: {episode_title}")
        print(f"  Content length: {len(episode_content)} characters")
        print()

        # Estimate cost
        input_tokens = self.client.estimate_tokens(system_prompt + user_prompt_formatted)
        output_tokens = self.client.estimate_tokens(episode_content) + 500  # Script will be similar length + pause tags
        estimated_cost = self.client.estimate_cost(input_tokens, output_tokens)
        print(f"  Estimated cost: ${estimated_cost:.4f}")

        # Make API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_formatted}
        ]

        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=16000  # Allow for full episode formatting
            )

            print(f"  API call completed")
            print(f"    Input tokens: {response['usage'].get('prompt_tokens', 'N/A')}")
            print(f"    Output tokens: {response['usage'].get('completion_tokens', 'N/A')}")
            print(f"    Total tokens: {response['usage'].get('total_tokens', 'N/A')}")
            print()

            script = response['content'].strip()

            # Count pause tags for validation
            pause_count = script.count('[pause')
            print(f"  Generated script with {len(script)} characters and {pause_count} pause tags")
            print()

            return script

        except Exception as e:
            raise Exception(f"Script formatting failed for episode {episode_number}: {str(e)}")


if __name__ == "__main__":
    # Test the formatter
    import sys

    if len(sys.argv) < 4:
        print("Usage: python script_formatter.py <episode_number> <episode_title> <content_file>")
        sys.exit(1)

    episode_number = int(sys.argv[1])
    episode_title = sys.argv[2]
    content_file = sys.argv[3]

    with open(content_file, 'r') as f:
        content = f.read()

    client = OpenRouterClient()
    formatter = ScriptFormatter(client)

    script = formatter.format_episode(content, episode_title, episode_number)

    # Save output
    output_file = f"episode_{episode_number}_script.txt"
    with open(output_file, 'w') as f:
        f.write(script)

    print(f"Saved script to {output_file}")
