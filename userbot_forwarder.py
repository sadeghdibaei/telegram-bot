# 🚀 Handles incoming Instagram links and media forwarding

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from config import INSTAGRAM_REGEX, IDOWNLOADER_BOT, MULTI_MEDIA_BOT, MAX_MEDIA_PER_GROUP
from state import media_buffer, pending_caption, last_instagram_link
from utils import build_final_caption

# ✅ Define Pyrogram client using environment variables
app = Client(
    "my_userbot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    session_string=os.getenv("SESSION_STRING")
)

# ✅ Register external handlers after app is defined
from handlers import register_handlers as register_bot_handlers
from cdn_handler import register_handlers as register_cdn_handlers
register_bot_handlers(app)
register_cdn_handlers(app)

# ✅ Local handler for Instagram links in group messages
@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        try:
            link = match.group(0)
            group_id = message.chat.id

            last_instagram_link[group_id] = link
            media_buffer.clear()

            # اولویت: iDownloadersBot
            await client.send_message(IDOWNLOADER_BOT, link)
            print("📤 Sent link to iDownloadersBot")

            # ⏳ اگر بعد از 10 ثانیه جوابی نیومد → fallback به Multi_Media_Downloader_bot
            async def fallback():
                await asyncio.sleep(10)
                if not media_buffer:
                    await client.send_message(MULTI_MEDIA_BOT, link)
                    print("↩️ Fallback to Multi_Media_Downloader_bot")

            asyncio.create_task(fallback())

            # پاک کردن پیام اصلی کاربر
            await message.delete()
            print("🗑️ Deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

# ✅ Shared logic for sending media + caption
async def send_album_with_caption(client: Client, group_id: int, caption: str):
    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        await client.send_media_group(group_id, media=chunk)
        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")
    await client.send_message(group_id, caption)
    print("📝 Sent caption with link")
    media_buffer.clear()

# ✅ Fallback timer if caption doesn't arrive
async def fallback_send(client: Client, group_id: int):
    await asyncio.sleep(10)
    if media_buffer:
        link = last_instagram_link.get(group_id, "")
        final_caption = build_final_caption(link)
        await send_album_with_caption(client, group_id, final_caption)
        pending_caption.pop(group_id, None)

# ✅ Start the userbot
print("🧪 Userbot forwarder is running...")
app.run()
