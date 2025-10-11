# 🧠 Shared state across handlers
# ----------------------------------------------------------------------
# All states are stored per group_id to avoid cross-talk between groups

# 📥 group_id -> list of InputMedia (photos/videos) buffered before sending as album
media_buffer = {}

# ✅ group_id -> set of file_unique_id (to prevent duplicate media)
media_seen = {}

# ⏱️ group_id -> asyncio.Task for delayed flush (caption + album)
pending_caption = {}

# 📦 group_id -> {step, link, caption}
# Optional: can be used for debugging or tracking upload progress
upload_state = {}

# 🔗 group_id -> original Instagram link
last_instagram_link = {}

# ✅ group_id -> bool (True if any response received from iDownloadersBot or Multi_Media_Downloader_bot)
got_response = {}

# 📝 group_id -> list of unique cleaned captions (for deduplication)
captions_buffer = {}

# 🕒 group_id -> timestamp of last request sent to iDownloadersBot (for cooldown control)
last_idownloader_request = {}
