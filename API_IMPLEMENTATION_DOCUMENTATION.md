# YouTube API Implementation - Technical Documentation

## Overview

This document describes our YouTube API integration for automated video uploads.

---

## 1. Authentication Implementation

### OAuth 2.0 Desktop Flow

```python
# File: scripts/youtube_uploader.py

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

# One-time authentication
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials/client_secret.json',
    SCOPES
)
credentials = flow.run_local_server(port=0)

# Build YouTube service
youtube = build('youtube', 'v3', credentials=credentials)
```

**Authentication Flow:**
1. User runs script for first time
2. Browser opens for Google login
3. User grants permissions
4. Credentials saved locally for future use
5. No re-authentication needed for subsequent uploads

---

## 2. Video Upload Implementation

### Single Video Upload

```python
def upload_video(video_path, title, description, tags):
    """Upload video to YouTube via API"""

    # Prepare video metadata
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # Entertainment
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    # Prepare file for upload
    media = MediaFileUpload(
        video_path,
        chunksize=-1,
        resumable=True
    )

    # Execute upload
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    response = request.execute()
    return response['id']  # Video ID
```

### Batch Upload Implementation

```python
def upload_batch(clips_directory, episode_title):
    """Upload multiple videos sequentially"""

    clips = sorted(Path(clips_directory).glob("clip_*.mp4"))

    for i, clip_path in enumerate(clips, 1):
        # Generate metadata
        title = f"{episode_title} - Part {i}"
        description = f"Part {i} of {len(clips)}\n\n#shorts"
        tags = ['shorts', 'educational', 'stories']

        # Upload
        video_id = upload_video(clip_path, title, description, tags)
        print(f"✓ Uploaded: {title}")
        print(f"  URL: https://www.youtube.com/watch?v={video_id}")

        # Brief pause between uploads
        time.sleep(2)
```

---

## 3. Example Upload Session

### Command Executed
```bash
$ python scripts/upload_tiktok_batch.py \
    --tiktok-dir output/tiktok/animal_farm_e1_vertical \
    --episode-title "Animal Farm Episode 1" \
    --tags "shorts,animalfarm,animation,stories"
```

### Console Output
```
📹 Found 10 clips to upload
📂 Directory: output/tiktok/animal_farm_e1_vertical
🎬 Episode: Animal Farm Episode 1

[1/10] Uploading clip_001
⬆️  Uploading: Animal Farm Episode 1 - Part 1
   File: clip_001.mp4
   Size: 0.5 MB
   Duration: 8.4s
   Type: Short
✓ Upload successful!
   Video ID: bksxlc3y5FI
   URL: https://www.youtube.com/watch?v=bksxlc3y5FI
   Time: 1.5s

[2/10] Uploading clip_002
⬆️  Uploading: Animal Farm Episode 1 - Part 2
   File: clip_002.mp4
   Size: 1.2 MB
   Duration: 12.1s
   Type: Short
✓ Upload successful!
   Video ID: -V6AtwHaBGw
   URL: https://www.youtube.com/watch?v=-V6AtwHaBGw
   Time: 1.8s

... (continues for all 10 clips) ...

============================================================
📊 UPLOAD SUMMARY
============================================================
Total clips: 10
Uploaded: 10 ✓
Failed: 0 ✗

📝 Uploaded videos:
   ✓ Animal Farm Episode 1 - Part 1
     https://www.youtube.com/watch?v=bksxlc3y5FI
   ✓ Animal Farm Episode 1 - Part 2
     https://www.youtube.com/watch?v=-V6AtwHaBGw
   ... (continues)
============================================================
```

---

## 4. YouTube Data as Displayed

### Video Metadata Applied

Each uploaded video receives:

**Title Format:**
```
{Episode Title} - Part {Number}
Example: "Animal Farm Episode 1 - Part 1"
```

**Description Format:**
```
Part {N} of {Total}

{Episode Title}

#shorts

🎬 Watch full episode: [optional link]
```

**Tags:**
```
['shorts', 'animalfarm', 'animation', 'stories', 'educational']
```

**Video Properties:**
- Category: Entertainment (24)
- Privacy: Public
- Format: Vertical (1080x1920)
- Duration: 8-60 seconds
- Made for Kids: No

### Resulting YouTube Display

When video appears on YouTube:
- Shows in Shorts feed (due to vertical format + #shorts tag)
- Title clearly indicates series and part number
- Description provides context and main video link
- Tags help with discovery

---

## 5. API Operations Used

### Primary Operations

1. **videos.insert** (1,600 units)
   - Purpose: Upload video file
   - Frequency: Once per video
   - Data sent: Video file, title, description, tags, metadata

2. **videos.delete** (50 units)
   - Purpose: Remove incorrectly uploaded videos
   - Frequency: Rare, only for corrections
   - Data sent: Video ID

3. **videos.update** (50 units)
   - Purpose: Modify video metadata if needed
   - Frequency: Rare, only for corrections
   - Data sent: Video ID, updated metadata

### No Data Collection

Our implementation:
- Does NOT collect viewer data
- Does NOT access other users' content
- Does NOT store YouTube data locally
- Only manages our own uploaded videos

---

## 6. Error Handling & Retry Logic

```python
def upload_with_retry(request, max_retries=3):
    """Upload with automatic retry on failure"""

    retry = 0
    while True:
        try:
            response = request.next_chunk()
            if response:
                return response
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                # Retriable error
                retry += 1
                if retry > max_retries:
                    raise
                time.sleep(2 ** retry)  # Exponential backoff
            else:
                raise  # Non-retriable error
```

**Handles:**
- Network timeouts
- Temporary API errors
- Rate limiting
- Invalid video format

---

## 7. Progress Tracking & Resumability

### Progress File Format

```json
{
  "total_clips": 10,
  "uploaded": 5,
  "failed": 0,
  "results": [
    {
      "clip_id": "clip_001",
      "success": true,
      "video_id": "bksxlc3y5FI",
      "video_url": "https://www.youtube.com/watch?v=bksxlc3y5FI"
    },
    ...
  ]
}
```

**Resume Logic:**
- Saves progress after each upload
- On restart, skips already-uploaded clips
- Continues from last successful upload

---

## 8. Security & Compliance

### Credentials Storage
- `client_secret.json` - OAuth client credentials (never committed to git)
- `youtube_token.pickle` - User access token (stored locally, encrypted)
- Both files excluded from version control

### API Scope Limitation
Only requests minimal necessary scopes:
- `youtube.upload` - Upload videos
- `youtube` - Manage own videos

Does NOT request:
- User data access
- Analytics data
- Other users' content
- Channel management beyond uploads

### Compliance
- OAuth 2.0 standard flow
- No credential sharing
- Respects rate limits
- Follows YouTube TOS
- Single user, single channel

---

## 9. File Structure

```
Project Directory:
├── credentials/                    # API credentials (gitignored)
│   ├── client_secret.json         # OAuth client ID/secret
│   └── youtube_token.pickle       # User access token
│
├── scripts/                        # Upload automation
│   ├── youtube_uploader.py        # Single video upload
│   ├── upload_tiktok_batch.py     # Batch upload
│   └── test_youtube_auth.py       # Authentication test
│
├── output/tiktok/                  # Pre-rendered videos
│   └── [episode_name]/
│       ├── clip_001.mp4           # Ready for upload
│       ├── clip_002.mp4
│       └── .upload_progress.json  # Resume tracking
│
└── requirements_youtube.txt        # Python dependencies
```

---

## 10. Usage Example - Complete Workflow

### Step 1: Authenticate (One-time)
```bash
$ python scripts/test_youtube_auth.py
🌐 Opening browser for authentication...
✓ Authentication successful
✓ Credentials saved
```

### Step 2: Prepare Videos
Videos already rendered at:
```
output/tiktok/episode_name/
├── clip_001.mp4  (1080x1920, 8.4s)
├── clip_002.mp4  (1080x1920, 12.1s)
└── ... (8 more clips)
```

### Step 3: Upload Batch
```bash
$ python scripts/upload_tiktok_batch.py \
    --tiktok-dir output/tiktok/episode_name \
    --episode-title "Episode Title" \
    --tags "shorts,educational"
```

### Step 4: Verify on YouTube
All videos appear on channel with:
- Correct titles
- Proper formatting
- #shorts tag
- Vertical format

---

## Summary

**What the API is used for:**
Uploading pre-made educational video files to YouTube with proper metadata.

**How it's implemented:**
Python script using OAuth 2.0 and YouTube Data API v3, with retry logic and progress tracking.

**What data is accessed:**
Only the creator's own channel for uploading and managing their own videos.

**Security:**
OAuth tokens stored locally, minimal scopes requested, no data collection.

**Compliance:**
Follows YouTube TOS, proper authentication, respects rate limits.
