# 📦 Handles responses from iDownloadersBot & Multi_Media_Downloader_bot

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio
import traceback

from config import MAX_MEDIA_PER_GROUP, IDOWNLOADER_BOT, MULTI_MEDIA_BOT
from state import media_buffer, pending_caption, last_instagram_link, got_response
from utils import build_final_caption, clean_caption


async def send_album_with_caption(client: Client, group_id: int, caption: str):
    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        await client.send_media_group(group_id, media=chunk)
        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")
    await client.send_message(group_id, caption)
    print("📝 Sent caption with link")
    media_buffer.clear()
    pending_caption.pop(group_id, None)


# -------------------------
# iDownloadersBot Handlers
# -------------------------

# ✅ PV: فقط پردازش، بدون حذف پیام
def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_pv(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return

            got_response[group_id] = True
            print(f"📩 [PV] Message from iDownloadersBot | group_id={group_id}")

            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video (PV)")
            elif message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo (PV)")

            if message.text or message.caption:
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, message.caption or message.text or "")
                if media_buffer:
                    await send_album_with_caption(client, group_id, final_caption)

        except Exception as e:
            print("❌ Error handling iDownloadersBot PV response:", e)
            traceback.print_exc()

    # ✅ Group: پردازش + حذف پیام خام
    @app.on_message(filters.group & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_group(client: Client, message: Message):
        try:
            group_id = message.chat.id
            got_response[group_id] = True
            print(f"📩 [Group] Message from iDownloadersBot | group_id={group_id}")

            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video (Group)")
            elif message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo[-1].file_id))
                print("📥 Buffered photo (Group)")

            if message.caption:
                cleaned = clean_caption(message.caption)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

            try:
                await message.delete()
                print("🗑️ Deleted raw iDownloadersBot message from group")
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling iDownloadersBot group response:", e)
            traceback.print_exc()


# -------------------------
# Multi_Media_Downloader_bot Handlers
# -------------------------

    # ✅ PV: فقط پردازش، بدون حذف پیام
    @app.on_message(filters.private & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_pv(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return

            got_response[group_id] = True
            print(f"📩 [PV] Message from Multi_Media_Downloader_bot | group_id={group_id}")

            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video (PV)")
            elif message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo[-1].file_id))
                print("📥 Buffered photo (PV)")

            if message.caption:
                cleaned = clean_caption(message.caption)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)
                if media_buffer:
                    await send_album_with_caption(client, group_id, final_caption)

        except Exception as e:
            print("❌ Error handling Multi_Media_Downloader_bot PV response:", e)
            traceback.print_exc()

    # ✅ Group: پردازش + حذف پیام خام
    @app.on_message(filters.group & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_group(client: Client, message: Message):
        try:
            group_id = message.chat.id
            got_response[group_id] = True
            print(f"📩 [Group] Message from Multi_Media_Downloader_bot | group_id={group_id}")

            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video (Group)")
            elif message.photo:
                media_buffer.append(InputMediaPhoto(message.photo[-1].file_id))
                print("📥 Buffered photo (Group)")

            if message.caption:
                cleaned = clean_caption(message.caption)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

            try:
                await message.delete()
                print("🗑️ Deleted raw Multi_Media_Downloader_bot message from group")
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling Multi_Media_Downloader_bot group response:", e)
            traceback.print_exc()
