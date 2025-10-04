import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from typing import Dict

# متغیرهای محیطی
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# ساخت اپلیکیشن
app = ApplicationBuilder().token(BOT_TOKEN).build()

# حافظه‌ی موقت برای ویدیو
pending_videos: Dict[int, Update] = {}
MAX_CAPTION = 1024

def extract_instagram_url(text: str) -> str | None:
    """پیدا کردن اولین لینک اینستاگرام داخل متن"""
    if not text:
        return None
    match = re.search(r"(https?://(?:www\.)?instagram\.com/\S+)", text)
    return match.group(1) if match else None

async def handle_video_and_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.message or update.channel_post
    if not msg:
        return

    # ذخیره‌ی ویدیو
    if msg.video:
        pending_videos[chat_id] = msg
        return

    # پردازش کپشن
    if msg.text and chat_id in pending_videos:
        video_msg = pending_videos.pop(chat_id)
        caption = msg.text

        try:
            # کوتاه‌سازی کپشن در صورت نیاز
            if len(caption) > MAX_CAPTION:
                caption = caption[:MAX_CAPTION - 3] + "..."

            # پیدا کردن لینک اینستاگرام
            instagram_url = extract_instagram_url(msg.text)

            # ساخت دکمه اگر لینک وجود داشت
            reply_markup = None
            if instagram_url:
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("مشاهده در اینستاگرام", url=instagram_url)]
                ])

            # ارسال ویدیو + کپشن + دکمه (اگر بود)
            await context.bot.send_video(
                chat_id,
                video=video_msg.video.file_id,
                caption=caption,
                reply_markup=reply_markup
            )

        finally:
            # پاک کردن پیام‌های اولیه
            for m in [video_msg, msg]:
                try:
                    await m.delete()
                except:
                    pass

# اضافه کردن هندلر
app.add_handler(MessageHandler(filters.ALL, handle_video_and_caption))

print("🤖 Bot is running on Railway...")

# اجرای وبهوک
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
