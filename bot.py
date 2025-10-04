import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ذخیره‌ی موقت بر اساس chat_id
# ساختار: pending[chat_id] = {"file_id": str, "type": "video|document", "orig_msg_id": int}
pending = {}
MAX_CAPTION = 1024

def is_video_message(msg):
    # ویدیو مستقیم
    if msg.video:
        return ("video", msg.video.file_id)
    # بعضی ربات‌ها ویدیو را به صورت document می‌فرستند
    if msg.document and msg.document.mime_type and "video" in msg.document.mime_type:
        return ("document", msg.document.file_id)
    return (None, None)

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # پیام موثر (message یا channel_post) را یک‌جا می‌گیریم
    msg = update.effective_message
    if not msg:
        return

    chat_id = msg.chat.id

    # لاگ حداقلی برای تشخیص نوع ورودی
    try:
        print({
            "chat_id": chat_id,
            "from_bot": bool(msg.from_user.is_bot) if msg.from_user else None,
            "has_video": bool(msg.video),
            "has_document": bool(msg.document),
            "mime": getattr(msg.document, "mime_type", None) if msg.document else None,
            "has_caption": bool(msg.caption),
            "has_text": bool(msg.text),
            "media_group_id": msg.media_group_id,
            "sender_chat_id": getattr(msg.sender_chat, "id", None),
            "message_id": msg.message_id,
        })
    except Exception:
        pass

    # اگر پیام، ویدیو/ویدیو-داکیومنت داشت، ذخیره کن
    mtype, file_id = is_video_message(msg)
    if file_id:
        # اگر کپشن در همان پیام هست، مستقیم خروجی را بفرست
        if msg.caption:
            caption = msg.caption
            if len(caption) > MAX_CAPTION:
                short_caption = caption[:MAX_CAPTION]
                rest = caption[MAX_CAPTION:]
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=short_caption
                )
                await context.bot.send_message(chat_id=chat_id, text=rest)
            else:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=caption
                )
            # تلاش برای پاک کردن پیام خام (نیازمند admin delete)
            try:
                await msg.delete()
            except:
                pass
            return

        # در غیر این صورت منتظر متن بعدی می‌مانیم
        pending[chat_id] = {
            "file_id": file_id,
            "type": mtype,
            "orig_msg_id": msg.message_id,
        }
        return

    # اگر متن رسید و قبلاً ویدیو ذخیره شده بود → ارسال و پاکسازی
    if msg.text and chat_id in pending:
        file_id = pending[chat_id]["file_id"]
        orig_msg_id = pending[chat_id]["orig_msg_id"]
        caption = msg.text
        # ارسال
        if len(caption) > MAX_CAPTION:
            short_caption = caption[:MAX_CAPTION]
            rest = caption[MAX_CAPTION:]
            await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=short_caption
            )
            await context.bot.send_message(chat_id=chat_id, text=rest)
        else:
            await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption
            )

        # پاکسازی
        pending.pop(chat_id, None)
        # پاک کردن پیام‌های خام (ویدیو اولیه + متن اولیه)
        try:
            # حذف پیام ویدیو اولیه
            await context.bot.delete_message(chat_id=chat_id, message_id=orig_msg_id)
        except:
            pass
        try:
            await msg.delete()
        except:
            pass

# همه‌ی پیام‌ها را می‌گیریم (message + channel_post)
app.add_handler(MessageHandler(filters.ALL, handler))

print("🤖 Bot is running on Railway...")

# اجرای وبهوک با allowed_updates کامل
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    # مطمئن شو آپدیت‌های مرتبط به دست بات برسند
    allowed_updates=[
        "message",
        "channel_post",
        "edited_message",
        "edited_channel_post",
    ],
)
