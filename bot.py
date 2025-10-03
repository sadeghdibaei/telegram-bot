import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# ساخت اپلیکیشن تلگرام
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# هندلر برای ویدیو + کپشن
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.video and update.message.caption:
        chat_id = update.message.chat_id
        video = update.message.video.file_id
        caption = update.message.caption

        # پاک کردن پیام اصلی
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

        # ارسال خروجی نهایی
        await context.bot.send_video(chat_id=chat_id, video=video, caption=caption)

# اضافه کردن هندلر
telegram_app.add_handler(MessageHandler(filters.VIDEO, handle_message))

if __name__ == "__main__":
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
