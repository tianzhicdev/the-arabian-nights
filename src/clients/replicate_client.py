"""
Replicate API client for Flux image generation.
"""

import os
import time
import requests
from typing import Optional


class ReplicateClient:
    """Client for interacting with Replicate API (Flux models)."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Replicate client.

        Args:
            api_key: Replicate API key (defaults to REPLICATE_API_TOKEN env var)
        """
        self.api_key = api_key or os.getenv('REPLICATE_API_TOKEN') or os.getenv('REPLICATE_API')
        if not self.api_key:
            raise ValueError("Replicate API key not provided. Set REPLICATE_API_TOKEN or REPLICATE_API environment variable.")

        self.base_url = "https://api.replicate.com/v1"

    def generate_image(
        self,
        prompt: str,
        model: str = "black-forest-labs/flux-1.1-pro",
        aspect_ratio: str = "16:9",
        output_format: str = "png",
        safety_tolerance: int = 2,
        prompt_upsampling: bool = True
    ) -> str:
        """
        Generate an image using Flux.

        Args:
            prompt: Image generation prompt
            model: Flux model (flux-1.1-pro, flux-schnell, flux-dev)
            aspect_ratio: Aspect ratio (16:9, 1:1, 4:3, etc.)
            output_format: Output format (png, jpg, webp)
            safety_tolerance: Safety filter tolerance (0-6, higher = more permissive)
            prompt_upsampling: Whether to enhance prompt automatically

        Returns:
            URL of generated image
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait"  # Wait for result synchronously
        }

        payload = {
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": output_format,
                "safety_tolerance": safety_tolerance,
                "prompt_upsampling": prompt_upsampling
            }
        }

        try:
            # Create prediction
            response = requests.post(
                f"{self.base_url}/models/{model}/predictions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()

            # Check if completed immediately (with Prefer: wait)
            if result.get("status") == "succeeded":
                output = result.get("output")
                if isinstance(output, list):
                    return output[0]
                return output

            # If not completed, poll for result
            prediction_id = result.get("id")
            return self._poll_prediction(prediction_id)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Replicate image generation failed: {str(e)}")

    def _poll_prediction(self, prediction_id: str, max_wait: int = 120, poll_interval: int = 2) -> str:
        """Poll for prediction completion."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        elapsed = 0
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            response = requests.get(
                f"{self.base_url}/predictions/{prediction_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            status = result.get("status")
            if status == "succeeded":
                output = result.get("output")
                if isinstance(output, list):
                    return output[0]
                return output
            elif status == "failed":
                error = result.get("error", "Unknown error")
                raise Exception(f"Image generation failed: {error}")

        raise Exception(f"Image generation timed out after {max_wait}s")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    client = ReplicateClient()
    print("Testing Replicate Flux client...")
    try:
        url = client.generate_image(
            "Professional photograph of a modern semiconductor factory clean room, "
            "workers in white bunny suits, advanced machinery, photorealistic",
            aspect_ratio="16:9"
        )
        print(f"\nGenerated image URL: {url}")
    except Exception as e:
        print(f"Error: {e}")
