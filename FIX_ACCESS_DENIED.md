# Fix: Error 403 - Access Denied

## Problem

```
Error 403: access_denied
wormhole has not completed the Google verification process.
The app is currently being tested, and can only be accessed by developer-approved testers.
```

## Solution: Add Yourself as Test User

### Step 1: Go to OAuth Consent Screen

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (the one you created earlier)
3. In left menu, go to: **APIs & Services** → **OAuth consent screen**

### Step 2: Add Test Users

1. Scroll down to **Test users** section
2. Click **"+ ADD USERS"** button
3. Enter your Google/Gmail email address (the one you want to upload videos from)
4. Click **"SAVE"**

### Step 3: Verify App Status

Make sure your app status shows:
- **Publishing status**: Testing ✓
- **User type**: External ✓

### Step 4: Retry Authentication

```bash
python scripts/test_youtube_auth.py
```

Now it should work!

## Visual Guide

```
Google Cloud Console
  └─ Select Project: "your-project-name"
      └─ APIs & Services
          └─ OAuth consent screen
              └─ Scroll down to "Test users"
                  └─ Click "+ ADD USERS"
                      └─ Enter your email
                      └─ Click "SAVE"
```

## Common Issues

### Issue: "Email not found"

**Solution:** Use the exact email address associated with your Google account (usually Gmail).

### Issue: Still getting error after adding email

**Solutions:**
1. Wait 1-2 minutes for changes to propagate
2. Clear browser cache/cookies
3. Try in incognito/private window
4. Make sure app is in "Testing" mode, not "Production"

### Issue: "App is in production mode"

**Solution:**
1. Go to OAuth consent screen
2. If it says "In Production", click "BACK TO TESTING"
3. This keeps your app in test mode (no verification needed)

## Why This Happens

Google requires apps to go through verification before they can be used by the public. However:
- **Testing mode**: Can be used immediately by up to 100 test users (no verification needed)
- **Production mode**: Requires Google verification (takes weeks)

For personal use, **testing mode is perfect** - just add your own email as a test user!

## After Adding Test User

Run the auth test again:

```bash
# This should now work
python scripts/test_youtube_auth.py
```

Expected output:
```
============================================================
YouTube API Authentication Test
============================================================

🌐 Opening browser for authentication...
   Please log in and grant permissions
✓ Authentication successful
✓ Saved credentials to credentials/youtube_token.pickle

============================================================
✅ SUCCESS - Authentication working!
============================================================
```

## Quick Checklist

- [ ] Go to Google Cloud Console
- [ ] Select your project
- [ ] Go to APIs & Services → OAuth consent screen
- [ ] Add your email as test user
- [ ] Save
- [ ] Wait 1-2 minutes
- [ ] Run `python scripts/test_youtube_auth.py`
- [ ] Should work now!
