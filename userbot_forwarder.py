# 🚀 Handles incoming Instagram links and media forwarding

import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message

from config import INSTAGRAM_REGEX, IDOWNLOADER_BOT, MULTI_MEDIA_BOT, MAX_MEDIA_PER_GROUP
from state import media_buffer, pending_caption, last_instagram_link, got_response, captions_buffer, last_idownloader_request
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
    if not match:
        return

    try:
        link = match.group(0)
        group_id = message.chat.id

        # Reset state for this group
        last_instagram_link[group_id] = link
        media_buffer.clear()
        captions_buffer[group_id] = []
        got_response[group_id] = False

        now = time.time()
        last_time = last_idownloader_request.get(group_id, 0)
        elapsed = now - last_time

        if elapsed < 30:
            # ⏱️ Less than 30s since last request → send directly to backup bot
            await client.send_message(MULTI_MEDIA_BOT, link)
            print(f"⚡ Sent link directly to Multi_Media_Downloader_bot (cooldown active) | group_id={group_id}")

            async def fallback_to_idownloader():
                # Wait until cooldown finishes
                await asyncio.sleep(30 - elapsed)
                if not got_response.get(group_id, False):
                    # Retry with iDownloadersBot after cooldown
                    await client.send_message(IDOWNLOADER_BOT, link)
                    last_idownloader_request[group_id] = time.time()
                    print(f"↩️ Fallback: sent to iDownloadersBot after cooldown | group_id={group_id}")

                    # If still no response → notify group
                    await asyncio.sleep(10)
                    if not got_response.get(group_id, False):
                        await client.send_message(group_id, f"⚠️ Please try again\n{link}")

            asyncio.create_task(fallback_to_idownloader())

        else:
            # ✅ More than 30s passed → try iDownloadersBot first
            await client.send_message(IDOWNLOADER_BOT, link)
            last_idownloader_request[group_id] = now
            print(f"📤 Sent link to iDownloadersBot | group_id={group_id}")

            async def fallback_to_multimedia():
                # Wait 3s for iDownloadersBot response
                await asyncio.sleep(3)
                if not got_response.get(group_id, False):
                    # No response → send to Multi_Media_Downloader_bot
                    await client.send_message(MULTI_MEDIA_BOT, link)
                    print(f"↩️ No response from iDownloadersBot → fallback to Multi_Media_Downloader_bot | group_id={group_id}")

                    # If still no response → notify group
                    await asyncio.sleep(10)
                    if not got_response.get(group_id, False):
                        await client.send_message(group_id, f"⚠️ Please try again\n{link}")

            asyncio.create_task(fallback_to_multimedia())

        # Delete original user message from group
        try:
            await message.delete()
            print("🗑️ Deleted original message from group")
        except:
            pass

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
    captions_buffer[group_id] = []   # ✅ clear captions buffer

# ✅ Fallback timer if caption doesn't arrive
async def fallback_send(client: Client, group_id: int):
    await asyncio.sleep(10)
    if media_buffer:
        link = last_instagram_link.get(group_id, "")
        final_caption = build_final_caption(link)
        await send_album_with_caption(client, group_id, final_caption)
        pending_caption.pop(group_id, None)
        captions_buffer[group_id] = []   # ✅ clear captions buffer
        
# ✅ Start the userbot
print("🧪 Userbot forwarder is running...")
app.run()
