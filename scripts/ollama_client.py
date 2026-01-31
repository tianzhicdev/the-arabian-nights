"""
Ollama API client for local LLM operations.
Compatible interface with OpenRouterClient.
"""

import requests
from typing import Dict, List, Optional
import json


class OllamaClient:
    """Client for interacting with local Ollama models."""

    def __init__(
        self,
        model: str = "qwen2.5:32b",
        base_url: str = "http://localhost:11434"
    ):
        """
        Initialize Ollama client.

        Args:
            model: Model to use (default: qwen2.5:32b)
            base_url: Ollama server URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Send a chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate (optional)
            max_retries: Maximum number of retries (not used for Ollama)

        Returns:
            Response dict with 'content', 'usage', etc.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=3600  # 60 minute timeout for very long creative generations
            )
            response.raise_for_status()

            result = response.json()

            # Extract content and format like OpenRouterClient
            return {
                "content": result["message"]["content"],
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                },
                "model": self.model,
                "finish_reason": "stop" if result.get("done") else "length"
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API request failed: {str(e)}")


if __name__ == "__main__":
    # Test the client
    client = OllamaClient(model="qwen2.5:32b")

    result = client.chat_completion(
        messages=[
            {"role": "user", "content": "Write a short creative scene description for a peaceful farm at sunset."}
        ],
        temperature=0.9,
        max_tokens=200
    )

    print("Test Response:")
    print(result["content"])
    print(f"\nTokens: {result['usage']['total_tokens']}")
