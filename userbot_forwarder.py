import os
import asyncio
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo

print("🚀 شروع اجرای یوزربات...")

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# بافر برای گروه مقصد
pending = defaultdict(lambda: {"album": [], "caption": None, "raw_msgs": [], "timer": None})

async def flush_buffer(client, chat_id):
    data = pending.get(chat_id)
    if not data:
        print("⚠️ بافر خالیه، ارسال انجام نشد")
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
            if media:
                await client.send_media_group(chat_id, media)
                print(f"✅ آلبوم ارسال شد با {len(media)} آیتم")
            else:
                print("⚠️ هیچ مدیای معتبری برای ارسال نبود")

        # ارسال کپشن (فوروارد)
        if caption:
            await client.forward_messages(chat_id, caption.chat.id, caption.id)
            print("✅ کپشن فوروارد شد")

    except Exception as e:
        print(f"❌ خطا در flush_buffer: {type(e).__name__} - {e}")
        return  # بافر رو پاک نکن

    # حذف پیام‌های خام
    await asyncio.sleep(1)
    for m in raw_msgs:
        try:
            await m.delete()
        except:
            pass

    # ریست بافر
    pending.pop(chat_id, None)
    print("🔄 بافر ریست شد")

async def wait_and_flush(client, chat_id, delay=30):
    await asyncio.sleep(delay)
    await flush_buffer(client, chat_id)

# هندلر تست ارسال به گروه
@app.on_message(filters.command("test", prefixes=["/", "!"]))
async def test_send_to_group(client, message):
    try:
        print(f"🧪 تست ارسال به گروه: {TARGET_GROUP_ID}")
        await client.send_message(TARGET_GROUP_ID, "🧪 تست موفق! یوزربات تونست پیام بفرسته.")
        print("✅ تست ارسال به گروه انجام شد")
    except Exception as e:
        print(f"❌ تست ارسال به گروه شکست خورد: {type(e).__name__} - {e}")

# هندلر گرفتن آیدی گروه برای تشخیص دقیق
@app.on_message(filters.group)
async def log_group_id(client, message):
    print(f"📌 Group ID: {message.chat.id} | Title: {message.chat.title}")

# هندلر تشخیص لینک اینستاگرام
@app.on_message(filters.text)
async def detect_instagram_link(client, message):
    if "instagram.com" in message.text.lower():
        try:
            link = message.text.strip()
            await client.send_message("iDownloadersBot", link)
            print(f"📨 لینک ارسال شد به iDownloadersBot: {link}")
        except Exception as e:
            print(f"❌ خطا در ارسال لینک: {type(e).__name__} - {e}")

# هندلر دریافت پاسخ از iDownloadersBot
@app.on_message()
async def relay_and_buffer(client, message):
    try:
        if not message.from_user or message.from_user.username != "iDownloadersBot":
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
        print(f"❌ خطا در relay_and_buffer: {type(e).__name__} - {e}")

print("👤 یوزربات آماده‌ست و منتظر لینک‌های اینستاگرام...")
app.run()
