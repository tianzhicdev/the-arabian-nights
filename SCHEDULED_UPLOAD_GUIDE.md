# Scheduled YouTube Upload Guide

Complete guide for automated daily uploads of Animal Farm episodes to YouTube using cron on Mac Mini.

## System Overview

**Structure**:
```
~/animal_farm_uploads/
├── episode_01/
│   ├── Episode_01_Old_Majors_Dream.mp4
│   ├── metadata.json
│   └── .uploaded (created after upload)
├── episode_02/
│   ├── Episode_02_The_Rebellion_Begins.mp4
│   └── metadata.json
...
```

**Upload Flow**:
1. Cron runs daily at 8:00 AM
2. Script checks `episode_XX/metadata.json` for `"uploaded": false`
3. If not uploaded, uploads video to YouTube
4. Updates `metadata.json` with upload info
5. Creates `.uploaded` marker file

---

## Step-by-Step Setup

### 1. Upload Episode 2 Now (From Local Machine)

```bash
cd ~/projects/the-arabian-nights
python scripts/upload_episode_with_metadata.py production_ready/animal_farm_uploads/episode_02
```

This will:
- Upload Episode 2 to YouTube
- Update metadata.json
- Create .uploaded marker

### 2. Transfer Files to Mac Mini

```bash
# Sync upload directory to Mac Mini
rsync -avz production_ready/animal_farm_uploads/ macmini:~/animal_farm_uploads/

# Sync YouTube credentials
rsync -avz credentials/youtube_token.pickle macmini:~/projects/the-arabian-nights/credentials/

# Sync upload scripts
rsync -avz scripts/upload_episode_with_metadata.py macmini:~/projects/the-arabian-nights/scripts/
rsync -avz scripts/youtube_uploader.py macmini:~/projects/the-arabian-nights/scripts/
```

### 3. Set Up Cron on Mac Mini

SSH into Mac Mini:
```bash
ssh macmini
```

Create cron script on Mac Mini:
```bash
cat > ~/upload_next_episode.sh << 'EOF'
#!/bin/bash
# Upload next unuploaded Animal Farm episode

# Configuration
UPLOAD_DIR="$HOME/animal_farm_uploads"
SCRIPT_DIR="$HOME/projects/the-arabian-nights/scripts"
LOG_DIR="$HOME/upload_logs"
LOG_FILE="$LOG_DIR/upload_$(date +%Y%m%d_%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Activate virtual environment
cd "$HOME/projects/the-arabian-nights"
source .venv/bin/activate

# Find next episode to upload
for ep_dir in "$UPLOAD_DIR"/episode_*/; do
    if [ ! -f "$ep_dir/.uploaded" ]; then
        echo "$(date): Found unuploaded episode: $ep_dir" >> "$LOG_FILE"

        # Upload episode
        python "$SCRIPT_DIR/upload_episode_with_metadata.py" "$ep_dir" >> "$LOG_FILE" 2>&1

        if [ $? -eq 0 ]; then
            echo "$(date): Upload successful!" >> "$LOG_FILE"
            exit 0
        else
            echo "$(date): Upload failed!" >> "$LOG_FILE"
            exit 1
        fi
    fi
done

echo "$(date): No more episodes to upload" >> "$LOG_FILE"
exit 0
EOF

chmod +x ~/upload_next_episode.sh
```

Add to crontab:
```bash
# Open crontab editor
crontab -e

# Add this line (uploads every day at 8:00 AM)
0 8 * * * /Users/biubiu/upload_next_episode.sh

# Save and exit (:wq in vim)
```

Verify cron setup:
```bash
crontab -l
```

---

## Quick Reference

### Upload Single Episode (Manual)

```bash
cd ~/projects/the-arabian-nights
source .venv/bin/activate
python scripts/upload_episode_with_metadata.py ~/animal_farm_uploads/episode_03
```

### Check Upload Status

```bash
# Show all episodes and upload status
for dir in ~/animal_farm_uploads/episode_*/; do
    ep=$(basename "$dir")
    if [ -f "$dir/.uploaded" ]; then
        url=$(head -1 "$dir/.uploaded")
        echo "✓ $ep - Uploaded: $url"
    else
        title=$(grep '"title"' "$dir/metadata.json" | cut -d'"' -f4)
        echo "⏳ $ep - Pending: $title"
    fi
done
```

### View Upload Logs (Mac Mini)

```bash
# Latest log
tail -50 ~/upload_logs/upload_*.log | tail -50

# All logs
ls -lt ~/upload_logs/
```

### Force Re-upload

```bash
# Remove .uploaded marker
rm ~/animal_farm_uploads/episode_03/.uploaded

# Edit metadata.json
vi ~/animal_farm_uploads/episode_03/metadata.json
# Change "uploaded": true to "uploaded": false

# Upload
python scripts/upload_episode_with_metadata.py ~/animal_farm_uploads/episode_03 --force
```

---

## Upload Schedule

Based on 8:00 AM daily uploads:

| Date | Episode | Title |
|------|---------|-------|
| 2026-01-30 | 1 | Old Major's Dream ✅ |
| Today | 2 | The Rebellion Begins (upload now) |
| Tomorrow 8 AM | 3 | The Summer of Hope |
| Day After 8 AM | 4 | The Battle of the Cowshed |
| +3 days | 5 | The Rise of Napoleon |
| +4 days | 6 | The Price of Progress |
| +5 days | 7 | The Bitter Winter |
| +6 days | 8 | The Battle of the Windmill |
| +7 days | 9 | The Fate of Boxer |
| +8 days | 10 | The Final Betrayal |

---

## Metadata File Structure

`episode_XX/metadata.json`:
```json
{
  "episode_number": 2,
  "video_filename": "Episode_02_The_Rebellion_Begins.mp4",
  "title": "Animal Farm Episode 2: The Rebellion Begins | George Orwell Classic",
  "subtitle": "The Rebellion Begins",
  "description": "Full description with emojis and links...",
  "tags": ["Animal Farm", "George Orwell", ...],
  "category_id": "27",
  "privacy_status": "public",
  "uploaded": false,
  "youtube_video_id": null,
  "youtube_url": null,
  "upload_date": null
}
```

After upload:
```json
{
  ...
  "uploaded": true,
  "youtube_video_id": "ABC123XYZ",
  "youtube_url": "https://www.youtube.com/watch?v=ABC123XYZ",
  "upload_date": "2026-01-31T08:00:15.123456"
}
```

---

## Troubleshooting

### Cron Not Running

```bash
# Check cron service
sudo launchctl list | grep cron

# Check cron logs
tail -f /var/log/system.log | grep cron

# Test script manually
~/upload_next_episode.sh
```

### Authentication Issues

```bash
# Re-authenticate on Mac Mini
cd ~/projects/the-arabian-nights
source .venv/bin/activate
rm credentials/youtube_token.pickle
python scripts/upload_episode_with_metadata.py ~/animal_farm_uploads/episode_02
# Follow OAuth flow in browser
```

### Upload Fails

Check logs:
```bash
cat ~/upload_logs/upload_*.log | tail -100
```

Common issues:
- **Quota exceeded**: Wait until midnight PT for quota reset
- **Network error**: Check internet connection
- **File not found**: Verify video file exists
- **Auth expired**: Re-authenticate (see above)

---

## Complete Setup Commands (Copy-Paste)

### On Local Machine:

```bash
# 1. Upload Episode 2
cd ~/projects/the-arabian-nights
python scripts/upload_episode_with_metadata.py production_ready/animal_farm_uploads/episode_02

# 2. Sync to Mac Mini
rsync -avz production_ready/animal_farm_uploads/ macmini:~/animal_farm_uploads/
rsync -avz credentials/youtube_token.pickle macmini:~/projects/the-arabian-nights/credentials/
rsync -avz scripts/upload_episode_with_metadata.py macmini:~/projects/the-arabian-nights/scripts/
rsync -avz scripts/youtube_uploader.py macmini:~/projects/the-arabian-nights/scripts/
```

### On Mac Mini:

```bash
# 3. Create upload script
cat > ~/upload_next_episode.sh << 'EOF'
#!/bin/bash
UPLOAD_DIR="$HOME/animal_farm_uploads"
SCRIPT_DIR="$HOME/projects/the-arabian-nights/scripts"
LOG_DIR="$HOME/upload_logs"
LOG_FILE="$LOG_DIR/upload_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"
cd "$HOME/projects/the-arabian-nights"
source .venv/bin/activate

for ep_dir in "$UPLOAD_DIR"/episode_*/; do
    if [ ! -f "$ep_dir/.uploaded" ]; then
        echo "$(date): Found unuploaded episode: $ep_dir" >> "$LOG_FILE"
        python "$SCRIPT_DIR/upload_episode_with_metadata.py" "$ep_dir" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "$(date): Upload successful!" >> "$LOG_FILE"
            exit 0
        else
            echo "$(date): Upload failed!" >> "$LOG_FILE"
            exit 1
        fi
    fi
done

echo "$(date): No more episodes to upload" >> "$LOG_FILE"
exit 0
EOF

chmod +x ~/upload_next_episode.sh

# 4. Test it
~/upload_next_episode.sh

# 5. Add to cron (uploads at 8 AM daily)
(crontab -l 2>/dev/null; echo "0 8 * * * /Users/biubiu/upload_next_episode.sh") | crontab -

# 6. Verify
crontab -l
```

---

## Summary

### What You Have:
- ✅ Episode 1 uploaded manually
- ✅ Episodes 2-10 ready with metadata
- ✅ Upload script with tracking
- ✅ Directory structure organized

### What To Do:
1. **Now**: Upload Episode 2 manually
2. **Now**: Sync files to Mac Mini
3. **On Mac Mini**: Set up cron for daily 8 AM uploads
4. **Tomorrow**: Episode 3 uploads automatically at 8 AM
5. **Following days**: Episodes 4-10 upload one per day

### Result:
- Fully automated uploads
- One episode per day at 8 AM
- Complete tracking via metadata.json
- Upload logs for debugging
- No manual intervention needed

Complete series uploaded in 8 more days!
