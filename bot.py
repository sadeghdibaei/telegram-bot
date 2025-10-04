import os
from telegram import Update
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
            if len(caption) > MAX_CAPTION:
                short_caption = caption[:MAX_CAPTION]
                rest = caption[MAX_CAPTION:]

                await context.bot.send_video(chat_id, video=video_msg.video.file_id, caption=short_caption)
                await context.bot.send_message(chat_id, text=rest)
            else:
                await context.bot.send_video(chat_id, video=video_msg.video.file_id, caption=caption)
        finally:
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
