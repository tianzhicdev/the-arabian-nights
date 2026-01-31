"""
OpenAI GPT-Image-1.5 client for style-consistent image generation.
Uses input_fidelity parameter for style transfer.
"""

import os
import base64
from typing import Optional
from openai import OpenAI


class OpenAIImageClient:
    """Client for GPT-Image-1.5 with style transfer capabilities."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI Image client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY or OPEN_AI_API env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_AI_API') or os.getenv('OPENAI_TOKEN')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)

    def generate_with_style_reference(
        self,
        prompt: str,
        style_reference_path: str,
        input_fidelity: str = "high",
        quality: str = "high",
        size: str = "1024x1024"
    ) -> str:
        """
        Generate an image with style from reference image using GPT-Image-1.5.

        Args:
            prompt: Text description of the scene content to generate
            style_reference_path: Local path to style reference image
            input_fidelity: "high" or "low" - how closely to match reference style
            quality: "high" or "standard"
            size: Image size (1024x1024, 1536x1024, 1024x1536, 1280x720, etc.)

        Returns:
            base64-encoded image data
        """
        # Build style-aware prompt
        style_prompt = f"Use the same visual style, color palette, brushstrokes, and artistic technique from the input image. Generate: {prompt}"

        print(f"    Generating image with GPT-Image-1.5...")
        print(f"    Style reference: {style_reference_path}")
        print(f"    Input fidelity: {input_fidelity}, Quality: {quality}")
        print(f"    Prompt: {style_prompt[:100]}...")

        try:
            # Open reference image as file handle
            with open(style_reference_path, 'rb') as image_file:
                # Use images.edit endpoint for style transfer
                response = self.client.images.edit(
                    model="gpt-image-1.5",
                    image=image_file,
                    prompt=style_prompt,
                    input_fidelity=input_fidelity,
                    quality=quality,
                    size=size,
                    n=1
                    # Note: response_format not supported for edit endpoint
                )

            # Extract image URL from response
            if response.data and len(response.data) > 0:
                # Debug: print the whole response
                print(f"    Response object: {response.data[0]}")
                image_url = response.data[0].url if hasattr(response.data[0], 'url') else None
                b64_json = response.data[0].b64_json if hasattr(response.data[0], 'b64_json') else None

                print(f"    Image URL: {image_url}")
                print(f"    Has b64_json: {b64_json is not None}")

                if b64_json:
                    print(f"    ✓ Image generated (b64_json)")
                    return b64_json
                elif image_url:
                    print(f"    ✓ Image generated: {image_url}")

                # Download image and convert to base64
                import requests
                img_response = requests.get(image_url, timeout=60)
                img_response.raise_for_status()
                b64_data = base64.b64encode(img_response.content).decode('utf-8')
                return b64_data
            else:
                raise Exception(f"No image data in response: {response}")

        except Exception as e:
            raise Exception(f"GPT-Image-1.5 generation failed: {str(e)}")

    def save_base64_image(self, b64_data: str, output_path: str):
        """
        Save base64-encoded image to file.

        Args:
            b64_data: base64 image data
            output_path: Path to save image file
        """
        # Decode and save
        image_data = base64.b64decode(b64_data)
        with open(output_path, 'wb') as f:
            f.write(image_data)
        print(f"    Saved image to: {output_path}")


if __name__ == "__main__":
    # Test the client
    client = OpenAIImageClient()
    print("Testing GPT-Image-1.5 client...")

    try:
        # Generate image with style transfer
        b64_data = client.generate_with_style_reference(
            prompt="A russet fox walking through an autumn forest with golden leaves",
            style_reference_path="resources/style_references/watercolor_reference_1280x720.jpg",
            input_fidelity="high",
            quality="high",
            size="1024x1024"
        )

        # Save to file
        client.save_base64_image(b64_data, "test_gpt_image_output.png")
        print("✓ Test completed successfully")

    except Exception as e:
        print(f"✗ Test failed: {e}")
