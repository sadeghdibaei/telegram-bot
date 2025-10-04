import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = ApplicationBuilder().token(BOT_TOKEN).build()

pending = {}
MAX_CAPTION = 1024
PENDING_TTL = 180.0  # ثانیه

def is_video_like(msg):
    if msg.video:
        return msg.video.file_id
    if msg.document and msg.document.mime_type and "video" in msg.document.mime_type:
        return msg.document.file_id
    return None

async def send_video_with_caption(bot, chat_id, file_id, caption):
    if len(caption) > MAX_CAPTION:
        short_caption = caption[:MAX_CAPTION]
        rest = caption[MAX_CAPTION:]
        await bot.send_video(chat_id=chat_id, video=file_id, caption=short_caption)
        await bot.send_message(chat_id=chat_id, text=rest)
    else:
        await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat_id = msg.chat.id

    # اگر ویدیو یا داکیومنت ویدیویی بود
    file_id = is_video_like(msg)
    if file_id:
        if msg.caption:
            await send_video_with_caption(context.bot, chat_id, file_id, msg.caption)
            try:
                await msg.delete()
            except:
                pass
            return
        pending[chat_id] = {
            "file_id": file_id,
            "orig_msg_id": msg.message_id,
            "ts": time.time(),
        }
        return

    # اگر متن بود و ویدیو در انتظار داشتیم
    if msg.text and chat_id in pending:
        slot = pending.get(chat_id)
        if not slot or (time.time() - slot["ts"] > PENDING_TTL):
            pending.pop(chat_id, None)
            return

        caption = msg.text
        file_id = slot["file_id"]
        orig_msg_id = slot["orig_msg_id"]

        await send_video_with_caption(context.bot, chat_id, file_id, caption)

        pending.pop(chat_id, None)

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=orig_msg_id)
        except:
            pass
        try:
            await msg.delete()
        except:
            pass

app.add_handler(MessageHandler(filters.ALL, handler))

print("🤖 Bot is running...")

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    allowed_updates=["message", "channel_post", "edited_message", "edited_channel_post"],
)
