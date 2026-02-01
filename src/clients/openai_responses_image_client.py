"""
OpenAI Responses API client for GPT-Image-1.5 style-consistent image generation.
Uses the Responses API with image_generation tool and reference images.
"""

import os
import base64
from typing import Optional
from openai import OpenAI


class OpenAIResponsesImageClient:
    """Client for GPT-Image-1.5 via Responses API with style transfer capabilities."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI Responses Image client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY or OPEN_AI_API env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_AI_API') or os.getenv('OPENAI_TOKEN')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode local image file to base64."""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def generate_with_style_reference(
        self,
        prompt: str,
        style_reference_path: str,
        model: str = "gpt-4o",
        size: str = "1536x1024",  # Closest to 16:9 ratio (3:2)
        consistent_objects: dict = None
    ) -> str:
        """
        Generate an image with style from reference image using Responses API.

        Args:
            prompt: Text description of the scene content to generate
            style_reference_path: Local path to style reference image
            model: Reasoning model to use (gpt-4o, gpt-5, etc.)
            size: Image size (1792x1024 for 16:9, 1024x1024 for square, etc.)
            consistent_objects: Dict of {object_id: {name, description}} for character consistency

        Returns:
            base64-encoded image data
        """
        # Encode reference image to base64
        print(f"    Encoding reference image: {style_reference_path}")
        reference_b64 = self._encode_image_to_base64(style_reference_path)

        # Build character block if consistent objects are provided
        character_block = ""
        if consistent_objects:
            character_block = "\n\nCHARACTERS/OBJECTS IN SCENE:\n"
            for obj_id, obj_data in consistent_objects.items():
                character_block += f"- {obj_data['name']}: {obj_data['description']}\n"
            character_block += "\n"

        # Build style-aware prompt with reference image
        style_prompt = f"Use the same visual style, color palette, brushstrokes, and artistic technique from the reference image I'm providing.{character_block}Generate a new image of: {prompt}"

        print(f"    Generating image with GPT-Image-1.5 via Responses API...")
        print(f"    Model: {model}, Size: {size}")
        print(f"    Prompt: {style_prompt[:100]}...")

        try:
            # Use Responses API with image_generation tool and reference image
            response = self.client.responses.create(
                model=model,
                input=[
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": style_prompt
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{reference_b64}"
                            }
                        ]
                    }
                ],
                tools=[{
                    "type": "image_generation",
                    "size": size
                }]
            )

            # Extract generated image from response
            for output in response.output:
                if output.type == "image_generation_call":
                    # Get the image data
                    if hasattr(output, 'result') and output.result:
                        # Result contains base64 image data
                        print(f"    ✓ Image generated successfully")
                        return output.result
                    elif hasattr(output, 'image') and output.image:
                        # Alternative structure
                        if hasattr(output.image, 'data'):
                            return output.image.data
                        elif hasattr(output.image, 'b64_json'):
                            return output.image.b64_json

            raise Exception(f"No image found in response output: {response.output}")

        except Exception as e:
            raise Exception(f"GPT-Image-1.5 via Responses API failed: {str(e)}")

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
    client = OpenAIResponsesImageClient()
    print("Testing GPT-Image-1.5 via Responses API...")

    try:
        # Generate image with style transfer
        b64_data = client.generate_with_style_reference(
            prompt="A russet fox walking through an autumn forest with golden leaves",
            style_reference_path="resources/style_references/watercolor_reference_1280x720.jpg",
            model="gpt-4o"
        )

        # Save to file
        client.save_base64_image(b64_data, "test_responses_output.png")
        print("✓ Test completed successfully")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
