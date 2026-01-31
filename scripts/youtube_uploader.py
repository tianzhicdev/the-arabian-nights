"""
YouTube Shorts Uploader - Upload videos to YouTube with automatic short detection.

Features:
- Auto-detect shorts (videos < 60s)
- Add #shorts tag automatically
- Link to main video in description
- Track upload progress
- Handle API errors and retries
"""

import os
import sys
import json
import time
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import argparse

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import http.client
import httplib2


# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CLIENT_SECRET_FILE = PROJECT_ROOT / 'credentials' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'credentials' / 'youtube_token.pickle'

# Retry settings
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 3


@dataclass
class UploadResult:
    """Result of a video upload."""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    title: str = ""
    error: Optional[str] = None
    upload_time: float = 0.0


class YouTubeUploader:
    """Upload videos to YouTube."""

    def __init__(self, credentials_path: Optional[Path] = None, token_path: Optional[Path] = None):
        """
        Initialize uploader.

        Args:
            credentials_path: Path to client_secret.json
            token_path: Path to saved token file
        """
        self.credentials_path = credentials_path or CLIENT_SECRET_FILE
        self.token_path = token_path or TOKEN_FILE
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API."""
        credentials = None

        # Try to load saved token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    credentials = pickle.load(token)
            except Exception as e:
                print(f"⚠️  Could not load token: {e}")

        # Refresh or get new credentials
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    print(f"⚠️  Could not refresh credentials: {e}")
                    credentials = None

            if not credentials:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"client_secret.json not found at {self.credentials_path}\n"
                        f"Please follow YOUTUBE_API_SETUP_GUIDE.md"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES
                )
                credentials = flow.run_local_server(port=0)  # Use random available port

                # Save token
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, 'wb') as token:
                    pickle.dump(credentials, token)

        self.youtube = build('youtube', 'v3', credentials=credentials)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "24",  # Entertainment
        privacy_status: str = "public",  # public, private, unlisted
        made_for_kids: bool = False,
        main_video_url: Optional[str] = None
    ) -> UploadResult:
        """
        Upload video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: public, private, or unlisted
            made_for_kids: Whether video is made for kids
            main_video_url: URL to main video (added to description)

        Returns:
            UploadResult object
        """
        start_time = time.time()

        if not video_path.exists():
            return UploadResult(
                success=False,
                title=title,
                error=f"Video file not found: {video_path}"
            )

        # Check if video is a short (< 60 seconds)
        duration = self._get_video_duration(video_path)
        is_short = duration < 60

        # Add #shorts tag if it's a short
        if is_short and '#shorts' not in description.lower():
            description = f"{description}\n\n#shorts"

        # Add main video link
        if main_video_url:
            description = f"{description}\n\n🎬 Watch full episode: {main_video_url}"

        # Prepare tags
        if tags is None:
            tags = []
        if is_short and 'shorts' not in [t.lower() for t in tags]:
            tags.append('shorts')

        # Build request body
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids
            }
        }

        # Prepare media upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,  # Upload in single request
            resumable=True
        )

        try:
            print(f"⬆️  Uploading: {title}")
            print(f"   File: {video_path.name}")
            print(f"   Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Type: {'Short' if is_short else 'Regular video'}")

            # Execute upload with retry
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )

            response = self._resumable_upload(request)

            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            upload_time = time.time() - start_time

            print(f"✓ Upload successful!")
            print(f"   Video ID: {video_id}")
            print(f"   URL: {video_url}")
            print(f"   Time: {upload_time:.1f}s")

            return UploadResult(
                success=True,
                video_id=video_id,
                video_url=video_url,
                title=title,
                upload_time=upload_time
            )

        except HttpError as e:
            error_msg = f"HTTP error {e.resp.status}: {e.content.decode()}"
            print(f"✗ Upload failed: {error_msg}")
            return UploadResult(
                success=False,
                title=title,
                error=error_msg,
                upload_time=time.time() - start_time
            )
        except Exception as e:
            error_msg = str(e)
            print(f"✗ Upload failed: {error_msg}")
            return UploadResult(
                success=False,
                title=title,
                error=error_msg,
                upload_time=time.time() - start_time
            )

    def _resumable_upload(self, request):
        """Execute resumable upload with retry."""
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"   Progress: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = f"Retriable error: {type(e).__name__}"

            if error is not None:
                retry += 1
                if retry > MAX_RETRIES:
                    raise Exception(f"Max retries exceeded: {error}")

                sleep_time = 2 ** retry
                print(f"   ⚠️  {error}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                error = None

        return response

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds using ffprobe."""
        try:
            import subprocess
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0


def main():
    """CLI for uploading videos."""
    parser = argparse.ArgumentParser(
        description="Upload videos to YouTube as shorts"
    )
    parser.add_argument(
        '--video',
        required=True,
        help="Path to video file"
    )
    parser.add_argument(
        '--title',
        required=True,
        help="Video title"
    )
    parser.add_argument(
        '--description',
        default="",
        help="Video description"
    )
    parser.add_argument(
        '--tags',
        default="",
        help="Comma-separated tags"
    )
    parser.add_argument(
        '--main-video-url',
        help="URL to main video (added to description)"
    )
    parser.add_argument(
        '--privacy',
        default="public",
        choices=['public', 'private', 'unlisted'],
        help="Privacy status"
    )
    parser.add_argument(
        '--category',
        default="24",
        help="YouTube category ID (default: 24 = Entertainment)"
    )

    args = parser.parse_args()

    # Parse tags
    tags = [t.strip() for t in args.tags.split(',') if t.strip()] if args.tags else []

    # Upload video
    uploader = YouTubeUploader()
    result = uploader.upload_video(
        video_path=Path(args.video),
        title=args.title,
        description=args.description,
        tags=tags,
        category_id=args.category,
        privacy_status=args.privacy,
        main_video_url=args.main_video_url
    )

    if result.success:
        print(f"\n✅ SUCCESS")
        print(f"Video URL: {result.video_url}")
        return 0
    else:
        print(f"\n❌ FAILED")
        print(f"Error: {result.error}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
