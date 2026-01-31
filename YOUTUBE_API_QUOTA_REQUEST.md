# YouTube API Quota Increase Request - Project Documentation

## Project Overview

**Project Name:** Automated Story Video Publishing System

**Purpose:** Educational content automation system that generates and uploads short-form video content from public domain literary works.

## API Client Description

This is a command-line automation tool (not publicly accessible) that manages the upload pipeline for pre-produced video content.

### Functionality

1. **Video Upload Automation**
   - Uploads pre-rendered video files to YouTube
   - Automatically formats videos as YouTube Shorts (9:16 vertical format)
   - Sets appropriate metadata (title, description, tags)
   - Adds #shorts tag for short-form content discovery

2. **Batch Processing**
   - Processes multiple videos in sequence
   - Tracks upload progress and handles interruptions
   - Resumes from last successful upload if interrupted

3. **Content Management**
   - Organizes videos by episode/series
   - Maintains consistent naming and categorization
   - Links short-form videos to corresponding full episodes

## Technical Implementation

### Architecture

```
Pre-rendered Videos (Local)
    ↓
Automation Script (Python)
    ↓
YouTube API v3 (Upload)
    ↓
YouTube Channel (Published Content)
```

### API Usage

- **Primary API:** YouTube Data API v3
- **Main Operations:**
  - `videos.insert` - Upload video files
  - `videos.delete` - Remove incorrect uploads
  - `videos.update` - Modify metadata if needed

### Authentication
- OAuth 2.0 Desktop Application flow
- Single user account (content creator)
- Credentials stored locally, never shared

## Content Type

**Educational Content:** Animated story narrations from public domain literature

**Format:**
- Vertical video (1080x1920, 9:16 aspect ratio)
- Duration: 8-60 seconds per video
- YouTube Shorts format

**Source Material:**
- Classic literature (public domain)
- Educational storytelling
- Animated visual presentation with narration

## Current Limitations & Need for Quota Increase

### Current Quota Issues

**Default quota:** 10,000 units/day
**Upload cost:** 1,600 units per video
**Current capacity:** 6 videos per day

### Business Need

Our content production pipeline generates:
- 10-20 short videos per episode
- 2-3 episodes per week
- Target: 30-40 uploads per week

**With current quota:**
- Can only upload 6 videos per day
- Takes 2-3 days to publish one episode's worth of content
- Disrupts content release schedule

**Requested quota:** 100,000 units/day
**Would allow:** 60 uploads per day
**Benefit:** Publish complete episodes in single day, maintain consistent release schedule

## Use Case Justification

### Why This is Legitimate Use

1. **Pre-produced Content:** All videos are fully rendered before upload (not spam or auto-generated)
2. **Educational Value:** Classic literature adapted for modern short-form consumption
3. **Human Oversight:** All content reviewed before publishing
4. **Metadata Quality:** Proper titles, descriptions, tags applied to each video
5. **Content Strategy:** Shorts drive traffic to full-length episodes

### Not Spam or Abuse

- Videos are unique, high-quality animated content
- Each video has educational narrative value
- Proper metadata and categorization
- Follows YouTube Community Guidelines
- Single channel (not bulk uploading to multiple channels)

## Workflow Example

### Step 1: Content Production (Manual)
- Story text prepared
- Narration generated
- Animation/visuals created
- Videos rendered to MP4 files

### Step 2: Format Optimization (Automated)
- Convert to vertical format (9:16)
- Ensure duration appropriate for Shorts (<60s)
- Add metadata structure

### Step 3: Upload (API Automation)
- Script authenticates via OAuth
- Uploads videos sequentially
- Applies consistent metadata
- Tracks success/failure

### Step 4: Verification (Manual)
- Creator reviews published videos
- Verifies correct formatting
- Checks metadata accuracy

## API Client Screenshots/Documentation

### Tool Structure
```
the-arabian-nights/
├── credentials/
│   └── client_secret.json         # OAuth credentials
├── scripts/
│   ├── youtube_uploader.py        # Single video upload
│   └── upload_tiktok_batch.py     # Batch upload automation
├── output/
│   └── tiktok/
│       └── [episode]/
│           ├── clip_001.mp4       # Pre-rendered videos
│           ├── clip_002.mp4
│           └── ...
```

### Example Command
```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/episode_name \
  --episode-title "Episode Title" \
  --tags "shorts,educational,stories"
```

### Upload Process Output
```
📹 Found 10 clips to upload
📂 Directory: output/tiktok/episode_name
🎬 Episode: Episode Title

[1/10] Uploading clip_001
⬆️  Uploading: Episode Title - Part 1
   File: clip_001.mp4
   Duration: 8.4s
   Type: Short
✓ Upload successful!
   Video ID: ABC123
   URL: https://www.youtube.com/watch?v=ABC123
```

## Data Privacy & Security

- **User Data:** Only creator's own account accessed
- **Viewer Data:** No collection or processing of viewer data
- **API Scopes:**
  - `youtube.upload` - Upload videos
  - `youtube` - Manage own videos
- **No Third-Party Sharing:** Credentials never shared
- **Local Processing:** All video processing happens locally

## Compliance

- **YouTube Terms of Service:** Fully compliant
- **Community Guidelines:** Educational content, no violations
- **Copyright:** Public domain source material only
- **API Terms:** Proper OAuth flow, no credential sharing
- **Rate Limiting:** Respects API quotas and limits

## Technical Contact

**Developer:** [Your Name]
**Email:** [Your Email]
**Project Type:** Personal educational content automation
**Channel Type:** Educational storytelling

## Summary

This is a legitimate educational content automation system that:
- Uploads pre-produced, high-quality video content
- Uses YouTube Shorts format for educational storytelling
- Requires higher quota to maintain consistent publishing schedule
- Follows all YouTube policies and best practices
- Provides value to viewers through accessible classic literature

**Request:** Increase daily quota to 100,000 units to support 20-30 daily uploads for sustainable content production.
