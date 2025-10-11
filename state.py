# 🧠 Shared state across handlers

media_buffer = []  # 📥 List of InputMediaPhoto/InputMediaVideo objects
pending_caption = {}  # ⏱️ group_id → asyncio.Task for fallback caption
upload_state = {}  # 📦 group_id → {step, link, caption}
last_instagram_link = {}  # 🔗 group_id → original Instagram link
got_response = {}  # ✅ group_id → bool (True if any response received from iDownloadersBot or Multi_Media_Downloader_bot)
