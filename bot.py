import os
from typing import Optional
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ذخیره کپشن و پیام برای اعمال روی ویدیوی بعدی
async def capture_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.from_user.is_bot:
        return

    # کپشن دریافت و ذخیره می‌شود
    context.user_data["pending_caption"] = msg.text
    context.user_data["pending_caption_msg_id"] = msg.message_id

    # پاک‌سازی مینیمال: پیام کپشن ورودی را پاک نکن تا اگر ویدیو نیاید، چیزی از بین نرود
    # اگر می‌خواهی فوراً پاک شود، این خط را باز کن:
    # await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.from_user.is_bot:
        return

    # فقط روی ویدیو کار کن
    if not msg.video:
        return

    # کپشن نهایی: یا کپشن خود ویدیو، یا کپشن ذخیره‌شده از پیام قبلی
    pending_caption: Optional[str] = context.user_data.get("pending_caption")
    final_caption = msg.caption if msg.caption else pending_caption

    # پاک کردن ورودی‌ها (ویدیوِ خام و اگر کپشن ذخیره‌شده داشتیم، خودش هم)
    await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
    pending_caption_msg_id = context.user_data.get("pending_caption_msg_id")
    if pending_caption and pending_caption_msg_id:
        try:
            await context.bot.delete_message(chat_id=msg.chat_id, message_id=pending_caption_msg_id)
        except Exception:
            pass  # اگر پیام کپشن قبلی موجود نبود، نادیده بگیر

    # ارسال خروجی نهایی (ویدیو با کپشن نهایی)
    await context.bot.send_video(chat_id=msg.chat_id, video=msg.video.file_id, caption=final_caption or "")

    # پاک کردن بافر کپشن بعد از استفاده
    context.user_data.pop("pending_caption", None)
    context.user_data.pop("pending_caption_msg_id", None)

# فیلترها:
# - متن (به‌جز کامندها) برای ذخیره‌ی کپشن احتمالی
# - ویدیو برای پردازش نهایی
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_caption))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )
