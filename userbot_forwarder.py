import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
TARGET_GROUP_ID = int(os.environ["TARGET_GROUP_ID"])  # از محیط بخونه

app = Client("userbot_test", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# regex برای لینک‌های معتبر اینستاگرام
INSTAGRAM_REGEX = re.compile(r"(https?://)?(www\.)?instagram\.com/[^\s]+")

# نگهداری لینک آخر برای هر گروه
last_instagram_link = {}

@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        try:
            link = match.group(0)
            last_instagram_link[message.chat.id] = link

            await client.send_message("iDownloadersBot", link)
            print("📤 Sent link to iDownloadersBot")

            await message.delete()
            print("🗑️ Deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        # فقط آخرین گروهی که لینک فرستاده رو هندل می‌کنیم
        for group_id, link in last_instagram_link.items():
            caption = message.caption or message.text or ""
            link_tag = f'<a href="{link}">O P E N P O S T ⎋</a>'
            final_caption = f"{caption}\n\n{link_tag}"

            if message.photo:
                await client.send_photo(
                    group_id,
                    photo=message.photo.file_id,
                    caption=final_caption,
                    parse_mode="HTML"
                )
                print("📥 Forwarded photo with caption to group")

            elif message.document:
                await client.send_document(
                    group_id,
                    document=message.document.file_id,
                    caption=final_caption,
                    parse_mode="HTML"
                )
                print("📥 Forwarded document with caption to group")

            elif message.video:
                await client.send_video(
                    group_id,
                    video=message.video.file_id,
                    caption=final_caption,
                    parse_mode="HTML"
                )
                print("📥 Forwarded video with caption to group")

            elif message.text:
                await client.send_message(group_id, final_caption, parse_mode="HTML")
                print("📥 Forwarded text to group")

    except Exception as e:
        print("❌ Error forwarding bot response:", e)

print("🧪 Userbot test relay is running...")
app.run()
