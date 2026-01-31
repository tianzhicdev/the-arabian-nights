"""
FLUX Redux client for style-consistent image generation via Replicate API.
"""

import os
import replicate
from typing import Optional


class FluxReduxClient:
    """Client for FLUX Redux image generation via Replicate."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FLUX Redux client.

        Args:
            api_key: Replicate API key (defaults to REPLICATE_API_TOKEN or REPLICATE_API env var)
        """
        self.api_key = api_key or os.getenv('REPLICATE_API_TOKEN') or os.getenv('REPLICATE_API')
        if not self.api_key:
            raise ValueError(
                "Replicate API key not provided. Set REPLICATE_API_TOKEN or REPLICATE_API "
                "environment variable or pass api_key parameter."
            )

        # Set API token for replicate library
        os.environ['REPLICATE_API_TOKEN'] = self.api_key

    def generate_with_style_reference(
        self,
        prompt: str,
        style_reference_url: str,
        aspect_ratio: str = "16:9",
        num_inference_steps: int = 28,
        guidance: float = 3.0,
        seed: Optional[int] = None,
        output_format: str = "png"
    ) -> str:
        """
        Generate an image with style from reference image.

        Args:
            prompt: Text description of the scene content to generate
            style_reference_url: URL or local path to style reference image
            aspect_ratio: Image aspect ratio (1:1, 16:9, 4:3, etc.)
            num_inference_steps: Denoising steps (28-50 recommended)
            guidance: Guidance strength (0-10)
            seed: Random seed for reproducibility
            output_format: Output format (png, jpg, webp)

        Returns:
            URL of generated image
        """
        # Handle local file paths - Replicate can accept file handles directly
        if style_reference_url.startswith('/') or style_reference_url.startswith('.'):
            # Local file - pass as file handle
            print(f"    Using local reference image: {style_reference_url}")
            redux_image_input = open(style_reference_url, 'rb')
        else:
            # URL - pass as string
            redux_image_input = style_reference_url

        input_params = {
            "redux_image": redux_image_input,
            "aspect_ratio": aspect_ratio,
            "num_outputs": 1,
            "num_inference_steps": num_inference_steps,
            "guidance": guidance,
            "output_format": output_format,
            "output_quality": 95 if output_format != "png" else 100
        }

        if seed is not None:
            input_params["seed"] = seed

        print(f"    Generating image with FLUX Redux...")
        print(f"    Style reference: {style_reference_url}")
        print(f"    Aspect ratio: {aspect_ratio}, Steps: {num_inference_steps}")

        try:
            # Run FLUX Redux model
            output = replicate.run(
                "black-forest-labs/flux-redux-dev",
                input=input_params
            )

            # Output is a list of URLs
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
                print(f"    ✓ Image generated: {image_url}")
                return image_url
            else:
                raise Exception(f"Unexpected output format: {output}")

        except Exception as e:
            raise Exception(f"FLUX Redux generation failed: {str(e)}")

    def upload_local_image(self, local_path: str) -> str:
        """
        Upload a local image file to Replicate.

        Args:
            local_path: Path to local image file

        Returns:
            Public URL of uploaded image
        """
        with open(local_path, 'rb') as f:
            file_output = replicate.Client().files.create(f)
            return file_output.url


if __name__ == "__main__":
    # Test the client
    client = FluxReduxClient()
    print("Testing FLUX Redux client...")

    # Example usage
    try:
        # Upload a reference image
        reference_url = client.upload_local_image("path/to/reference.jpg")
        print(f"Reference uploaded: {reference_url}")

        # Generate image with style transfer
        result_url = client.generate_with_style_reference(
            prompt="A russet fox walking through an autumn forest",
            style_reference_url=reference_url,
            aspect_ratio="16:9"
        )
        print(f"Generated image: {result_url}")

    except Exception as e:
        print(f"Error: {e}")
