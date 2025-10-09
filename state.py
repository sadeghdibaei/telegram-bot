# 🧠 Shared state across handlers

media_buffer = []  # 📥 List of InputMediaPhoto/InputMediaVideo objects
pending_caption = {}  # ⏱️ group_id → asyncio.Task for fallback caption
upload_state = {}  # 📦 group_id → {step, link, caption}
last_instagram_link = {}  # 🔗 group_id → original Instagram link
