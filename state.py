# 🧠 Shared state across handlers

# 📥 Buffer for media (photos/videos) before sending as album
media_buffer = []

# ⏱️ group_id → asyncio.Task for delayed flush (caption + album)
pending_caption = {}

# 📦 group_id → {step, link, caption}
# Can be used for tracking upload progress or debugging
upload_state = {}

# 🔗 group_id → original Instagram link
last_instagram_link = {}

# ✅ group_id → bool (True if any response received from iDownloadersBot or Multi_Media_Downloader_bot)
got_response = {}

# 📝 group_id → list of unique cleaned captions (for deduplication)
captions_buffer = {}
