import os
import asyncio
from typing import Dict, Optional
from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Env vars
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# App
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Config
EXTRA_LINK_BLOCK = 60   # فضای رزرو برای لینک
MAX_CAPTION = 1024 - EXTRA_LINK_BLOCK
SINGLE_DEBOUNCE_SECS = 3
GROUP_DEBOUNCE_SECS = 2

# State
pending_single: Dict[int, Dict] = {}
pending_groups: Dict[str, Dict] = {}
last_group_by_chat: Dict[int, str] = {}

def shorten_caption(text: Optional[str], limit: int) -> str:
    if not text:
        return ""
    return text[:limit - 3] + "..." if len(text) > limit else text

def build_caption(base_caption: str, url: Optional[str]) -> str:
    caption = shorten_caption(base_caption, MAX_CAPTION)
    if url:
        caption += f"\n\n<a href=\"{url}\">O P E N P O S T ⎋</a>"
    return caption

def extract_button_url(msg) -> Optional[str]:
    if not msg or not msg.reply_markup or not msg.reply_markup.inline_keyboard:
        return None
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if getattr(btn, "url", None):
                return btn.url
    return None

async def flush_single(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_single.pop(chat_id, None)
    if not data:
        return

    caption = build_caption(data.get("caption") or "", data.get("button_url"))
    try:
        if data["type"] == "photo":
            await context.bot.send_photo(chat_id, photo=data["file_id"], caption=caption, parse_mode="HTML")
        else:
            await context.bot.send_video(chat_id, video=data["file_id"], caption=caption, parse_mode="HTML")
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
            except:
                pass

async def flush_group(group_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_groups.pop(group_id, None)
    if not data:
        return

    caption = build_caption(data.get("caption") or "", data.get("button_url"))
    if data["media"]:
        data["media"][0].caption = caption
        data["media"][0].parse_mode = "HTML"

    try:
        await context.bot.send_media_group(chat_id, media=data["media"])
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
            except:
                pass

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg:
        return

    chat_id = msg.chat_id
    button_url_in = extract_button_url(msg)

    # آلبوم
    if msg.media_group_id:
        group_id = f"group_{msg.media_group_id}"
        grp = pending_groups.get(group_id)
        if not grp:
            grp = pending_groups[group_id] = {
                "media": [],
                "caption": None,
                "button_url": None,
                "raw_msgs": [],
                "timer": None,
                "chat_id": chat_id,
            }
        grp["raw_msgs"].append(msg)

        if msg.photo:
            grp["media"].append(InputMediaPhoto(msg.photo[-1].file_id))
        elif msg.video:
            grp["media"].append(InputMediaVideo(msg.video.file_id))

        if msg.caption and not grp["caption"]:
            grp["caption"] = msg.caption

        if button_url_in and not grp["button_url"]:
            grp["button_url"] = button_url_in

        last_group_by_chat[chat_id] = group_id

        if grp["timer"]:
            grp["timer"].cancel()
        grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
        return

    # تک‌مدیا
    if msg.photo or msg.video:
        if chat_id in pending_single:
            t = pending_single[chat_id].get("timer")
            if t:
                t.cancel()
            await flush_single(chat_id, context)

        pending_single[chat_id] = {
            "file_id": msg.photo[-1].file_id if msg.photo else msg.video.file_id,
            "type": "photo" if msg.photo else "video",
            "caption": msg.caption or None,
            "button_url": button_url_in or None,
            "raw_msgs": [msg],
            "timer": None,
        }

        t = asyncio.create_task(single_timer_task(chat_id, context))
        pending_single[chat_id]["timer"] = t
        return

    # کپشن جدا
    if msg.text:
        text = msg.text

        if chat_id in pending_single:
            data = pending_single[chat_id]
            t = data.get("timer")
            if t:
                t.cancel()
            if text:
                data["caption"] = text
            if button_url_in and not data["button_url"]:
                data["button_url"] = button_url_in
            data["raw_msgs"].append(msg)
            await flush_single(chat_id, context)
            return

        group_id = last_group_by_chat.get(chat_id)
        if group_id and group_id in pending_groups:
            grp = pending_groups[group_id]
            grp["caption"] = text
            if button_url_in and not grp["button_url"]:
                grp["button_url"] = button_url_in
            grp["raw_msgs"].append(msg)
            if grp["timer"]:
                grp["timer"].cancel()
            grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
            return

async def single_timer_task(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        await asyncio.sleep(SINGLE_DEBOUNCE_SECS)
    except asyncio.CancelledError:
        return
    await flush_single(chat_id, context)

async def group_timer_task(group_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        await asyncio.sleep(GROUP_DEBOUNCE_SECS)
    except asyncio.CancelledError:
        return
    await flush_group(group_id, chat_id, context)
    if last_group_by_chat.get(chat_id) == group_id:
        last_group_by_chat.pop(chat_id, None)

# Handler
app.add_handler(MessageHandler(filters.ALL, handle))

print("🤖 Bot is running on Railway...")

# Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
)
