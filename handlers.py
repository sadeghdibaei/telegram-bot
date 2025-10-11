# 📦 Handles responses from iDownloadersBot and manages media + caption logic

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio
import traceback

from config import MAX_MEDIA_PER_GROUP, IDOWNLOADER_BOT, MULTI_MEDIA_BOT
from state import media_buffer, pending_caption, last_instagram_link
from utils import build_final_caption, clean_caption

def extract_button_url(message: Message) -> str | None:
    rm = getattr(message, "reply_markup", None)
    kb = getattr(rm, "inline_keyboard", None) if rm else None
    if not kb:
        return None
    for row in kb:
        for btn in row:
            url = getattr(btn, "url", None)
            if url:
                return url
    return None

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
        if not link:
            print("⚠️ Empty link in fallback")
            return
        final_caption = build_final_caption(link)
        await send_album_with_caption(client, group_id, final_caption)

def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user(IDOWNLOADER_BOT))
    async def handle_bot_response(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                print("⚠️ No group_id found in last_instagram_link")
                # Clean up the source message to keep the private chat tidy
                try:
                    await message.delete()
                except Exception:
                    pass
                return

            print(f"📩 Message from iDownloadersBot | group_id={group_id}")

            # 📸 Buffer media only (no caption attached to media groups)
            if message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")
                try:
                    await message.delete()
                except Exception:
                    pass
                return
            elif message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")
                try:
                    await message.delete()
                except Exception:
                    pass
                return

            # 📝 Accept caption only as a separate text message
            if message.text:
                # Prefer URL from inline button if present; otherwise use last_instagram_link
                button_url = extract_button_url(message)
                link = button_url or last_instagram_link.get(group_id, "")

                if not link:
                    print("⚠️ No link available (no button_url and no last_instagram_link)")
                    # Still forward cleaned caption even if link missing
                    final_caption = build_final_caption(link="", original_caption=message.text)
                else:
                    final_caption = build_final_caption(link, message.text)

                # Cancel any pending caption timeout since caption arrived
                if pending_caption.get(group_id):
                    pending_caption[group_id].cancel()
                    del pending_caption[group_id]
                    print("🛑 Caption arrived: Cancelled timeout")

                if media_buffer:
                    await send_album_with_caption(client, group_id, final_caption)
                else:
                    print("⚠️ Caption arrived but no media buffered")

                # Delete source caption message from iDownloadersBot
                try:
                    await message.delete()
                except Exception:
                    pass
                return

            print("⚠️ Message has no media or usable caption")
            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling iDownloadersBot response:", e)
            traceback.print_exc()
            try:
                await message.delete()
            except Exception:
                pass
    @app.on_message(filters.private & filters.user(MULTI_MEDIA_BOT))
    async def handle_multimedia_response(client: Client, message: Message):
        try:
            group_id = next(iter(last_instagram_link), None)
            if not group_id:
                print("⚠️ No group_id found for Multi_Media_Downloader_bot")
                return

            print(f"📩 Message from Multi_Media_Downloader_bot | group_id={group_id}")

            # 📸 مدیا + کپشن با هم میاد
            if message.photo:
                media = InputMediaPhoto(message.photo[-1].file_id)
            elif message.video:
                media = InputMediaVideo(message.video.file_id)
            else:
                print("⚠️ Unsupported media type")
                return

            # کپشن رو پاکسازی کن
            cleaned = clean_caption(message.caption or "")
            link = last_instagram_link.get(group_id, "")
            final_caption = build_final_caption(link, cleaned)

            # ارسال مدیا با کپشن نهایی
            if isinstance(media, InputMediaPhoto):
                await client.send_photo(group_id, media.media, caption=final_caption, parse_mode="HTML")
            else:
                await client.send_video(group_id, media.media, caption=final_caption, parse_mode="HTML")

            print("✅ Sent media with cleaned caption from Multi_Media_Downloader_bot")

            # پاک کردن پیام خام
            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            print("❌ Error handling Multi_Media_Downloader_bot response:", e)
            traceback.print_exc()
