import os
from pyrogram import Client, filters

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]  # با pyrogram genstring می‌سازی

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# هر پیامی که از @iDownloadersBot توی گروه بیاد
@app.on_message(filters.chat("iDownloadersBot"))
async def relay_and_delete(client, message):
    try:
        chat_id = message.chat.id

        # فوروارد پیام به همون گروه
        await message.forward(chat_id)

        # حذف پیام اصلی @iDownloadersBot
        await message.delete()

        print(f"✅ Forwarded & deleted message {message.id} in chat {chat_id}")

    except Exception as e:
        print("❌ Error:", e)

print("👤 Userbot relay is running...")
app.run()
