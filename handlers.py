# 📦 Handles responses from iDownloadersBot and manages media + caption logic

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio
import traceback

from config import MAX_MEDIA_PER_GROUP, IDOWNLOADER_BOT
from state import media_buffer, pending_caption, upload_state, last_instagram_link
from utils import build_final_caption

def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user(IDOWNLOADER_BOT))
    async def handle_bot_response(client: Client, message: Message):
        try:
            chat_id = message.chat.id
            group_id = chat_id  # فرض بر اینه که group_id همونه

            print(f"📩 Message from iDownloadersBot | chat_id={chat_id}")

            # 📸 مدیا اول بررسی بشه
            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")
            elif message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")
            else:
                print("⚠️ No media found in message")

            # 📝 کپشن بعد بررسی بشه
            if message.text or message.caption:
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, message.caption or message.text)

                if pending_caption.get(group_id):
                    pending_caption[group_id].cancel()
                    del pending_caption[group_id]
                    print("🛑 Caption arrived: Cancelled timeout")

                if media_buffer:
                    await send_album_with_caption(client, group_id, final_caption)
                else:
                    print("⚠️ Caption arrived but no media buffered")
                return

            # ⏱️ fallback فقط اگر کپشن نیومده
            if group_id not in pending_caption:
                pending_caption[group_id] = asyncio.create_task(fallback_send(client, group_id))

        except Exception as e:
            print("❌ Error handling iDownloadersBot response:", e)
            traceback.print_exc()

async def send_album_with_caption(client: Client, group_id: int, caption: str):
    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        await client.send_media_group(group_id, media=chunk)
        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")
    await client.send_message(group_id, caption)
    print("📝 Sent caption with link")
    media_buffer.clear()
    pending_caption.pop(group_id, None)

async def fallback_send(client: Client, group_id: int):
    await asyncio.sleep(10)
    if media_buffer:
        link = last_instagram_link.get(group_id, "")
        final_caption = build_final_caption(link)
        await send_album_with_caption(client, group_id, final_caption)
