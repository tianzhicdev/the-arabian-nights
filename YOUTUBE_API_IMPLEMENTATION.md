# YouTube Programmatic Upload Implementation Guide

## 📋 Overview

This guide covers how to programmatically upload videos to YouTube using the YouTube Data API v3 with Python. Based on official documentation and best practices as of 2025.

---

## 🚀 Quick Start Summary

**What you need:**
1. Google account
2. Google Cloud project with YouTube Data API v3 enabled
3. OAuth 2.0 credentials
4. Python with `google-api-python-client` library

**Daily limits:**
- Default quota: 10,000 units/day
- Video upload cost: 1,600 units/upload
- **Result: ~6 video uploads per day** (default quota)

---

## 📦 Prerequisites

### 1. Install Required Libraries

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Create Google Cloud Project

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Name it: `Arabian-Nights-YouTube-Uploader`
4. Note your Project ID

### 3. Enable YouTube Data API v3

**Steps:**
1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "YouTube Data API v3"
3. Click **Enable**

### 4. Create OAuth 2.0 Credentials

**Steps:**
1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - User Type: **External** (for personal use)
   - App name: `Arabian Nights Uploader`
   - User support email: Your email
   - Developer contact: Your email
   - Add scope: `https://www.googleapis.com/auth/youtube.upload`
4. Application type: **Desktop app**
5. Name: `YouTube Uploader`
6. Click **Create**
7. **Download JSON** → Save as `client_secrets.json`

---

## 💻 Python Implementation

### Basic Upload Script

Save as `scripts/youtube_uploader.py`:

```python
#!/usr/bin/env python3
"""
YouTube Video Uploader
Uploads videos to YouTube using YouTube Data API v3
"""

import os
import sys
import argparse
from pathlib import Path
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes define the level of access
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# YouTube categories (IDs)
CATEGORIES = {
    'education': '27',
    'entertainment': '24',
    'people_blogs': '22',
    'howto_style': '26'
}


class YouTubeUploader:
    """Handle YouTube video uploads via API."""

    def __init__(self, client_secrets_file='client_secrets.json'):
        """
        Initialize YouTube uploader.

        Args:
            client_secrets_file: Path to OAuth2 credentials JSON
        """
        self.client_secrets_file = client_secrets_file
        self.youtube = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        creds = None
        token_file = 'token.json'

        # Load existing credentials
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # If no valid credentials, request new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                # New authentication flow
                print("Starting OAuth2 authentication flow...")
                print("Your browser will open for authorization.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next time
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("✓ Credentials saved to token.json")

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("✓ Authenticated with YouTube API")

    def upload_video(
        self,
        video_file,
        title,
        description,
        category='education',
        tags=None,
        privacy_status='private',
        thumbnail=None
    ):
        """
        Upload a video to YouTube.

        Args:
            video_file: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            category: Video category (default: 'education')
            tags: List of tags (max 500 chars total)
            privacy_status: 'public', 'private', or 'unlisted'
            thumbnail: Optional path to thumbnail image

        Returns:
            Video ID if successful, None otherwise
        """
        video_path = Path(video_file)
        if not video_path.exists():
            print(f"✗ Error: Video file not found: {video_file}")
            return None

        # Prepare video metadata
        body = {
            'snippet': {
                'title': title[:100],  # Max 100 chars
                'description': description[:5000],  # Max 5000 chars
                'tags': tags or [],
                'categoryId': CATEGORIES.get(category, CATEGORIES['education'])
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False  # Set appropriately
            }
        }

        # Prepare video file for upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,  # Upload entire file at once
            resumable=True
        )

        try:
            print(f"\nUploading: {video_path.name}")
            print(f"  Title: {title}")
            print(f"  Privacy: {privacy_status}")
            print()

            # Execute upload request
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  Upload progress: {progress}%", end='\r')

            print("\n✓ Upload complete!")

            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"  Video ID: {video_id}")
            print(f"  URL: {video_url}")

            # Upload thumbnail if provided
            if thumbnail and Path(thumbnail).exists():
                self.upload_thumbnail(video_id, thumbnail)

            return video_id

        except HttpError as e:
            print(f"\n✗ Upload failed: {e}")
            return None

    def upload_thumbnail(self, video_id, thumbnail_path):
        """
        Upload a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image (JPG/PNG)
        """
        try:
            print(f"\n  Uploading thumbnail: {Path(thumbnail_path).name}")

            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()

            print("  ✓ Thumbnail uploaded")

        except HttpError as e:
            print(f"  ✗ Thumbnail upload failed: {e}")

    def update_video(self, video_id, title=None, description=None, tags=None, privacy_status=None):
        """
        Update video metadata.

        Args:
            video_id: YouTube video ID
            title: New title (optional)
            description: New description (optional)
            tags: New tags list (optional)
            privacy_status: New privacy status (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current video details
            video = self.youtube.videos().list(
                part='snippet,status',
                id=video_id
            ).execute()

            if not video['items']:
                print(f"✗ Video not found: {video_id}")
                return False

            # Update metadata
            body = video['items'][0]

            if title:
                body['snippet']['title'] = title
            if description:
                body['snippet']['description'] = description
            if tags:
                body['snippet']['tags'] = tags
            if privacy_status:
                body['status']['privacyStatus'] = privacy_status

            # Update video
            self.youtube.videos().update(
                part='snippet,status',
                body=body
            ).execute()

            print(f"✓ Video updated: {video_id}")
            return True

        except HttpError as e:
            print(f"✗ Update failed: {e}")
            return False


def main():
    """Command-line interface for YouTube uploader."""
    parser = argparse.ArgumentParser(
        description='Upload videos to YouTube programmatically'
    )
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--title', required=True, help='Video title')
    parser.add_argument('--description', default='', help='Video description')
    parser.add_argument('--tags', help='Comma-separated tags')
    parser.add_argument('--category', default='education',
                       choices=['education', 'entertainment', 'people_blogs', 'howto_style'],
                       help='Video category')
    parser.add_argument('--privacy', default='private',
                       choices=['public', 'private', 'unlisted'],
                       help='Privacy status')
    parser.add_argument('--thumbnail', help='Path to thumbnail image')
    parser.add_argument('--client-secrets', default='client_secrets.json',
                       help='Path to OAuth2 client secrets JSON')

    args = parser.parse_args()

    # Parse tags
    tags = [tag.strip() for tag in args.tags.split(',')] if args.tags else []

    # Initialize uploader
    uploader = YouTubeUploader(client_secrets_file=args.client_secrets)

    # Upload video
    video_id = uploader.upload_video(
        video_file=args.video,
        title=args.title,
        description=args.description,
        category=args.category,
        tags=tags,
        privacy_status=args.privacy,
        thumbnail=args.thumbnail
    )

    if video_id:
        print("\n✓ SUCCESS!")
        sys.exit(0)
    else:
        print("\n✗ FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## 🎯 Usage Examples

### Example 1: Upload with Metadata

```bash
python scripts/youtube_uploader.py \
  output/animal_farm_slides_test/Old_Major\'s_Dream_slides.mp4 \
  --title "Animal Farm Episode 1 - Old Major's Dream | Illustrated Story" \
  --description "Experience George Orwell's timeless allegory..." \
  --tags "Animal Farm, George Orwell, classic literature, audiobook" \
  --category education \
  --privacy private
```

### Example 2: Upload with Thumbnail

```bash
python scripts/youtube_uploader.py \
  video.mp4 \
  --title "My Video Title" \
  --description "My video description" \
  --thumbnail thumbnail.jpg \
  --privacy public
```

### Example 3: Batch Upload Script

Create `scripts/batch_upload.py`:

```python
#!/usr/bin/env python3
"""Batch upload multiple episodes to YouTube."""

from youtube_uploader import YouTubeUploader
from pathlib import Path
import json

def batch_upload_episodes(episodes_dir, metadata_file):
    """
    Upload multiple episodes from a directory.

    Args:
        episodes_dir: Directory containing episode videos
        metadata_file: JSON file with metadata for each episode
    """
    # Load metadata
    with open(metadata_file, 'r') as f:
        episodes = json.load(f)

    # Initialize uploader
    uploader = YouTubeUploader()

    results = []

    for episode in episodes:
        video_path = Path(episodes_dir) / episode['filename']

        if not video_path.exists():
            print(f"⚠️  Skipping {episode['filename']}: file not found")
            continue

        print(f"\n{'='*80}")
        print(f"Uploading Episode {episode['number']}")
        print(f"{'='*80}")

        video_id = uploader.upload_video(
            video_file=str(video_path),
            title=episode['title'],
            description=episode['description'],
            tags=episode.get('tags', []),
            privacy_status='private',  # Upload as private first
            thumbnail=episode.get('thumbnail')
        )

        results.append({
            'episode': episode['number'],
            'video_id': video_id,
            'success': video_id is not None
        })

    # Print summary
    print(f"\n{'='*80}")
    print("UPLOAD SUMMARY")
    print(f"{'='*80}")
    successful = sum(1 for r in results if r['success'])
    print(f"Total: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")

    return results

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: batch_upload.py <episodes_dir> <metadata.json>")
        sys.exit(1)

    batch_upload_episodes(sys.argv[1], sys.argv[2])
```

Metadata JSON format (`episodes_metadata.json`):

```json
[
  {
    "number": 1,
    "filename": "Old_Major's_Dream_slides.mp4",
    "title": "Animal Farm Episode 1 - Old Major's Dream",
    "description": "Experience George Orwell's...",
    "tags": ["Animal Farm", "George Orwell", "classic literature"],
    "thumbnail": "thumbnails/ep1.jpg"
  },
  {
    "number": 2,
    "filename": "The_Rebellion_slides.mp4",
    "title": "Animal Farm Episode 2 - The Rebellion",
    "description": "...",
    "tags": ["Animal Farm", "George Orwell"],
    "thumbnail": "thumbnails/ep2.jpg"
  }
]
```

---

## 📊 Quota Management

### Understanding Quota Costs

| Operation | Cost (units) | Daily Limit |
|-----------|--------------|-------------|
| Upload video | 1,600 | 6 uploads |
| Update video | 50 | 200 updates |
| Search | 100 | 100 searches |
| Get video details | 1 | 10,000 queries |

**Default Daily Quota: 10,000 units**

### Monitoring Quota Usage

**In Google Cloud Console:**
1. Go to **APIs & Services** → **Dashboard**
2. Select **YouTube Data API v3**
3. View **Quotas** tab

### Requesting Higher Quotas

**If you need more than 6 uploads/day:**

1. Go to [YouTube API Quota Extension Form](https://support.google.com/youtube/contact/yt_api_form)
2. Provide:
   - Project details
   - Use case explanation
   - Expected usage
   - Compliance with YouTube policies
3. Wait for review (can take 1-2 weeks)

**Tips for approval:**
- Clear educational or creative use case
- Demonstrate content quality
- Show audience engagement
- Prove compliance with YouTube ToS

---

## 🛡️ Best Practices

### 1. **Security**

```bash
# NEVER commit client_secrets.json or token.json to git
echo "client_secrets.json" >> .gitignore
echo "token.json" >> .gitignore

# Store credentials securely
chmod 600 client_secrets.json
chmod 600 token.json
```

### 2. **Error Handling**

```python
from googleapiclient.errors import HttpError
import time

def upload_with_retry(uploader, video_file, max_retries=3):
    """Upload with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return uploader.upload_video(video_file, ...)
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                # Server error - retry
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Server error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Client error - don't retry
                raise
    return None
```

### 3. **Rate Limiting**

```python
import time

def upload_multiple_videos(videos, delay=10):
    """Upload multiple videos with rate limiting."""
    uploader = YouTubeUploader()

    for i, video_info in enumerate(videos):
        print(f"\nUploading {i+1}/{len(videos)}")
        uploader.upload_video(**video_info)

        # Wait between uploads to avoid rate limits
        if i < len(videos) - 1:
            print(f"Waiting {delay}s before next upload...")
            time.sleep(delay)
```

### 4. **Logging**

```python
import logging

logging.basicConfig(
    filename='youtube_uploads.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log all upload attempts
logger.info(f"Uploading: {video_title}")
logger.info(f"Video ID: {video_id}")
```

---

## 🔧 Troubleshooting

### Error: "insufficientPermissions"
**Solution:** Check OAuth2 scope includes `youtube.upload`

### Error: "quotaExceeded"
**Solution:** Wait 24 hours or request quota increase

### Error: "invalidTitle"
**Solution:** Title must be 1-100 characters

### Error: "invalidDescription"
**Solution:** Description max 5000 characters

### Video stuck in "Processing"
**Solution:** Normal - can take hours for long videos

### Can't set thumbnail
**Solution:** Requires verified YouTube account (phone verification)

---

## 📈 Advanced Features

### Add to Playlist

```python
def add_to_playlist(youtube, video_id, playlist_id):
    """Add video to a playlist."""
    youtube.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
    ).execute()
```

### Schedule Video

```python
from datetime import datetime, timedelta

def schedule_video(youtube, video_id, publish_time):
    """Schedule video for future publication."""
    youtube.videos().update(
        part='status',
        body={
            'id': video_id,
            'status': {
                'privacyStatus': 'private',
                'publishAt': publish_time.isoformat() + 'Z'
            }
        }
    ).execute()

# Example: Schedule for tomorrow at 2 PM
publish_time = datetime.now() + timedelta(days=1)
publish_time = publish_time.replace(hour=14, minute=0)
schedule_video(youtube, video_id, publish_time)
```

---

## 📚 Additional Resources

**Official Documentation:**
- [YouTube Data API v3 Docs](https://developers.google.com/youtube/v3)
- [Upload Guide](https://developers.google.com/youtube/v3/guides/uploading_a_video)
- [Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)

**Python Libraries:**
- [google-api-python-client](https://github.com/googleapis/google-api-python-client)
- [google-auth](https://google-auth.readthedocs.io/)

**Community Resources:**
- [YouTube API on Stack Overflow](https://stackoverflow.com/questions/tagged/youtube-api)
- [r/youtube on Reddit](https://reddit.com/r/youtube)

---

## ✅ Implementation Checklist

- [ ] Create Google Cloud project
- [ ] Enable YouTube Data API v3
- [ ] Create OAuth 2.0 credentials
- [ ] Download `client_secrets.json`
- [ ] Install Python dependencies
- [ ] Create `youtube_uploader.py` script
- [ ] Test authentication flow
- [ ] Test single video upload (private)
- [ ] Review video in YouTube Studio
- [ ] Create batch upload script (if needed)
- [ ] Set up logging
- [ ] Add error handling
- [ ] Monitor quota usage
- [ ] Document your workflow

---

Generated: 2026-01-28
Last Updated: 2026-01-28
Version: 1.0
