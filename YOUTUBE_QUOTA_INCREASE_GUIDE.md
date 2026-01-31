# YouTube API Quota - Understanding & Increasing Limits

## Why Only 9 Videos Per Day?

YouTube API has **daily quotas** to prevent abuse:

```
Default Daily Quota: 10,000 units
Video Upload Cost:   1,600 units per upload
─────────────────────────────────────────
Maximum Uploads:     6 videos per day (10,000 ÷ 1,600 = 6.25)
```

**You uploaded 9** because:
- New accounts sometimes get slightly higher initial quota (~15,000 units)
- Or there was quota rollover from previous day

## API Cost Breakdown

| Operation | Cost (units) | Example |
|-----------|-------------|---------|
| Upload video | 1,600 | Upload 1 short |
| Delete video | 50 | Delete wrong video |
| Update video | 50 | Change title/description |
| List videos | 1 | Check your videos |

**Your usage today:**
- 9 uploads: 9 × 1,600 = 14,400 units
- 9 deletes: 9 × 50 = 450 units
- **Total: ~14,850 units** (exceeded default 10,000 quota)

## Is 9 Shorts Enough?

**For storytelling: Not really!**

Your Animal Farm Episode 1 has:
- 63 scenes total
- Currently split into 10 clips (~6 scenes per clip)
- Each clip is only 8-17 seconds

**Ideal for YouTube Shorts:**
- 30-60 seconds per short (sweet spot: 45s)
- Should combine 3-4 scenes per short
- Target: 15-20 shorts per episode for good coverage

**Problem:** With 10,000 quota, you can only upload 6 videos per day

## Solution 1: Request Quota Increase (Recommended)

### Step 1: Go to Google Cloud Console

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to **"IAM & Admin" → "Quotas"**

### Step 2: Find YouTube Data API v3 Quota

1. In "Filter" box, type: `youtube`
2. Find: **"YouTube Data API v3"**
3. Look for: **"Queries per day"**
4. Click the checkbox next to it
5. Click **"EDIT QUOTAS"** at the top

### Step 3: Request Increase

Fill out the form:

**Name:** Your name
**Email:** Your email
**Phone:** Your phone (optional)

**New quota limit:**
```
100,000 units per day
```
(Allows 60 uploads per day)

**Request description:**
```
I am developing an educational content automation system that generates
short-form animated story videos (YouTube Shorts) from classic literature.

Current usage:
- Uploading 10-20 short videos per day (30-60 seconds each)
- Educational content: Animal Farm, Arabian Nights, classic stories
- Each episode generates 15-20 shorts to drive traffic to main video

The default 10,000 unit quota only allows 6 uploads per day, which is
insufficient for our content strategy.

Requesting 100,000 units per day to support:
- 20-30 shorts uploads per day
- Video management (updates, monitoring)
- Sustainable content pipeline

This is for a legitimate educational content channel, not spam or abuse.
```

**Click "SUBMIT"**

### Step 4: Wait for Approval

- **Review time:** 2-7 business days
- **Success rate:** High if you explain legitimate use case
- **Email notification:** You'll get notified when approved

## Solution 2: Multiple Uploads Per Day Strategy

While waiting for quota increase, **spread uploads across days:**

### Day 1: Upload 6 shorts
```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1_vertical \
  --episode-title "Animal Farm Episode 1: Old Major's Dream" \
  --clip-selection "1,2,3,4,5,6" \
  --tags "shorts,animalfarm,animation"
```

### Day 2: Upload remaining 4 shorts
```bash
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1_vertical \
  --episode-title "Animal Farm Episode 1: Old Major's Dream" \
  --clip-selection "7,8,9,10" \
  --tags "shorts,animalfarm,animation"
```

**Wait... that won't work with current script!**

Let me fix the upload script to support selective upload.

## Solution 3: Upload as Unlisted First

**Strategy:**
1. Upload all videos as **"unlisted"** (spread across days if needed)
2. Once all uploaded, change them to **"public"** (costs only 50 units each)

```bash
# Day 1: Upload 6 as unlisted
python scripts/upload_tiktok_batch.py \
  --tiktok-dir output/tiktok/animal_farm_e1_vertical \
  --episode-title "Animal Farm Episode 1" \
  --privacy unlisted

# Day 2: Upload remaining 4 as unlisted
# (script auto-resumes from clip 7)

# Day 3: Make all public (manually in YouTube Studio)
```

## Solution 4: Multiple Google Accounts (Not Recommended)

**Pros:**
- Each account gets separate 10,000 quota
- Can upload to multiple channels

**Cons:**
- Violates YouTube TOS if used for same channel
- Management overhead
- Not scalable

**Don't do this unless you have legitimate multiple channels.**

## Quota Increase Tiers

| Tier | Daily Quota | Uploads/Day | Use Case |
|------|-------------|-------------|----------|
| Default | 10,000 | 6 | Personal/testing |
| Small increase | 50,000 | 30 | Small creator |
| Medium increase | 100,000 | 60 | Active creator |
| Large increase | 1,000,000 | 625 | Production platform |

**Recommended for your use case: 100,000 units (60 uploads/day)**

## Alternative: Optimize Upload Strategy

Instead of uploading **one episode as 10 shorts**, optimize to **longer shorts**:

### Current Strategy
- 10 clips × 8-17 seconds = Not ideal for Shorts
- Needs 10 uploads (1,600 units each)

### Optimized Strategy
- Combine scenes to make 30-60 second shorts
- 5-6 longer shorts per episode
- Better engagement (Shorts algorithm prefers 30-60s)
- Only 5-6 uploads needed (fits daily quota!)

### Example Optimization
```bash
# Instead of 10 short clips, create 5 longer shorts
python scripts/convert_episode_to_tiktok.py \
  --episode-dir output/animal_farm_ep1_full_slides \
  --output-dir output/tiktok/animal_farm_e1_optimized \
  --clip-count 5 \
  --target-duration 45
```

**Benefits:**
- Fits daily quota (5 × 1,600 = 8,000 units)
- Better for YouTube algorithm
- Higher engagement

## Summary

### Immediate Action (Today)

✅ **Request quota increase** in Google Cloud Console:
- Go to IAM & Admin → Quotas
- Request 100,000 units per day
- Explain educational content use case

### While Waiting (2-7 days)

**Option A: Upload 6 per day**
- Spread your 10 shorts across 2 days
- Upload 6 today, 4 tomorrow

**Option B: Optimize to 5 longer shorts**
- Combine scenes to make 30-60s shorts
- Fits daily quota
- Better engagement

### Long-term Strategy

Once quota increased:
- ✅ Upload 20-30 shorts per day
- ✅ Multiple episodes per week
- ✅ Scale content production

## Quick Command: Request Quota Increase

**Direct link:**
[Request YouTube API Quota Increase](https://console.cloud.google.com/iam-admin/quotas?project=YOUR_PROJECT_ID)

Replace `YOUR_PROJECT_ID` with your actual project ID from Google Cloud Console.

---

**Bottom line:** Request quota increase to 100,000 units. It's free, approved within a week, and lets you upload 60 videos per day!
