import os
from pyrogram import Client, filters

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@app.on_message()
async def debug_all(client, message):
    try:
        sender = message.from_user.username if message.from_user else None
        chat_title = message.chat.title if message.chat else None
        print(f"📩 New message in chat={chat_title} ({message.chat.id}) "
              f"from={sender} (id={message.from_user.id if message.from_user else 'N/A'}) "
              f"type={'media' if message.media else 'text'}")

        # فقط وقتی فرستنده iDownloadersBot باشه
        if sender == "iDownloadersBot":
            chat_id = message.chat.id

            # فوروارد پیام به همون گروه
            fwd = await message.forward(chat_id)
            print(f"✅ Forwarded message {message.id} -> new id {fwd.id}")

            # حذف پیام اصلی
            try:
                await message.delete()
                print(f"🗑 Deleted original message {message.id}")
            except Exception as e:
                print(f"⚠️ Could not delete original: {e}")

    except Exception as e:
        print("❌ Handler error:", e)

print("👤 Userbot relay is running...")
app.run()
