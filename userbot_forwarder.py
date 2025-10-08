import os
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

app = Client("userbot_test", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# هندلر: وقتی توی گروه لینک اینستاگرام فرستاده شد
@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    if "instagram.com" in message.text.lower():
        try:
            # ارسال لینک به بات
            await client.send_message("iDownloadersBot", message.text)
            print("📤 Sent link to iDownloadersBot")

            # حذف پیام اصلی از گروه
            await message.delete()
            print("🗑️ Deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

# هندلر: وقتی بات جواب داد
@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        # ارسال پاسخ بات به آخرین گروهی که لینک ازش اومده
        # اینجا فرض می‌گیریم فقط یه گروه فعاله و پیام رو به اون می‌فرستیم
        # اگه چند گروه داری، باید یه سیستم نگهداری context اضافه کنیم

        TARGET_GROUP_ID = -1003183210016  # 🔧 جایگزین کن با chat_id گروه تستت

        if message.media:
            await client.copy_message(TARGET_GROUP_ID, message.chat.id, message.id)
            print("📥 Forwarded media to group")
        elif message.text:
            await client.send_message(TARGET_GROUP_ID, message.text)
            print("📥 Forwarded text to group")

    except Exception as e:
        print("❌ Error forwarding bot response:", e)

print("🧪 Userbot test relay is running...")
app.run()
