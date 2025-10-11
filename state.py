# 🧠 Shared state across handlers
# All state is per-group to avoid cross-talk between groups.

# 📥 group_id -> list of InputMedia (photos/videos) buffered before sending as album
media_buffer = {}  # CHANGED from list to dict

# ⏱️ group_id -> asyncio.Task for delayed flush (caption + album)
pending_caption = {}

# 📦 group_id -> {step, link, caption}
# Optional: track upload progress or debug flow
upload_state = {}

# 🔗 group_id -> original Instagram link
last_instagram_link = {}

# ✅ group_id -> bool (True if any response received from iDownloadersBot or Multi_Media_Downloader_bot)
got_response = {}

# 📝 group_id -> list of unique cleaned captions (for deduplication)
captions_buffer = {}

# 🕒 group_id -> timestamp of last request sent to iDownloadersBot (for 30s cooldown)
last_idownloader_request = {}
