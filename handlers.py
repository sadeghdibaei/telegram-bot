# 📦 Handles responses from iDownloadersBot and manages media + caption logic

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio

from config import MAX_MEDIA_PER_GROUP
from state import media_buffer, pending_caption, upload_state, last_instagram_link
from utils import build_final_caption

def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user("iDownloadersBot"))
    async def handle_bot_response(client: Client, message: Message):
        """
        🔁 Handles media, captions, CDN links, and fallback logic from iDownloadersBot.
        """
        try:
            for group_id, link in last_instagram_link.items():
                # 🎯 Check for CDN button
                if message.reply_markup:
                    for row in message.reply_markup.inline_keyboard:
                        for btn in row:
                            if btn.url and "cdn" in btn.url:
                                cdn_link = btn.url
                                caption = message.text or message.caption or ""
                                upload_state[group_id] = {
                                    "step": "waiting",
                                    "link": link,
                                    "caption": caption
                                }
                                await client.send_message("urluploadxbot", cdn_link)
                                print("📤 Sent CDN link to @urluploadxbot")
                                return

                # 📝 Check for caption
                if message.text or message.caption:
                    final_caption = build_final_caption(link, message.caption or message.text)
                    if pending_caption.get(group_id):
                        pending_caption[group_id].cancel()
                        del pending_caption[group_id]
                        print("🛑 Caption arrived: Cancelled timeout")
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                    else:
                        print("⚠️ No media found, caption skipped")
                    return

                # 📸 Check for media
                if message.photo:
                    media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                    print("📥 Buffered photo")
                elif message.video:
                    media_buffer.append(InputMediaVideo(media=message.video.file_id))
                    print("📥 Buffered video")

                # ⏱️ Start fallback timer
                if group_id not in pending_caption:
                    pending_caption[group_id] = asyncio.create_task(fallback_send(client, group_id))

        except Exception as e:
            print("❌ Error handling iDownloadersBot response:", e)

async def send_album_with_caption(client: Client, group_id: int, caption: str):
    """
    📸 Sends media in chunks of 10 with a separate caption message.
    """
    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        await client.send_media_group(group_id, media=chunk)
        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")
    await client.send_message(group_id, caption)
    print("📝 Sent caption with link")
    media_buffer.clear()

async def fallback_send(client: Client, group_id: int):
    """
    ⏱️ Sends media with link-only caption if no caption arrives within 10 seconds.
    """
    await asyncio.sleep(10)
    if media_buffer:
        link = last_instagram_link.get(group_id, "")
        final_caption = build_final_caption(link)
        await send_album_with_caption(client, group_id, final_caption)
        pending_caption.pop(group_id, None)
