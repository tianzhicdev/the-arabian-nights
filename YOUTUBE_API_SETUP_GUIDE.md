# YouTube API Setup Guide - Upload Shorts Automatically

## Overview

To upload videos programmatically to YouTube, you need:
1. Google Cloud Project with YouTube Data API v3 enabled
2. OAuth 2.0 credentials (client_secret.json)
3. One-time authentication to get access token

## Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `arabian-nights-youtube` (or any name)
4. Click "Create"
5. Wait for project creation (takes ~30 seconds)

### Step 2: Enable YouTube Data API v3

1. In Google Cloud Console, select your new project
2. Go to "APIs & Services" → "Library"
3. Search for "YouTube Data API v3"
4. Click on it
5. Click "Enable"

### Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen first:
   - **User Type**: Choose "External" (for personal use)
   - Click "Create"
   - **App Information**:
     - App name: `Arabian Nights Video Uploader`
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - **Scopes**: Click "Add or Remove Scopes"
     - Search and add: `https://www.googleapis.com/auth/youtube.upload`
     - Search and add: `https://www.googleapis.com/auth/youtube`
     - Click "Update" → "Save and Continue"
   - **Test Users**: Add your Google account email
     - Click "Add Users" → Enter your email → "Add"
     - Click "Save and Continue"
   - Click "Back to Dashboard"

4. Now create OAuth client ID:
   - Go back to "Credentials" → "Create Credentials" → "OAuth client ID"
   - **Application type**: "Desktop app"
   - **Name**: `Arabian Nights Desktop Client`
   - Click "Create"

5. **Download credentials**:
   - A popup shows your client ID and secret
   - Click "Download JSON"
   - Save as `client_secret.json`

### Step 4: Place Credentials in Project

```bash
# Create credentials directory
mkdir -p credentials

# Move downloaded file
mv ~/Downloads/client_secret_*.json credentials/client_secret.json
```

**IMPORTANT**: Add to `.gitignore` to avoid committing secrets:
```bash
echo "credentials/" >> .gitignore
```

## File Structure

```
the-arabian-nights/
├── credentials/
│   ├── client_secret.json       # OAuth credentials (from Google Cloud)
│   └── youtube_token.json       # Generated after first auth (automatic)
├── scripts/
│   └── youtube_uploader.py      # Upload script (I'll create this)
└── output/
    └── tiktok/
        └── animal_farm_e1/
            ├── clip_001.mp4
            └── ...
```

## Security Best Practices

1. **Never commit credentials to git**:
   ```bash
   # Add to .gitignore
   credentials/
   client_secret*.json
   *token*.json
   ```

2. **Restrict API key usage** (optional):
   - In Google Cloud Console → Credentials
   - Click on your OAuth client ID
   - Add "Application restrictions" if needed

3. **Keep credentials safe**:
   - Don't share `client_secret.json`
   - Don't share `youtube_token.json`
   - Regenerate if compromised

## First-Time Authentication Flow

When you first run the upload script:

1. Script will open a browser window
2. You'll be asked to log in to your Google account
3. Grant permissions to upload videos
4. Browser will show "Authentication successful"
5. Script saves token to `credentials/youtube_token.json`
6. Future runs use saved token (no browser popup)

## Required Scopes

The script needs these OAuth scopes:
- `https://www.googleapis.com/auth/youtube.upload` - Upload videos
- `https://www.googleapis.com/auth/youtube` - Manage videos

## Quota Limits

YouTube API has daily quotas:
- **Daily quota**: 10,000 units
- **Video upload**: 1,600 units per upload
- **Max uploads per day**: ~6 videos

For higher limits, request quota increase from Google Cloud Console.

## Testing OAuth Setup

Before creating the full uploader, test OAuth flow:

```bash
# Install required library
pip install google-auth-oauthlib google-api-python-client

# Test authentication (I'll create test script)
python scripts/test_youtube_auth.py
```

## Summary Checklist

- [ ] Create Google Cloud Project
- [ ] Enable YouTube Data API v3
- [ ] Configure OAuth consent screen
- [ ] Add test users (your email)
- [ ] Create OAuth 2.0 client ID (Desktop app)
- [ ] Download `client_secret.json`
- [ ] Move to `credentials/client_secret.json`
- [ ] Add `credentials/` to `.gitignore`
- [ ] Run test authentication script
- [ ] Ready to upload videos!

## Next Steps

Once you have `credentials/client_secret.json` in place:

1. I'll create `scripts/youtube_uploader.py` - Upload shorts to YouTube
2. I'll create `scripts/upload_tiktok_batch.py` - Batch upload all clips
3. I'll add features:
   - Auto-generate titles and descriptions
   - Add links to main video in description
   - Set as YouTube Shorts (#shorts tag)
   - Schedule uploads
   - Track upload status

## Quick Setup Commands

```bash
# Create credentials directory
mkdir -p credentials

# After downloading from Google Cloud Console:
mv ~/Downloads/client_secret_*.json credentials/client_secret.json

# Add to gitignore
echo "credentials/" >> .gitignore
echo "client_secret*.json" >> .gitignore
echo "*token*.json" >> .gitignore

# Install Python libraries
pip install google-auth-oauthlib google-api-python-client

# Test authentication (after I create the script)
python scripts/test_youtube_auth.py
```

## Troubleshooting

### Error: "Access blocked: Arabian Nights Video Uploader has not completed the Google verification process"

**Solution**: This is normal for testing. Add your Google account as a test user:
- Google Cloud Console → OAuth consent screen
- "Test users" section → "Add Users"
- Add your email

### Error: "invalid_client: Unauthorized"

**Solution**:
- Re-download `client_secret.json` from Google Cloud Console
- Make sure it's in `credentials/client_secret.json`

### Error: "Quota exceeded"

**Solution**:
- Wait until next day (quota resets at midnight Pacific Time)
- Or request quota increase in Google Cloud Console

## Reference Links

- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Guide](https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps)
