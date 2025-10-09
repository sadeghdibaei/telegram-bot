# 🚀 Handles incoming Instagram links and media forwarding

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import asyncio

from config import INSTAGRAM_REGEX, IDOWNLOADER_BOT, MAX_MEDIA_PER_GROUP
from state import media_buffer, pending_caption, last_instagram_link
from utils import build_final_caption

# ✅ تعریف app
app = Client("my_userbot")

# ✅ بعد از تعریف app، هندلرها رو ثبت کن
from handlers import register_handlers
register_handlers(app)

@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    """
    🔗 Detects Instagram link in group message and forwards to @iDownloadersBot.
    """
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        try:
            link = match.group(0)
            last_instagram_link[message.chat.id] = link
            media_buffer.clear()

            await client.send_message(IDOWNLOADER_BOT, link)
            await message.delete()
            print("📤 Sent link to iDownloadersBot and deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

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

app.run()
