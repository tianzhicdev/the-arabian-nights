"""
OpenAI API client for image generation.
"""

import os
import requests
from typing import Optional


class OpenAIClient:
    """Client for interacting with OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY or OPEN_AI_API env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_AI_API') or os.getenv('OPENAI_TOKEN')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY or OPEN_AI_API environment variable or pass api_key parameter.")

        self.base_url = "https://api.openai.com/v1"

    def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1792x1024",
        quality: str = "standard"
    ) -> str:
        """
        Generate an image using DALL-E.

        Args:
            prompt: Image generation prompt
            model: DALL-E model (dall-e-2 or dall-e-3)
            size: Image size (dall-e-3: 1024x1024, 1792x1024, 1024x1792; dall-e-2: 256x256, 512x512, 1024x1024)
            quality: Quality level (standard or hd) - dall-e-3 only

        Returns:
            URL of generated image
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1
        }

        # Quality parameter only for dall-e-3
        if model == "dall-e-3":
            payload["quality"] = quality

        try:
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            image_url = result["data"][0]["url"]
            return image_url

        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI image generation failed: {str(e)}")

    def generate_video(
        self,
        prompt: str,
        model: str = "sora-2",
        seconds: int = 4,
        size: str = "1280x720",
        input_reference: Optional[str] = None,
        poll_interval: int = 5,
        max_wait: int = 600
    ) -> str:
        """
        Generate a video using Sora (async with polling).

        Args:
            prompt: Video generation prompt
            model: Sora model (sora-2 or sora-2-pro)
            seconds: Clip duration in seconds (4, 8, or 12)
            size: Output resolution (720x1280, 1280x720, 1024x1792, 1792x1024)
            input_reference: Optional image reference file path for style guidance
            poll_interval: Seconds between status checks (default: 5)
            max_wait: Maximum seconds to wait for completion (default: 600)

        Returns:
            URL of generated video
        """
        if seconds not in [4, 8, 12]:
            raise ValueError(f"Invalid duration {seconds}s. Must be 4, 8, or 12 seconds.")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        # If input_reference is provided, use multipart/form-data
        # Otherwise, use JSON
        if input_reference:
            if not os.path.exists(input_reference):
                raise ValueError(f"Reference image not found: {input_reference}")

            # Multipart form data for image upload
            data = {
                "model": model,
                "prompt": prompt,
                "seconds": str(seconds),
                "size": size
            }

            # Determine MIME type based on file extension
            mime_type = "image/jpeg"
            if input_reference.lower().endswith('.png'):
                mime_type = "image/png"
            elif input_reference.lower().endswith('.webp'):
                mime_type = "image/webp"

            files = {
                'input_reference': (os.path.basename(input_reference), open(input_reference, 'rb'), mime_type)
            }

            # Note: headers should NOT include Content-Type for multipart - requests sets it automatically
        else:
            # JSON payload (no reference image)
            headers["Content-Type"] = "application/json"
            data = {
                "model": model,
                "prompt": prompt,
                "seconds": str(seconds),
                "size": size
            }
            files = None

        try:
            # Step 1: Submit video generation job
            if files:
                response = requests.post(
                    f"{self.base_url}/videos",
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=30
                )
            else:
                response = requests.post(
                    f"{self.base_url}/videos",
                    headers=headers,
                    json=data,
                    timeout=30
                )

            # Capture error details before raising
            if not response.ok:
                try:
                    error_body = response.json()
                    error_msg = error_body.get('error', {}).get('message', str(error_body))
                except:
                    error_msg = response.text
                raise Exception(f"Sora API error ({response.status_code}): {error_msg}")

            response.raise_for_status()

            result = response.json()
            video_id = result["id"]

            print(f"    Video job submitted: {video_id}")

            # Step 2: Poll for completion
            import time
            elapsed = 0
            while elapsed < max_wait:
                time.sleep(poll_interval)
                elapsed += poll_interval

                status_response = requests.get(
                    f"{self.base_url}/videos/{video_id}",
                    headers=headers,
                    timeout=30
                )
                status_response.raise_for_status()
                status_result = status_response.json()

                status = status_result.get("status")
                progress = status_result.get("progress", 0)

                if status == "completed":
                    # Video is ready - the video file is available at the /content endpoint
                    print(f"    Video completed after {elapsed}s")

                    # The video file must be downloaded from the /content endpoint
                    # Return the content endpoint URL - caller will download with auth headers
                    content_url = f"{self.base_url}/videos/{video_id}/content"
                    return content_url
                elif status == "failed":
                    error = status_result.get("error", "Unknown error")
                    raise Exception(f"Video generation failed: {error}")
                else:
                    # Still processing
                    print(f"    Status: {status}, Progress: {progress}% ({elapsed}s elapsed)")

            raise Exception(f"Video generation timed out after {max_wait}s")

        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI video generation failed: {str(e)}")


if __name__ == "__main__":
    # Test the client
    client = OpenAIClient()
    print("Testing OpenAI client...")
    try:
        url = client.generate_image("A serene landscape with mountains and a lake", size="1024x1024", quality="standard")
        print(f"\nGenerated image URL: {url}")
    except Exception as e:
        print(f"Error: {e}")
