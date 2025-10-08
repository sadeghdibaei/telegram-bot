import os
import re
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InputMediaPhoto,
    InputMediaVideo
)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
TARGET_GROUP_ID = int(os.environ["TARGET_GROUP_ID"])

app = Client("userbot_test", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

INSTAGRAM_REGEX = re.compile(r"(https?://)?(www\.)?instagram\.com/[^\s]+")
last_instagram_link = {}
media_buffer = []

def clean_caption(text: str) -> str:
    blacklist = [
        "🤖 Downloaded with @iDownloadersBot",
        "🤖 دریافت شده توسط @iDownloadersBot"
    ]
    for phrase in blacklist:
        text = text.replace(phrase, "")
    return text.strip()

@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        try:
            link = match.group(0)
            last_instagram_link[message.chat.id] = link
            media_buffer.clear()

            await client.send_message("iDownloadersBot", link)
            print("📤 Sent link to iDownloadersBot")

            await message.delete()
            print("🗑️ Deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        for group_id, link in last_instagram_link.items():
            if message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")

            elif message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")

            elif message.text or message.caption:
                cleaned = clean_caption(message.caption or message.text or "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"


                if media_buffer:
                    await client.send_media_group(group_id, media=media_buffer)
                    print("📤 Sent media group")
                    media_buffer.clear()

                await client.send_message(
                    group_id,
                    final_caption
                )
                print("📥 Sent caption with link")

    except Exception as e:
        print("❌ Error forwarding bot response:", e)

print("🧪 Userbot relay with album + caption + link is running...")
app.run()
