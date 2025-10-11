# 📦 Handles responses from iDownloadersBot & Multi_Media_Downloader_bot
# -----------------------------------------
# Unified logic:
#   - Always buffer incoming media (photo/video).
#   - Collect all captions (separate or attached).
#   - Clean signatures and deduplicate captions.
#   - Flush after short delay: send album + single final caption.
#   - In private chats: do NOT delete bot messages.
#   - In groups: delete raw bot messages after processing.
# -----------------------------------------

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio
import traceback

from config import MAX_MEDIA_PER_GROUP, IDOWNLOADER_BOT, MULTI_MEDIA_BOT
from state import media_buffer, pending_caption, last_instagram_link, got_response, captions_buffer
from utils import build_final_caption, clean_caption


async def send_album_with_caption(client: Client, group_id: int, caption: str):
    """
    Flush the buffered media as an album, then send the caption separately.
    """
    # Split media into chunks (Telegram max 10 per album)
    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        await client.send_media_group(group_id, media=chunk)
        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")

    # Send caption separately
    await client.send_message(group_id, caption)
    print("📝 Sent caption with link")

    # Clear state
    media_buffer.clear()
    captions_buffer[group_id] = []
    pending_caption.pop(group_id, None)


def collect_caption_and_schedule_flush(client: Client, group_id: int, raw_caption: str):
    """
    Collect caption (clean + dedup), then schedule delayed flush.
    """
    cleaned = clean_caption(raw_caption)
    if not cleaned:
        return

    if group_id not in captions_buffer:
        captions_buffer[group_id] = []

    if cleaned not in captions_buffer[group_id]:
        captions_buffer[group_id].append(cleaned)
        print(f"📝 Collected caption: {cleaned[:60]}")

    # Cancel previous pending flush if exists
    if group_id in pending_caption:
        try:
            pending_caption[group_id].cancel()
        except Exception:
            pass

    async def delayed_flush():
        await asyncio.sleep(2)  # wait for all media
        if media_buffer:
            link = last_instagram_link.get(group_id, "")
            # pick the longest caption (usually the most complete)
            best_caption = max(captions_buffer[group_id], key=len) if captions_buffer[group_id] else ""
            final_caption = build_final_caption(link, best_caption)
            await send_album_with_caption(client, group_id, final_caption)

    pending_caption[group_id] = asyncio.create_task(delayed_flush())


def register_handlers(app: Client):

    # -------------------------
    # iDownloadersBot Handlers
    # -------------------------

    @app.on_message(filters.private & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_pv(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return
            got_response[group_id] = True

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo.file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # Collect caption if present
            if message.caption or message.text:
                collect_caption_and_schedule_flush(client, group_id, message.caption or message.text)

        except Exception as e:
            print("❌ Error handling iDownloadersBot PV:", e)
            traceback.print_exc()

    @app.on_message(filters.group & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_group(client: Client, message: Message):
        try:
            group_id = message.chat.id
            got_response[group_id] = True

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo.file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # Collect caption if present
            if message.caption or message.text:
                collect_caption_and_schedule_flush(client, group_id, message.caption or message.text)

            # Delete raw bot message
            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling iDownloadersBot group:", e)
            traceback.print_exc()


    # -------------------------
    # Multi_Media_Downloader_bot Handlers
    # -------------------------

    @app.on_message(filters.private & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_pv(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return
            got_response[group_id] = True
    
            # ✅ Always buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo.file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))
    
            # ✅ If caption exists, collect it separately
            if message.caption:
                collect_caption_and_schedule_flush(client, group_id, message.caption)
    
        except Exception as e:
            print("❌ Error handling Multi_Media PV:", e)
            traceback.print_exc()
    
