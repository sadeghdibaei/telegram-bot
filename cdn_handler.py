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
            
                # حذف پیام قبلی Processing...⏳ اگر وجود داشت
                old_msg_id = upload_state.get(chat_id, {}).get("processing_msg_id")
                if old_msg_id:
                    await client.delete_messages(chat_id, old_msg_id)
            
                # ارسال پیام مخصوص پست‌های حجیم
                cdn_notice = await client.send_message(
                    chat_id,
                    "⏳ Large post detected. Processing via alternate CDN route..."
                )
            
                # ذخیره وضعیت
                upload_state[chat_id] = {
                    "step": "waiting",
                    "cdn_notice_id": cdn_notice.id
                }
            
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
    chat_id = message.chat.id
    print("📥 Final video received from @urluploadxbot")

    # حذف پیام اطلاع‌رسانی موقت
    cdn_notice_id = upload_state[chat_id].get("cdn_notice_id")
    if cdn_notice_id:
        await client.delete_messages(chat_id, cdn_notice_id)

    processing_msg_id = upload_state[chat_id].get("processing_msg_id")
    if processing_msg_id:
        await client.delete_messages(chat_id, processing_msg_id)

    upload_state.pop(chat_id, None)
    return message.video.file_id

    # مرحله ۴: رد کردن پیام‌های غیرمفید
    if message.photo or "۴ دقیقه" in message.text:
        print("⏭ Skipped non-video message from @urluploadxbot")
        return

    chat_id = message.chat.id
    cdn_notice_id = upload_state.get(chat_id, {}).get("cdn_notice_id")
    if cdn_notice_id:
        await client.delete_messages(chat_id, cdn_notice_id)
    
    processing_msg_id = upload_state.get(chat_id, {}).get("processing_msg_id")
    if processing_msg_id:
        await client.delete_messages(chat_id, processing_msg_id)
    
    await client.send_message(chat_id, "❌ Failed to process the post. Please try again.")
    upload_state.pop(chat_id, None)
