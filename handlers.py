# 📦 Handles responses from iDownloadersBot & Multi_Media_Downloader_bot
# ----------------------------------------------------------------------

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
    if group_id not in media_buffer or not media_buffer[group_id]:
        print(f"⚠️ No media to flush for group {group_id}")
        return

    print(f"📤 Flushing {len(media_buffer[group_id])} items to group {group_id}")

    # Split media into chunks (Telegram max 10 per album)
    chunks = [media_buffer[group_id][i:i + MAX_MEDIA_PER_GROUP]
              for i in range(0, len(media_buffer[group_id]), MAX_MEDIA_PER_GROUP)]
    for index, chunk in enumerate(chunks):
        try:
            await client.send_media_group(group_id, media=chunk)
            print(f"✅ Sent media group chunk {index + 1}/{len(chunks)}")
        except Exception as e:
            print(f"❌ Failed to send media group chunk {index + 1}: {e}")

    # Send caption separately
    if caption:
        await client.send_message(group_id, caption)
        print("📝 Sent caption with link")

    # Clear state
    media_buffer[group_id] = []
    captions_buffer[group_id] = []
    pending_caption.pop(group_id, None)


def schedule_flush(client: Client, group_id: int):
    """
    Schedule flush with dynamic delay depending on media count.
    """
    # Cancel previous pending flush if exists
    if group_id in pending_caption:
        try:
            pending_caption[group_id].cancel()
        except Exception:
            pass

    async def delayed_flush():
        # Dynamic delay: longer if album
        delay = 2
        if len(media_buffer.get(group_id, [])) > 1:
            delay = 5
        await asyncio.sleep(delay)

        if media_buffer.get(group_id):
            link = last_instagram_link.get(group_id, "")
            best_caption = max(captions_buffer[group_id], key=len) if captions_buffer.get(group_id) else ""
            final_caption = build_final_caption(link, best_caption)
            print(f"🚀 Triggering flush for group {group_id} with {len(media_buffer[group_id])} media")
            await send_album_with_caption(client, group_id, final_caption)

    pending_caption[group_id] = asyncio.create_task(delayed_flush())


def collect_caption(client: Client, group_id: int, raw_caption: str):
    """
    Collect caption (clean + dedup).
    """
    cleaned = clean_caption(raw_caption)
    if not cleaned:
        return

    captions_buffer.setdefault(group_id, [])

    if cleaned not in captions_buffer[group_id]:
        captions_buffer[group_id].append(cleaned)
        print(f"📝 Collected caption for group {group_id}: {cleaned[:60]}")

    # Reschedule flush with updated caption
    schedule_flush(client, group_id)


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

            media_buffer.setdefault(group_id, [])

            if message.photo:
                media_buffer[group_id].append(InputMediaPhoto(message.photo.file_id))
                print(f"📩 Buffered PHOTO from iDownloader for group {group_id}")
            elif message.video:
                media_buffer[group_id].append(InputMediaVideo(message.video.file_id))
                print(f"📩 Buffered VIDEO from iDownloader for group {group_id}")

            if message.caption or message.text:
                collect_caption(client, group_id, message.caption or message.text)
            else:
                # No caption → still schedule flush
                schedule_flush(client, group_id)

        except Exception as e:
            print("❌ Error handling iDownloadersBot PV:", e)
            traceback.print_exc()

    @app.on_message(filters.group & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_group(client: Client, message: Message):
        try:
            group_id = message.chat.id
            got_response[group_id] = True

            media_buffer.setdefault(group_id, [])

            if message.photo:
                media_buffer[group_id].append(InputMediaPhoto(message.photo.file_id))
                print(f"📩 Buffered PHOTO from iDownloader (group) {group_id}")
            elif message.video:
                media_buffer[group_id].append(InputMediaVideo(message.video.file_id))
                print(f"📩 Buffered VIDEO from iDownloader (group) {group_id}")

            if message.caption or message.text:
                collect_caption(client, group_id, message.caption or message.text)
            else:
                schedule_flush(client, group_id)

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

            media_buffer.setdefault(group_id, [])

            if message.photo:
                media_buffer[group_id].append(InputMediaPhoto(message.photo.file_id))
                print(f"📩 Buffered PHOTO from MultiMedia for group {group_id}")
            elif message.video:
                media_buffer[group_id].append(InputMediaVideo(message.video.file_id))
                print(f"📩 Buffered VIDEO from MultiMedia for group {group_id}")

            if message.caption or message.text:
                collect_caption(client, group_id, message.caption or message.text)
            else:
                schedule_flush(client, group_id)

        except Exception as e:
            print("❌ Error handling Multi_Media PV:", e)
            traceback.print_exc()
