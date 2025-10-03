import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = Flask(__name__)

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

telegram_app.add_handler(MessageHandler(filters.VIDEO & filters.Caption(True), handle_message))

# وبهوک برای دریافت آپدیت‌ها
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

# روت تست ساده
@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
