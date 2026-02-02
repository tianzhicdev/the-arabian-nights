"""
Pixabay API client for stock video and photo search.
"""

import os
import requests
from typing import Optional, List, Dict, Set
from pathlib import Path
from PIL import Image
from io import BytesIO


class PixabayClient:
    """Client for searching and downloading videos/photos from Pixabay."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Pixabay client.

        Args:
            api_key: Pixabay API key (defaults to PIXABAY_API env var)
        """
        self.api_key = api_key or os.getenv('PIXABAY_API') or os.getenv('PIXABAY_API_KEY')
        if not self.api_key:
            raise ValueError("Pixabay API key not provided. Set PIXABAY_API environment variable.")

        self.base_url = "https://pixabay.com/api"
        self.used_video_ids: Set[int] = set()
        self.used_photo_ids: Set[int] = set()

    def search_videos_with_metadata(
        self,
        query: str,
        per_page: int = 10,
        min_duration: int = 0
    ) -> List[Dict]:
        """
        Search for videos and return full metadata for LLM selection.

        Returns:
            List of video dicts with id, duration, tags, url, description
        """
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": per_page,
            "video_type": "all",
            "safesearch": "true"
        }

        try:
            response = requests.get(
                f"{self.base_url}/videos/",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            videos = []

            for video in data.get("hits", []):
                duration = video.get("duration", 0)
                if duration >= min_duration and video["id"] not in self.used_video_ids:
                    # Get video URL - prefer medium (720p)
                    video_sizes = video.get("videos", {})
                    video_url = None
                    height = 0

                    if "medium" in video_sizes and video_sizes["medium"].get("url"):
                        video_url = video_sizes["medium"]["url"]
                        height = video_sizes["medium"].get("height", 720)
                    elif "large" in video_sizes and video_sizes["large"].get("url"):
                        video_url = video_sizes["large"]["url"]
                        height = video_sizes["large"].get("height", 1080)
                    elif "small" in video_sizes and video_sizes["small"].get("url"):
                        video_url = video_sizes["small"]["url"]
                        height = video_sizes["small"].get("height", 480)

                    if video_url:
                        tags = video.get("tags", "")
                        videos.append({
                            "id": video["id"],
                            "source": "pixabay",
                            "duration": duration,
                            "width": int(height * 16 / 9),
                            "height": height,
                            "url": video_url,
                            "tags": tags.split(", ") if isinstance(tags, str) else tags,
                            "user": video.get("user", ""),
                            "description": f"Tags: {tags}. By {video.get('user', 'unknown')}, {duration}s"
                        })

            return videos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pixabay video search failed: {str(e)}")

    def search_photos(
        self,
        query: str,
        per_page: int = 20,
        orientation: str = "horizontal"
    ) -> List[Dict]:
        """
        Search for photos on Pixabay.

        Args:
            query: Search keyword
            per_page: Number of results
            orientation: Photo orientation (horizontal, vertical, all)

        Returns:
            List of photo dicts
        """
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": per_page,
            "orientation": orientation,
            "safesearch": "true",
            "image_type": "photo"
        }

        try:
            response = requests.get(
                f"{self.base_url}/",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            photos = []

            for photo in data.get("hits", []):
                photos.append({
                    "id": photo["id"],
                    "width": photo.get("imageWidth", 0),
                    "height": photo.get("imageHeight", 0),
                    "largeImageURL": photo.get("largeImageURL", ""),
                    "webformatURL": photo.get("webformatURL", ""),
                    "user": photo.get("user", "")
                })

            return photos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pixabay photo search failed: {str(e)}")

    def search_photos_with_metadata(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "horizontal"
    ) -> List[Dict]:
        """
        Search for photos and return full metadata for LLM selection.

        Returns:
            List of photo dicts with id, source, width, height, url, tags, description
        """
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": per_page,
            "orientation": orientation,
            "safesearch": "true",
            "image_type": "photo"
        }

        try:
            response = requests.get(
                f"{self.base_url}/",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            photos = []

            for photo in data.get("hits", []):
                if photo["id"] not in self.used_photo_ids:
                    tags = photo.get("tags", "")
                    photos.append({
                        "id": photo["id"],
                        "source": "pixabay",
                        "type": "photo",
                        "width": photo.get("imageWidth", 0),
                        "height": photo.get("imageHeight", 0),
                        "url": photo.get("largeImageURL", "") or photo.get("webformatURL", ""),
                        "tags": tags.split(", ") if isinstance(tags, str) else tags,
                        "user": photo.get("user", ""),
                        "description": f"Tags: {tags}. By {photo.get('user', 'unknown')}, {photo.get('imageWidth', 0)}x{photo.get('imageHeight', 0)}"
                    })

            return photos

        except requests.exceptions.RequestException as e:
            raise Exception(f"Pixabay photo search failed: {str(e)}")

    def get_best_unused_video(
        self,
        query: str,
        min_duration: int = 3,
        preferred_height: int = 720
    ) -> Optional[Dict]:
        """
        Get the best video for a query that hasn't been used yet.

        Args:
            query: Search keyword
            min_duration: Minimum video duration in seconds
            preferred_height: Preferred video height (720 or 1080)

        Returns:
            Video dict with download URL or None
        """
        videos = self.search_videos(query, per_page=30, min_duration=min_duration)

        for video in videos:
            if video["id"] in self.used_video_ids:
                continue

            # Get video URLs - prefer 720p, fall back to other sizes
            video_sizes = video.get("videos", {})

            # Priority: medium (720p) → large (1080p) → small (480p)
            video_url = None
            actual_height = 0

            if "medium" in video_sizes and video_sizes["medium"].get("url"):
                video_url = video_sizes["medium"]["url"]
                actual_height = video_sizes["medium"].get("height", 720)
            elif "large" in video_sizes and video_sizes["large"].get("url"):
                video_url = video_sizes["large"]["url"]
                actual_height = video_sizes["large"].get("height", 1080)
            elif "small" in video_sizes and video_sizes["small"].get("url"):
                video_url = video_sizes["small"]["url"]
                actual_height = video_sizes["small"].get("height", 480)
            elif "tiny" in video_sizes and video_sizes["tiny"].get("url"):
                video_url = video_sizes["tiny"]["url"]
                actual_height = video_sizes["tiny"].get("height", 360)

            if video_url:
                self.used_video_ids.add(video["id"])
                return {
                    "id": video["id"],
                    "url": video_url,
                    "duration": video["duration"],
                    "height": actual_height,
                    "type": "video"
                }

        return None

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
            Photo dict or None
        """
        photos = self.search_photos(query, per_page=30)

        for photo in photos:
            if photo["id"] in self.used_photo_ids:
                continue

            if photo["width"] >= min_width and photo["height"] >= min_height:
                self.used_photo_ids.add(photo["id"])
                return {
                    "id": photo["id"],
                    "url": photo["largeImageURL"] or photo["webformatURL"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "type": "photo"
                }

        # Fall back to any unused photo
        for photo in photos:
            if photo["id"] not in self.used_photo_ids:
                self.used_photo_ids.add(photo["id"])
                return {
                    "id": photo["id"],
                    "url": photo["largeImageURL"] or photo["webformatURL"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "type": "photo"
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

    def download_and_resize_photo(
        self,
        photo: Dict,
        output_path: Path,
        target_width: int = 1280,
        target_height: int = 720
    ) -> Path:
        """Download photo and resize/crop to target dimensions."""
        response = requests.get(photo["url"], timeout=60)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Crop to 16:9
        target_ratio = target_width / target_height
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        elif img_ratio < target_ratio:
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG", quality=95)

        return output_path

    def reset_used_ids(self):
        """Reset used IDs for a new video."""
        self.used_video_ids.clear()
        self.used_photo_ids.clear()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    client = PixabayClient()
    print("Testing Pixabay client...")

    # Test video search
    video = client.get_best_unused_video("arctic landscape", min_duration=5)
    if video:
        print(f"Found video: {video['id']} - {video['duration']}s, {video['height']}p")
    else:
        print("No video found, trying photo...")
        photo = client.get_best_unused_photo("arctic landscape")
        if photo:
            print(f"Found photo: {photo['id']} - {photo['width']}x{photo['height']}")
