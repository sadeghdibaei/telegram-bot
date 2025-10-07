import os
import asyncio
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# آیدی عددی گروهی که بات اصلی اونجاست
TARGET_GROUP_ID = -1001234567890

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# هندلر چاپ آیدی گروه
@app.on_message(filters.group)
async def print_group_info(client, message):
    print(f"📌 Group ID: {message.chat.id} | Title: {message.chat.title}")

# هندلر تست ارسال پیام
@app.on_message(filters.command("test", prefixes=["/", "!"]))
async def test_send(client, message):
    await client.send_message(TARGET_GROUP_ID, "🧪 تست ارسال به گروه")
    print("✅ پیام تست ارسال شد")

# هندلر تشخیص لینک اینستاگرام
@app.on_message(filters.text)
async def detect_instagram_link(client, message):
    ...

# هندلر دریافت پاسخ از iDownloadersBot
@app.on_message()
async def relay_and_buffer(client, message):
    ...
    
# بافر برای گروه مقصد
pending = defaultdict(lambda: {"album": [], "caption": None, "raw_msgs": [], "timer": None})

async def flush_buffer(client, chat_id):
    data = pending.get(chat_id)
    if not data:
        return

    album = data["album"]
    caption = data["caption"]
    raw_msgs = data["raw_msgs"]

    try:
        # ارسال آلبوم
        if album:
            media = []
            for m in album:
                if m.photo:
                    media.append(InputMediaPhoto(m.photo.file_id))
                elif m.video:
                    media.append(InputMediaVideo(m.video.file_id))
            await client.send_media_group(chat_id, media)
            print(f"✅ Sent album with {len(album)} items")

        # ارسال کپشن (فوروارد)
        if caption:
            await client.forward_messages(chat_id, caption.chat.id, caption.id)
            print("✅ Forwarded caption")

    except Exception as e:
        print("❌ Flush error:", e)

    # حذف پیام‌های خام
    await asyncio.sleep(1)
    for m in raw_msgs:
        try:
            await m.delete()
        except:
            pass

    # ریست بافر
    pending.pop(chat_id, None)

async def wait_and_flush(client, chat_id, delay=30):
    await asyncio.sleep(delay)
    await flush_buffer(client, chat_id)

# تشخیص لینک اینستاگرام از هر چت
@app.on_message(filters.text)
async def detect_instagram_link(client, message):
    if "instagram.com" in message.text.lower():
        try:
            link = message.text.strip()
            await client.send_message("iDownloadersBot", link)
            print(f"📨 Sent link to iDownloadersBot: {link}")
        except Exception as e:
            print("❌ Error sending link to iDownloadersBot:", e)

# دریافت پاسخ از iDownloadersBot و ارسال به گروه مقصد
@app.on_message()
async def relay_and_buffer(client, message):
    try:
        sender = message.from_user.username if message.from_user else None
        if sender != "iDownloadersBot":
            return

        chat_id = TARGET_GROUP_ID
        data = pending[chat_id]

        data["raw_msgs"].append(message)

        if message.media_group_id or message.photo or message.video:
            data["album"].append(message)
        elif message.text:
            data["caption"] = message

        if data["album"] and data["caption"]:
            await flush_buffer(client, chat_id)
        elif not data["timer"]:
            data["timer"] = asyncio.create_task(wait_and_flush(client, chat_id))

    except Exception as e:
        print("❌ Handler error:", e)

print("👤 Userbot with Instagram relay is running...")
app.run()
