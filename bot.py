import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = ApplicationBuilder().token(BOT_TOKEN).build()

# وقتی ویدیو میاد → ذخیره کن برای استفاده بعدی
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.video:
        context.user_data["pending_video"] = {
            "file_id": update.message.video.file_id,
            "msg_id": update.message.message_id,
            "chat_id": update.message.chat_id,
        }

# وقتی متن (کپشن اصلی) میاد → ویدیو قبلی رو با این کپشن دوباره بفرست
async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    pending = context.user_data.get("pending_video")
    if not pending:
        return  # اگه ویدیو ذخیره نشده بود، کاری نکن

    chat_id = pending["chat_id"]
    video_id = pending["file_id"]
    video_msg_id = pending["msg_id"]
    caption_msg_id = update.message.message_id

    # پاک کردن پیام‌های خام
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=video_msg_id)
    except Exception:
        pass
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=caption_msg_id)
    except Exception:
        pass

    # ارسال ویدیو با کپشن اصلی
    await context.bot.send_video(chat_id=chat_id, video=video_id, caption=update.message.text)

    # پاک کردن بافر
    context.user_data.pop("pending_video", None)

# هندلرها
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption))

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
