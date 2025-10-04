import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from typing import Dict, List

# متغیرهای محیطی
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# ساخت اپلیکیشن
app = ApplicationBuilder().token(BOT_TOKEN).build()

# حافظه‌ی موقت برای مدیا
pending_media: Dict[int, Dict] = {}
MAX_CAPTION = 1024

def shorten_caption(caption: str) -> str:
    if not caption:
        return ""
    if len(caption) > MAX_CAPTION:
        return caption[:MAX_CAPTION - 3] + "..."
    return caption

async def handle_media_and_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.message or update.channel_post
    if not msg:
        return

    # اگر آلبوم (media group) بود
    if msg.media_group_id:
        group_id = msg.media_group_id
        if group_id not in pending_media:
            pending_media[group_id] = {"media": [], "caption": None, "button_url": None}

        # ذخیره مدیا
        if msg.photo:
            pending_media[group_id]["media"].append(
                InputMediaPhoto(msg.photo[-1].file_id)
            )
        elif msg.video:
            pending_media[group_id]["media"].append(
                InputMediaVideo(msg.video.file_id)
            )

        # ذخیره کپشن (اگر وجود داشت)
        if msg.caption:
            pending_media[group_id]["caption"] = shorten_caption(msg.caption)

        # ذخیره دکمه (اگر وجود داشت)
        if msg.reply_markup and msg.reply_markup.inline_keyboard:
            for row in msg.reply_markup.inline_keyboard:
                for button in row:
                    if button.url:
                        pending_media[group_id]["button_url"] = button.url
                        break

        # وقتی آخرین مدیا رسید → ارسال
        if len(pending_media[group_id]["media"]) >= 2:  # فرض: آلبوم حداقل 2 مدیا
            data = pending_media.pop(group_id)
            reply_markup = None
            if data["button_url"]:
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("مشاهده در اینستاگرام", url=data["button_url"])]
                ])
            await context.bot.send_media_group(
                chat_id,
                media=data["media"]
            )
            if data["caption"]:
                await context.bot.send_message(chat_id, text=data["caption"], reply_markup=reply_markup)
        return

    # اگر تک‌مدیا بود (عکس یا ویدیو)
    if msg.photo or msg.video:
        pending_media[chat_id] = {
            "file_id": msg.photo[-1].file_id if msg.photo else msg.video.file_id,
            "type": "photo" if msg.photo else "video",
            "caption": msg.caption if msg.caption else None,
            "button_url": None,
        }

        # ذخیره دکمه (اگر وجود داشت)
        if msg.reply_markup and msg.reply_markup.inline_keyboard:
            for row in msg.reply_markup.inline_keyboard:
                for button in row:
                    if button.url:
                        pending_media[chat_id]["button_url"] = button.url
                        break
        return

    # اگر کپشن جدا اومد
    if msg.text and chat_id in pending_media:
        media = pending_media.pop(chat_id)
        caption = shorten_caption(msg.text or media["caption"])

        reply_markup = None
        if media["button_url"]:
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("مشاهده در اینستاگرام", url=media["button_url"])]
            ])

        if media["type"] == "photo":
            await context.bot.send_photo(chat_id, photo=media["file_id"], caption=caption, reply_markup=reply_markup)
        elif media["type"] == "video":
            await context.bot.send_video(chat_id, video=media["file_id"], caption=caption, reply_markup=reply_markup)

# اضافه کردن هندلر
app.add_handler(MessageHandler(filters.ALL, handle_media_and_caption))

print("🤖 Bot is running on Railway...")

# اجرای وبهوک
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
