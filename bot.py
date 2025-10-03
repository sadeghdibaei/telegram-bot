import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, MessageHandler, filters, CallbackContext

# گرفتن مقادیر از Environment Variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# Dispatcher برای مدیریت پیام‌ها
dispatcher = Dispatcher(bot, None, workers=0)

# هندلر برای پیام‌های ویدیو + کپشن
def handle_message(update: Update, context: CallbackContext):
    if update.message and update.message.video and update.message.caption:
        # فقط ویدیو + کپشن رو نگه می‌داریم
        chat_id = update.message.chat_id
        video = update.message.video.file_id
        caption = update.message.caption

        # پاک کردن پیام اصلی
        context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

        # ارسال خروجی نهایی
        context.bot.send_video(chat_id=chat_id, video=video, caption=caption)

dispatcher.add_handler(MessageHandler(filters.VIDEO & filters.Caption(True), handle_message))

# وبهوک برای دریافت آپدیت‌ها
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# روت تست ساده
@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    # ست کردن وبهوک
    bot.delete_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
