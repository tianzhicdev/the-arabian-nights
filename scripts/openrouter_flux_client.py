"""
FLUX.2 client for style-consistent image generation via OpenRouter API.
Uses your existing OpenRouter API key.
"""

import os
import base64
import requests
from typing import Optional


class OpenRouterFluxClient:
    """Client for FLUX.2 image generation via OpenRouter."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter FLUX client.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY or OPEN_ROUTER_API env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPEN_ROUTER_API')
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not provided. Set OPENROUTER_API_KEY or OPEN_ROUTER_API "
                "environment variable or pass api_key parameter."
            )

        self.base_url = "https://openrouter.ai/api/v1"

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Encode local image file to base64 data URL.

        Args:
            image_path: Path to local image file

        Returns:
            base64-encoded data URL
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()

        # Determine MIME type
        mime_type = "image/jpeg"
        if image_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif image_path.lower().endswith('.webp'):
            mime_type = "image/webp"

        # Encode to base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"

    def generate_with_style_reference(
        self,
        prompt: str,
        style_reference_path: str,
        model: str = "black-forest-labs/flux.2-max",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None
    ) -> str:
        """
        Generate an image with style from reference image using FLUX.2.

        Args:
            prompt: Text description of the scene content to generate
            style_reference_path: Local path to style reference image
            model: FLUX model (flux.2-max, flux.2-pro, flux.2-flex)
            aspect_ratio: Image aspect ratio (16:9, 4:3, 1:1, etc.)
            seed: Random seed for reproducibility

        Returns:
            base64-encoded data URL of generated image
        """
        # Encode reference image to base64
        print(f"    Encoding reference image: {style_reference_path}")
        reference_image_url = self._encode_image_to_base64(style_reference_path)

        # Build request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-project",  # Optional
            "X-Title": "Arabian Nights Video Generator"  # Optional
        }

        # Build message content with text prompt and reference image
        message_content = [
            {
                "type": "text",
                "text": f"{prompt}. Aspect ratio: {aspect_ratio}. Match the artistic style of the reference image."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": reference_image_url
                }
            }
        ]

        payload = {
            "model": model,
            "modalities": ["image", "text"],
            "messages": [
                {
                    "role": "user",
                    "content": message_content
                }
            ]
        }

        # Add seed if provided
        if seed is not None:
            payload["seed"] = seed

        print(f"    Generating image with FLUX.2 via OpenRouter...")
        print(f"    Model: {model}")
        print(f"    Aspect ratio: {aspect_ratio}")

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )

            # Check for errors
            if not response.ok:
                error_body = response.text
                raise Exception(f"OpenRouter API error ({response.status_code}): {error_body}")

            response.raise_for_status()
            result = response.json()

            # Extract generated image from response
            # OpenRouter returns images as base64 data URLs in the assistant message
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})

                # Check for images in message
                if 'images' in message and len(message['images']) > 0:
                    image_data_url = message['images'][0]
                    print(f"    ✓ Image generated successfully")
                    return image_data_url

                # Some models might return images in content
                content = message.get('content', '')
                if content.startswith('data:image'):
                    print(f"    ✓ Image generated successfully")
                    return content

                raise Exception(f"No image found in response: {result}")
            else:
                raise Exception(f"Unexpected response format: {result}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"FLUX.2 generation via OpenRouter failed: {str(e)}")

    def save_base64_image(self, data_url: str, output_path: str):
        """
        Save base64-encoded data URL image to file.

        Args:
            data_url: base64 data URL (data:image/png;base64,...)
            output_path: Path to save image file
        """
        # Extract base64 data from data URL
        if ',' in data_url:
            base64_data = data_url.split(',', 1)[1]
        else:
            base64_data = data_url

        # Decode and save
        image_data = base64.b64decode(base64_data)
        with open(output_path, 'wb') as f:
            f.write(image_data)
        print(f"    Saved image to: {output_path}")


if __name__ == "__main__":
    # Test the client
    client = OpenRouterFluxClient()
    print("Testing OpenRouter FLUX.2 client...")

    try:
        # Generate image with style transfer
        result_data_url = client.generate_with_style_reference(
            prompt="A russet fox walking through an autumn forest",
            style_reference_path="resources/style_references/watercolor_reference_1280x720.jpg",
            aspect_ratio="16:9"
        )

        # Save to file
        client.save_base64_image(result_data_url, "test_output.png")
        print("✓ Test completed successfully")

    except Exception as e:
        print(f"✗ Test failed: {e}")
