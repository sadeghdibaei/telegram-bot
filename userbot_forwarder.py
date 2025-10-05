import os
from pyrogram import Client, filters

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
BOT_USERNAME = os.environ["BOT_USERNAME"]  # مثلا "YourBotName" بدون @

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# پیام‌های iDownloadersBot
@app.on_message(filters.chat("iDownloadersBot"))
async def relay(client, message):
    try:
        # اگر آلبوم است، تلگرام خود media_group_id را نگه می‌دارد موقع فوروارد
        await message.forward(BOT_USERNAME)
    except Exception as e:
        print("Forward error:", e)

print("👤 Userbot relay is running...")
app.run()
