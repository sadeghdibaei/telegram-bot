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

# هندلر اصلی: ویدیو + کپشن
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending_videos
    chat_id = update.effective_chat.id

    # اگر پیام ویدیو بود → ذخیره کن
    if update.message and update.message.video:
        pending_videos[chat_id] = update.message
        return

    # اگر پیام متن بود و قبلاً ویدیو ذخیره شده
    if update.message and update.message.text and chat_id in pending_videos:
        video_msg = pending_videos.pop(chat_id)
        caption = update.message.text

        # ارسال ویدیو با کپشن
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=video_msg.chat_id,
            message_id=video_msg.message_id,
            caption=caption
        )

        # پاک کردن پیام‌های خام (ویدیو + کپشن)
        try:
            await video_msg.delete()
            await update.message.delete()
        except:
            pass

# هندلر تستی: هر پیامی بیاد → جواب بده
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("✅ پیام رسید (Webhook کار می‌کنه)")

# اضافه کردن هندلرها
app.add_handler(MessageHandler(filters.ALL, handler))
app.add_handler(MessageHandler(filters.ALL, echo))

print("🤖 بات روی Railway روشن شد...")

# اجرای وبهوک
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
