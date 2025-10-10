# 🎬 Handles CDN link responses and final media delivery from @urluploadxbot

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaVideo, InputMediaPhoto

from config import URLUPLOAD_BOT
from state import upload_state, media_buffer
from utils import build_final_caption

def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user(URLUPLOAD_BOT))
    async def handle_cdn_link(client: Client, message: Message):
        try:
            for group_id, state in upload_state.items():
                if message.reply_markup:
                    for row in message.reply_markup.inline_keyboard:
                        for i, btn in enumerate(row):
                            if "default" in btn.text.lower():
                                await message.click(i)
                                print(f"✅ Clicked 'Default' button: {btn.text}")
                                return

                if message.video:
                    media = InputMediaVideo(media=message.video.file_id)
                elif message.document and message.document.mime_type.startswith("video/"):
                    media = InputMediaVideo(media=message.document.file_id)
                elif message.photo:
                    media = InputMediaPhoto(media=message.photo.file_id)
                else:
                    print("⚠️ No valid media found in CDN response")
                    return

                media_buffer.append(media)
                caption = build_final_caption(state["link"], state["caption"])
                await client.send_media_group(group_id, media=[media])
                await client.send_message(group_id, caption)
                print("📤 Sent final media + caption")
                media_buffer.clear()
                upload_state.pop(group_id, None)

        except Exception as e:
            print("❌ Error handling CDN response:", e)
