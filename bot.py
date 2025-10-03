import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# دیکشنری برای نگه داشتن ویدیوهای در انتظار کپشن
pending_videos = {}

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

async def main():
    token = os.environ["8046432071:AAGHppjd4-bCVnASER4Nx2AcTjXXKsFVim4"]
    webhook_url = os.environ["https://example.com/temp"]

    app = (
        ApplicationBuilder()
        .token(token)
        .build()
    )

    # هندلر اصلی
    app.add_handler(MessageHandler(filters.ALL, handler))

    # راه‌اندازی webhook
    await app.bot.set_webhook(webhook_url)
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path=token,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
