import os
import asyncio
import logging
import re
from typing import Dict, Optional
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("relay-bot")

# Env
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# App
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Config
EXTRA_LINK_BLOCK = 60
MAX_CAPTION = 1024 - EXTRA_LINK_BLOCK
SINGLE_DEBOUNCE_SECS = 3
GROUP_DEBOUNCE_SECS = 2

# State
pending_single: Dict[int, Dict] = {}
pending_groups: Dict[str, Dict] = {}
last_group_by_chat: Dict[int, str] = {}

URL_REGEX = re.compile(r"(https?://\S+)")

def shorten_caption(text: Optional[str], limit: int) -> str:
    if not text:
        return ""
    return text[:limit - 3] + "..." if len(text) > limit else text

def extract_url(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = URL_REGEX.search(text)
    return m.group(1) if m else None

def build_caption(base_caption: str, url: Optional[str]) -> str:
    caption = shorten_caption(base_caption, MAX_CAPTION)
    if url:
        caption += f"\n\n<a href=\"{url}\">O P E N P O S T ⎋</a>"
    return caption

async def flush_single(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_single.pop(chat_id, None)
    if not data:
        return
    caption = build_caption(data.get("caption") or "", data.get("url"))
    try:
        if data["type"] == "photo":
            await context.bot.send_photo(chat_id, photo=data["file_id"], caption=caption, parse_mode="HTML")
        else:
            await context.bot.send_video(chat_id, video=data["file_id"], caption=caption, parse_mode="HTML")
        log.info(f"Sent single {data['type']} to {chat_id}")
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
            except:
                pass

async def flush_group(group_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_groups.pop(group_id, None)
    if not data or not data["media"]:
        return
    caption = build_caption(data.get("caption") or "", data.get("url"))
    first = data["media"][0]
    if isinstance(first, InputMediaPhoto):
        data["media"][0] = InputMediaPhoto(first.media, caption=caption, parse_mode="HTML")
    elif isinstance(first, InputMediaVideo):
        data["media"][0] = InputMediaVideo(first.media, caption=caption, parse_mode="HTML")
    try:
        await context.bot.send_media_group(chat_id, media=data["media"])
        log.info(f"Sent media group {group_id} ({len(data['media'])}) to {chat_id}")
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
            except:
                pass

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

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id

    try:
        # آلبوم
        if msg.media_group_id:
            group_id = f"group_{msg.media_group_id}"
            grp = pending_groups.get(group_id)
            if not grp:
                grp = pending_groups[group_id] = {
                    "media": [],
                    "caption": None,
                    "url": None,
                    "raw_msgs": [],
                    "timer": None,
                    "chat_id": chat_id,
                }
            grp["raw_msgs"].append(msg)

            if msg.photo:
                grp["media"].append(InputMediaPhoto(msg.photo[-1].file_id))
            elif msg.video:
                grp["media"].append(InputMediaVideo(msg.video.file_id))

            # کپشن یا URL از متن/کپشن
            if msg.caption and not grp["caption"]:
                grp["caption"] = msg.caption
                url_in = extract_url(msg.caption)
                if url_in and not grp["url"]:
                    grp["url"] = url_in

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
                "url": extract_url(msg.caption) if msg.caption else None,
                "raw_msgs": [msg],
                "timer": None,
            }
            t = asyncio.create_task(single_timer_task(chat_id, context))
            pending_single[chat_id]["timer"] = t
            return

        # متن (مثلاً کپشن جدا یا پیام URL)
        if msg.text:
            text = msg.text
            url_in = extract_url(text)

            if chat_id in pending_single:
                data = pending_single[chat_id]
                t = data.get("timer")
                if t:
                    t.cancel()
                if text:
                    data["caption"] = text
                if url_in and not data.get("url"):
                    data["url"] = url_in
                data["raw_msgs"].append(msg)
                await flush_single(chat_id, context)
                return

            group_id = last_group_by_chat.get(chat_id)
            if group_id and group_id in pending_groups:
                grp = pending_groups[group_id]
                grp["caption"] = text
                if url_in and not grp.get("url"):
                    grp["url"] = url_in
                grp["raw_msgs"].append(msg)
                if grp["timer"]:
                    grp["timer"].cancel()
                grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
                return

    except Exception as e:
        log.error(f"Handle failed: {e}")

# Handler
app.add_handler(MessageHandler(filters.ALL, handle))

log.info("🤖 Bot is running...")

# Webhook (بدون aiohttp)
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
)
