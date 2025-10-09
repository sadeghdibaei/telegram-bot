import re
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client

# وضعیت مرحله‌ی آپلود
upload_state = {}

async def handle_cdn_link(client: Client, message: Message):
    # مرحله ۱: استخراج لینک از دکمه‌ی شیشه‌ای
    if message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url and "cdninstagram.com" in btn.url:
                    cdn_link = btn.url
                    chat_id = message.chat.id
                    upload_state[chat_id] = {"step": "waiting"}
                    await client.send_message("urluploadxbot", cdn_link)
                    print("📤 Sent CDN link to @urluploadxbot")
                    return

    # مرحله ۲: انتخاب گزینه‌ی دیفالت
    if "rename" in message.text.lower() and message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for i, btn in enumerate(row):
                if "default" in btn.text.lower():
                    await message.click(i)
                    print(f"✅ Clicked 'Default' button: {btn.text}")
                    for group_id in upload_state:
                        upload_state[group_id]["step"] = "processing"
                    return

    # مرحله ۳: دریافت ویدیو
    if message.video and message.chat.id in upload_state:
        print("📥 Final video received from @urluploadxbot")
        upload_state.pop(message.chat.id, None)
        return message.video.file_id

    # مرحله ۴: رد کردن پیام‌های غیرمفید
    if message.photo or "۴ دقیقه" in message.text:
        print("⏭ Skipped non-video message from @urluploadxbot")
        return
