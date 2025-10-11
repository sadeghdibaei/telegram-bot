# 📦 Handles responses from iDownloadersBot & Multi_Media_Downloader_bot
# handlers.py
# -----------------------------------------
# Unified handlers for iDownloadersBot and Multi_Media_Downloader_bot
# Logic:
#   - Always buffer incoming media (photo/video).
#   - Extract caption (whether separate or attached).
#   - When caption arrives, flush: send album + caption separately.
#   - In private chats: do NOT delete bot messages.
#   - In groups: delete raw bot messages after processing.
# -----------------------------------------

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio
import traceback

from config import MAX_MEDIA_PER_GROUP, IDOWNLOADER_BOT, MULTI_MEDIA_BOT
from state import media_buffer, pending_caption, last_instagram_link, got_response
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
    pending_caption.pop(group_id, None)


def register_handlers(app: Client):

    # -------------------------
    # iDownloadersBot Handlers
    # -------------------------

    @app.on_message(filters.private & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_pv(client: Client, message: Message):
        """
        Handle messages from iDownloadersBot in private chat.
        - Buffer media
        - Extract caption if present
        - Do NOT delete messages in PV
        """
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return

            got_response[group_id] = True
            print(f"📩 [PV] Message from iDownloadersBot | group_id={group_id}")

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo[-1].file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # If caption present, build final caption and flush
            if message.caption or message.text:
                cleaned = clean_caption(message.caption or message.text)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

        except Exception as e:
            print("❌ Error handling iDownloadersBot PV response:", e)
            traceback.print_exc()

    @app.on_message(filters.group & filters.user(IDOWNLOADER_BOT))
    async def handle_idownloader_group(client: Client, message: Message):
        """
        Handle messages from iDownloadersBot in groups.
        - Buffer media
        - Extract caption if present
        - Delete raw bot messages after processing
        """
        try:
            group_id = message.chat.id
            got_response[group_id] = True
            print(f"📩 [Group] Message from iDownloadersBot | group_id={group_id}")

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo[-1].file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # If caption present, build final caption and flush
            if message.caption or message.text:
                cleaned = clean_caption(message.caption or message.text)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

            # Delete raw bot message in group
            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling iDownloadersBot group response:", e)
            traceback.print_exc()


    # -------------------------
    # Multi_Media_Downloader_bot Handlers
    # -------------------------

    @app.on_message(filters.private & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_pv(client: Client, message: Message):
        """
        Handle messages from Multi_Media_Downloader_bot in private chat.
        - Buffer media
        - Extract caption if present (attached to first media)
        - Do NOT delete messages in PV
        """
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                return

            got_response[group_id] = True
            print(f"📩 [PV] Message from Multi_Media_Downloader_bot | group_id={group_id}")

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo[-1].file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # If caption present, build final caption and flush
            if message.caption:
                cleaned = clean_caption(message.caption)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

        except Exception as e:
            print("❌ Error handling Multi_Media_Downloader_bot PV response:", e)
            traceback.print_exc()

    @app.on_message(filters.group & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_group(client: Client, message: Message):
        """
        Handle messages from Multi_Media_Downloader_bot in groups.
        - Buffer media
        - Extract caption if present (attached to first media)
        - Delete raw bot messages after processing
        """
        try:
            group_id = message.chat.id
            got_response[group_id] = True
            print(f"📩 [Group] Message from Multi_Media_Downloader_bot | group_id={group_id}")

            # Buffer media
            if message.photo:
                media_buffer.append(InputMediaPhoto(message.photo[-1].file_id))
            elif message.video:
                media_buffer.append(InputMediaVideo(message.video.file_id))

            # If caption present, build final caption and flush
            if message.caption:
                cleaned = clean_caption(message.caption)
                link = last_instagram_link.get(group_id, "")
                final_caption = build_final_caption(link, cleaned)

                async def flush():
                    await asyncio.sleep(1)
                    if media_buffer:
                        await send_album_with_caption(client, group_id, final_caption)
                asyncio.create_task(flush())

            # Delete raw bot message in group
            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling Multi_Media_Downloader_bot group response:", e)
            traceback.print_exc()
