from pyrogram import Client, filters
import requests
import os

# متغیرهای محیطی
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]  # سشن یوزربات (با pyrogram genstring می‌سازی)
BOT_ENDPOINT = os.environ["BOT_ENDPOINT"]      # آدرس وبهوک بات اصلی (مثلاً https://yourapp.up.railway.app/userbot)

# یوزربات
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# هر پیامی که از @iDownloadersBot بیاد
@app.on_message(filters.chat("iDownloadersBot"))
async def forward_to_bot(client, message):
    try:
        # اگر مدیا بود
        if message.photo or message.video:
            file_id = message.photo.file_id if message.photo else message.video.file_id
            payload = {
                "chat_id": message.chat.id,
                "file_id": file_id,
                "type": "photo" if message.photo else "video",
                "caption": message.caption or ""
            }
            requests.post(f"{BOT_ENDPOINT}", json=payload)

        # اگر متن (کپشن جدا) بود
        elif message.text:
            payload = {
                "chat_id": message.chat.id,
                "text": message.text
            }
            requests.post(f"{BOT_ENDPOINT}", json=payload)

    except Exception as e:
        print("Error forwarding:", e)

print("👤 Userbot relay is running...")
app.run()
