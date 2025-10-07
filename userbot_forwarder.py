import os
import asyncio
from collections import defaultdict
from pyrogram import Client
from pyrogram.types import InputMediaPhoto, InputMediaVideo

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# بافر برای هر چت
pending = defaultdict(lambda: {"album": [], "caption": None, "raw_msgs": [], "timer": None})

async def flush_buffer(client, chat_id):
    data = pending.get(chat_id)
    if not data:
        return

    album = data["album"]
    caption = data["caption"]
    raw_msgs = data["raw_msgs"]

    try:
        # اول آلبوم
        if album:
            media = []
            for m in album:
                if m.photo:
                    media.append(InputMediaPhoto(m.photo.file_id))
                elif m.video:
                    media.append(InputMediaVideo(m.video.file_id))
            await client.send_media_group(chat_id, media)
            print(f"✅ Sent album with {len(album)} items")

        # بعد کپشن
        if caption:
            await client.forward_messages(chat_id, chat_id, caption.id)
            print("✅ Forwarded caption")

    except Exception as e:
        print("❌ Flush error:", e)

    # پاک کردن پیام‌های خام
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
    # اگر بعد از ۳۰ ثانیه هنوز flush نشده، هرچی هست رو بفرست
    await flush_buffer(client, chat_id)


@app.on_message()
async def relay_and_buffer(client, message):
    try:
        sender = message.from_user.username if message.from_user else None
        if sender != "iDownloadersBot":
            return

        chat_id = message.chat.id
        data = pending[chat_id]

        # ذخیره پیام خام
        data["raw_msgs"].append(message)

        # مدیا
        if message.media_group_id or message.photo or message.video:
            data["album"].append(message)

        # کپشن
        elif message.text:
            data["caption"] = message

        # اگر هم آلبوم و هم کپشن داریم → فوری flush
        if data["album"] and data["caption"]:
            await flush_buffer(client, chat_id)

        # اگر تایمر فعال نیست → بذار
        elif not data["timer"]:
            data["timer"] = asyncio.create_task(wait_and_flush(client, chat_id))

    except Exception as e:
        print("❌ Handler error:", e)

from pyrogram import filters

@app.on_message(filters.text)
async def forward_instagram_links(client, message):
    if "instagram.com" in message.text.lower():
        try:
            await client.send_message("iDownloadersBot", message.text)
            print(f"📤 Sent Instagram link from {message.chat.id} to iDownloadersBot")

            # حذف پیام اصلی
            await asyncio.sleep(1)  # یه تأخیر کوچیک برای اطمینان
            await message.delete()
            print("🗑️ Original message deleted")

        except Exception as e:
            print("❌ Failed to forward/delete:", e)

print("👤 Userbot relay with smart buffer is running...")
app.run()
