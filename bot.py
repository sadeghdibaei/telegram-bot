import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = ApplicationBuilder().token(BOT_TOKEN).build()

# فقط نگه‌داری موقت به ازای هر گروه؛ بدون حذف پیام
# pending[chat_id] = {"file_id": str, "ts": float}
pending = {}
MAX_CAPTION = 1024
TTL = 180.0  # زمان انتظار برای رسیدن متن بعد از ویدیو

def is_video_like(msg):
    if msg.video:
        return msg.video.file_id
    if msg.document and msg.document.mime_type and "video" in msg.document.mime_type:
        return msg.document.file_id
    return None

async def send_video(bot, chat_id, file_id, caption):
    if caption and len(caption) > MAX_CAPTION:
        await bot.send_video(chat_id=chat_id, video=file_id, caption=caption[:MAX_CAPTION])
        await bot.send_message(chat_id=chat_id, text=caption[MAX_CAPTION:])
    else:
        await bot.send_video(chat_id=chat_id, video=file_id, caption=caption or "")

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat = msg.chat
    chat_id = chat.id
    chat_type = chat.type  # "private", "group", "supergroup", "channel"

    # فقط گروه‌ها؛ چت خصوصی رو دست نمی‌زنیم تا رفتار قبلی خراب نشه
    if chat_type not in ("group", "supergroup"):
        return

    # آلبوم‌ها فعلاً نادیده گرفته می‌شن تا بعد جداگانه هندل کنیم
    if msg.media_group_id:
        return

    file_id = is_video_like(msg)

    # سناریو 1: ویدیو با کپشن در همان پیام → مستقیم نسخه نهایی را ارسال کن
    if file_id and msg.caption:
        await send_video(context.bot, chat_id, file_id, msg.caption)
        return

    # سناریو 2: ویدیو بدون کپشن → منتظر متن بعدی بمان
    if file_id and not msg.caption:
        pending[chat_id] = {"file_id": file_id, "ts": time.time()}
        return

    # سناریو 3: متن رسید و قبلاً ویدیو منتظر بود → ترکیب و ارسال
    if msg.text and chat_id in pending:
        slot = pending.get(chat_id)
        if not slot or (time.time() - slot["ts"] > TTL):
            pending.pop(chat_id, None)
            return

        caption = msg.text
        await send_video(context.bot, chat_id, slot["file_id"], caption)
        pending.pop(chat_id, None)

# فقط message و channel_post را بگیر؛ ادیت‌ها فعلاً لازم نیست
app.add_handler(MessageHandler(filters.ALL, handler))

print("🤖 Bot is running (group-safe minimal).")

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    allowed_updates=["message", "channel_post"],
)
