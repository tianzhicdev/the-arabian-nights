"""
OpenRouter API client for LLM operations.
"""

import os
import requests
from typing import Dict, List, Optional
import json


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model to use (default: claude-3.5-sonnet)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPEN_ROUTER_API')
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided. Set OPENROUTER_API_KEY environment variable or pass api_key parameter.")

        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Send a chat completion request to OpenRouter with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            max_retries: Maximum number of retries for 500 errors

        Returns:
            Response dict with 'content', 'usage', etc.
        """
        import time
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/the-arabian-nights",  # Optional
            "X-Title": "The Arabian Nights Podcast Generator"  # Optional
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300  # 5 minute timeout for long generations
                )
                response.raise_for_status()

                result = response.json()

                # Extract content and usage info
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "usage": result.get("usage", {}),
                    "model": result.get("model", self.model),
                    "finish_reason": result["choices"][0].get("finish_reason")
                }

            except requests.exceptions.HTTPError as e:
                last_error = e
                # Retry on 500-level errors
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                        print(f"  ⚠️  OpenRouter 500 error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                raise Exception(f"OpenRouter API request failed: {str(e)}")

            except requests.exceptions.RequestException as e:
                raise Exception(f"OpenRouter API request failed: {str(e)}")

        # If we exhausted all retries
        raise Exception(f"OpenRouter API request failed after {max_retries} retries: {str(last_error)}")

    def image_generation(
        self,
        prompt: str,
        model: Optional[str] = None,
        width: int = 1280,
        height: int = 720
    ) -> str:
        """
        Generate an image using OpenRouter image models.

        Args:
            prompt: Image generation prompt
            model: Image model to use (if not specified, uses self.model)
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Base64-encoded image data URL (data:image/png;base64,...)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/the-arabian-nights",
            "X-Title": "The Arabian Nights Podcast Generator"
        }

        payload = {
            "model": model or self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "modalities": ["image", "text"],
            # Some models support dimension parameters
            "max_tokens": 1000  # For any text response
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()

            result = response.json()

            # Extract image from response
            message = result["choices"][0]["message"]

            # Check for images in the response
            if "images" in message and len(message["images"]) > 0:
                image_url = message["images"][0]["image_url"]["url"]
                return image_url
            else:
                raise Exception(f"No image in response. Model might not support image generation. Response: {json.dumps(result, indent=2)}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter image generation failed: {str(e)}")

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses rough approximation: 1 token ≈ 4 characters.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
        """
        Estimate API call cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (uses self.model if not specified)

        Returns:
            Estimated cost in USD
        """
        model = model or self.model

        # Pricing as of 2025 (per million tokens)
        # These are approximate - check OpenRouter for current pricing
        pricing = {
            "anthropic/claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
            "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
            "openai/gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "openai/gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        }

        if model not in pricing:
            # Default fallback pricing
            prices = {"input": 3.0, "output": 15.0}
        else:
            prices = pricing[model]

        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]

        return input_cost + output_cost


if __name__ == "__main__":
    # Test the client
    client = OpenRouterClient()

    test_messages = [
        {"role": "user", "content": "Say 'Hello, world!' and nothing else."}
    ]

    print("Testing OpenRouter client...")
    result = client.chat_completion(test_messages, temperature=0)

    print(f"\nResponse: {result['content']}")
    print(f"Tokens used: {result['usage']}")
    print(f"Model: {result['model']}")
