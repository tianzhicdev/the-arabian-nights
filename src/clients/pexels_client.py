"""
Pexels API client for stock photo search.
"""

import os
import requests
from typing import Optional, List, Dict, Set
from pathlib import Path
from PIL import Image
from io import BytesIO


class PexelsClient:
    """Client for searching and downloading videos and photos from Pexels."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Pexels client.

        Args:
            api_key: Pexels API key (defaults to PEXELS_API env var)
        """
        self.api_key = api_key or os.getenv('PEXELS_API') or os.getenv('PEXELS_API_KEY')
        if not self.api_key:
            raise ValueError("Pexels API key not provided. Set PEXELS_API environment variable.")

        self.base_url = "https://api.pexels.com/v1"
        self.videos_url = "https://api.pexels.com/videos"
        self.used_photo_ids: Set[int] = set()
        self.used_video_ids: Set[int] = set()

    def search_videos_with_metadata(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "landscape",
        min_duration: int = 0
    ) -> List[Dict]:
        """
        Search for videos and return full metadata for LLM selection.

        Returns:
            List of video dicts with id, duration, tags, url, description
        """
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation
        }

        try:
            response = requests.get(
                f"{self.videos_url}/search",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            videos = []

            for video in data.get("videos", []):
                duration = video.get("duration", 0)
                if duration >= min_duration and video["id"] not in self.used_video_ids:
                    # Get best video file URL
                    video_files = video.get("video_files", [])
                    best_file = None
                    for vf in sorted(video_files, key=lambda x: abs(x.get("height", 0) - 720)):
                        if vf.get("link"):
                            best_file = vf
                            break

                    if best_file:
                        videos.append({
                            "id": video["id"],
                            "source": "pexels",
                            "duration": duration,
                            "width": best_file.get("width", 1280),
                            "height": best_file.get("height", 720),
                            "url": best_file["link"],
                            "tags": video.get("tags", []),  # Pexels doesn't have tags, but we include for consistency
                            "user": video.get("user", {}).get("name", ""),
                            "description": f"Video by {video.get('user', {}).get('name', 'unknown')}, {duration}s"
                        })

            return videos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pexels video search failed: {str(e)}")

    def search_photos_with_metadata(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "landscape"
    ) -> List[Dict]:
        """
        Search for photos and return full metadata for LLM selection.

        Returns:
            List of photo dicts with id, source, width, height, url, description
        """
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation
        }

        try:
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            photos = []

            for photo in data.get("photos", []):
                if photo["id"] not in self.used_photo_ids:
                    photos.append({
                        "id": photo["id"],
                        "source": "pexels",
                        "type": "photo",
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                        "url": photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large"),
                        "photographer": photo.get("photographer", ""),
                        "description": f"Photo by {photo.get('photographer', 'unknown')}, {photo.get('width', 0)}x{photo.get('height', 0)}"
                    })

            return photos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pexels photo search failed: {str(e)}")

    def get_best_unused_video(
        self,
        query: str,
        min_duration: int = 3,
        preferred_height: int = 720
    ) -> Optional[Dict]:
        """
        Get the best video that hasn't been used yet.

        Args:
            query: Search keyword
            min_duration: Minimum duration in seconds
            preferred_height: Preferred height (720 or 1080)

        Returns:
            Video dict with download URL or None
        """
        videos = self.search_videos(query, per_page=30, min_duration=min_duration)

        for video in videos:
            if video["id"] in self.used_video_ids:
                continue

            # Find best quality video file
            video_files = video.get("video_files", [])

            # Sort by height, prefer 720p then 1080p
            best_file = None
            for vf in sorted(video_files, key=lambda x: abs(x.get("height", 0) - preferred_height)):
                if vf.get("link"):
                    best_file = vf
                    break

            if best_file:
                self.used_video_ids.add(video["id"])
                return {
                    "id": video["id"],
                    "url": best_file["link"],
                    "duration": video["duration"],
                    "width": best_file.get("width", 1280),
                    "height": best_file.get("height", 720),
                    "type": "video"
                }

        return None

    def download_video(self, video: Dict, output_path: Path) -> Path:
        """Download video to file."""
        response = requests.get(video["url"], timeout=120)
        response.raise_for_status()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path

    def search_photos(
        self,
        query: str,
        per_page: int = 15,
        orientation: str = "landscape"
    ) -> List[Dict]:
        """
        Search for photos on Pexels.

        Args:
            query: Search keyword
            per_page: Number of results (max 80)
            orientation: Photo orientation (landscape, portrait, square)

        Returns:
            List of photo dicts with id, url, width, height
        """
        headers = {
            "Authorization": self.api_key
        }

        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation
        }

        try:
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            photos = []

            for photo in data.get("photos", []):
                photos.append({
                    "id": photo["id"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "photographer": photo["photographer"],
                    "src": photo["src"]  # Contains original, large2x, large, medium, etc.
                })

            return photos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pexels search failed: {str(e)}")

    def get_best_unused_photo(
        self,
        query: str,
        min_width: int = 1280,
        min_height: int = 720
    ) -> Optional[Dict]:
        """
        Get the best photo for a query that hasn't been used yet.

        Args:
            query: Search keyword
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels

        Returns:
            Photo dict or None if no suitable photo found
        """
        photos = self.search_photos(query, per_page=30)

        for photo in photos:
            # Skip if already used
            if photo["id"] in self.used_photo_ids:
                continue

            # Check minimum size
            if photo["width"] >= min_width and photo["height"] >= min_height:
                self.used_photo_ids.add(photo["id"])
                return photo

        # If all top results are used or too small, try without size filter
        for photo in photos:
            if photo["id"] not in self.used_photo_ids:
                self.used_photo_ids.add(photo["id"])
                return photo

        return None

    def download_and_resize(
        self,
        photo: Dict,
        output_path: Path,
        target_width: int = 1280,
        target_height: int = 720
    ) -> Path:
        """
        Download photo and resize/crop to target dimensions.

        Args:
            photo: Photo dict from search
            output_path: Path to save the image
            target_width: Target width (default 1280 for 720p)
            target_height: Target height (default 720 for 720p)

        Returns:
            Path to saved image
        """
        # Get the best available resolution
        src = photo["src"]
        # Prefer large2x or original for quality
        image_url = src.get("large2x") or src.get("original") or src.get("large")

        try:
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()

            # Open image with PIL
            img = Image.open(BytesIO(response.content))

            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate crop to maintain 16:9 aspect ratio
            target_ratio = target_width / target_height
            img_ratio = img.width / img.height

            if img_ratio > target_ratio:
                # Image is wider than target - crop sides
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            elif img_ratio < target_ratio:
                # Image is taller than target - crop top/bottom
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))

            # Resize to target dimensions
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Save
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG", quality=95)

            return output_path

        except Exception as e:
            raise Exception(f"Failed to download/resize image: {str(e)}")

    def reset_used_ids(self):
        """Reset all used IDs for a new video."""
        self.used_photo_ids.clear()
        self.used_video_ids.clear()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    client = PexelsClient()
    print("Testing Pexels client...")

    # Test search
    photo = client.get_best_unused_photo("semiconductor factory")
    if photo:
        print(f"Found: {photo['id']} - {photo['width']}x{photo['height']} by {photo['photographer']}")

        # Test download
        output = Path("output/test_pexels.png")
        client.download_and_resize(photo, output)
        print(f"Saved to: {output}")
    else:
        print("No suitable photo found")
