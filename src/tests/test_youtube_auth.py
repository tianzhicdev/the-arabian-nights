"""
Test YouTube API authentication.

Run this first to verify OAuth setup before uploading videos.
"""

import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

# OAuth scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

# Credentials paths
PROJECT_ROOT = Path(__file__).parent.parent
CLIENT_SECRET_FILE = PROJECT_ROOT / 'credentials' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'credentials' / 'youtube_token.pickle'


def get_authenticated_service():
    """
    Authenticate with YouTube API.

    Returns:
        Credentials object if successful, None otherwise
    """
    credentials = None

    # Check if we have saved credentials
    if TOKEN_FILE.exists():
        print("📂 Found existing token file")
        try:
            with open(TOKEN_FILE, 'rb') as token:
                credentials = pickle.load(token)
            print("✓ Loaded saved credentials")
        except Exception as e:
            print(f"⚠️  Could not load saved credentials: {e}")
            credentials = None

    # If credentials are invalid or don't exist, authenticate
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("🔄 Refreshing expired credentials...")
            try:
                credentials.refresh(Request())
                print("✓ Credentials refreshed")
            except Exception as e:
                print(f"⚠️  Could not refresh credentials: {e}")
                credentials = None

        if not credentials:
            # Check if client secret exists
            if not CLIENT_SECRET_FILE.exists():
                print(f"\n❌ ERROR: client_secret.json not found!")
                print(f"   Expected location: {CLIENT_SECRET_FILE}")
                print(f"\n📖 Please follow YOUTUBE_API_SETUP_GUIDE.md to create credentials")
                return None

            print("\n🌐 Opening browser for authentication...")
            print("   Please log in and grant permissions")

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRET_FILE),
                    SCOPES
                )
                credentials = flow.run_local_server(
                    port=0,  # Use random available port
                    prompt='consent',
                    success_message='Authentication successful! You can close this window.'
                )
                print("✓ Authentication successful")
            except Exception as e:
                print(f"\n❌ Authentication failed: {e}")
                return None

            # Save credentials for future use
            try:
                TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(credentials, token)
                print(f"✓ Saved credentials to {TOKEN_FILE}")
            except Exception as e:
                print(f"⚠️  Could not save credentials: {e}")

    return credentials


def main():
    """Test authentication."""
    print("=" * 60)
    print("YouTube API Authentication Test")
    print("=" * 60)
    print()

    # Test authentication
    credentials = get_authenticated_service()

    if credentials:
        print("\n" + "=" * 60)
        print("✅ SUCCESS - Authentication working!")
        print("=" * 60)
        print("\nCredentials info:")
        print(f"  Token: {credentials.token[:20]}...")
        print(f"  Valid: {credentials.valid}")
        print(f"  Scopes: {', '.join(credentials.scopes)}")
        print("\n✓ Ready to upload videos to YouTube!")
        print("\nNext step: Run youtube_uploader.py to upload videos")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED - Could not authenticate")
        print("=" * 60)
        print("\n📖 Please check YOUTUBE_API_SETUP_GUIDE.md for setup instructions")
        return 1


if __name__ == '__main__':
    sys.exit(main())
