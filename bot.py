import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# متغیرهای محیطی
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# ساخت اپلیکیشن
app = ApplicationBuilder().token(BOT_TOKEN).build()

# حافظه‌ی موقت برای ویدیو
pending_videos = {}
MAX_CAPTION = 1024

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_videos
    chat_id = update.effective_chat.id

    # پیام می‌تونه از message یا channel_post بیاد
    msg = update.message or update.channel_post
    if not msg:
        return

    # اگر ویدیو بود → ذخیره کن
    if msg.video:
        pending_videos[chat_id] = msg
        return

    # اگر متن بود و قبلاً ویدیو ذخیره شده
    if msg.text and chat_id in pending_videos:
        video_msg = pending_videos.pop(chat_id)
        caption = msg.text

        try:
            if len(caption) > MAX_CAPTION:
                short_caption = caption[:MAX_CAPTION]
                rest = caption[MAX_CAPTION:]

                # ارسال ویدیو با کپشن کوتاه
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_msg.video.file_id,
                    caption=short_caption
                )
                # بقیه متن جدا
                await context.bot.send_message(chat_id=chat_id, text=rest)
            else:
                # کپشن کوتاه → مستقیم روی ویدیو
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_msg.video.file_id,
                    caption=caption
                )
        finally:
            # پاک کردن پیام‌های خام
            try:
                await video_msg.delete()
            except:
                pass
            try:
                await msg.delete()
            except:
                pass

# اضافه کردن هندلر
app.add_handler(MessageHandler(filters.ALL, handler))

print("🤖 Bot is running on Railway...")

# اجرای وبهوک
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
