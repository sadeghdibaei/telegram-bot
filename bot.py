import os
import asyncio
import logging
import sys
import re
from typing import Dict, Optional
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout
                   )
log = logging.getLogger("relay-bot")

# ---------------------------
# Environment variables
# ---------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# ---------------------------
# Application (PTB v20+)
# ---------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------------------------
# Config
# ---------------------------
EXTRA_LINK_BLOCK = 60
MAX_CAPTION = 1024 - EXTRA_LINK_BLOCK
SINGLE_DEBOUNCE_SECS = 3
GROUP_DEBOUNCE_SECS = 4

# ---------------------------
# State buffers
# ---------------------------
pending_single: Dict[int, Dict] = {}
pending_groups: Dict[str, Dict] = {}
last_group_by_chat: Dict[int, str] = {}

# ---------------------------
# Helper functions
# ---------------------------
def shorten_caption(text: Optional[str], limit: int) -> str:
    if not text:
        return ""
    return text[:limit - 3] + "..." if len(text) > limit else text

def clean_caption(text: Optional[str]) -> str:
    if not text:
        return ""
    return text.replace("🤖 Downloaded with @iDownloadersBot", "").strip()

def extract_linked_caption(caption: Optional[str]) -> str:
    """از کپشن HTML لینک را استخراج کرده و دوباره با فرمت صحیح می‌سازد."""
    if not caption:
        return ""
    match = re.search(r'<a href="([^"]+)">O P E N P O S T ⎋</a>', caption)
    link = match.group(1) if match else None
    cleaned = re.sub(r'<a href="[^"]+">O P E N P O S T ⎋</a>', '', caption).strip()
    cleaned = shorten_caption(clean_caption(cleaned), MAX_CAPTION)
    if link:
        return f"{cleaned}\n\n<a href=\"{link}\">O P E N P O S T ⎋</a>"
    else:
        return cleaned

def extract_button_url(msg) -> Optional[str]:
    if not msg or not msg.reply_markup or not msg.reply_markup.inline_keyboard:
        return None
    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if getattr(btn, "url", None):
                return btn.url
    return None

# ---------------------------
# Flush operations
# ---------------------------
async def flush_single(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_single.pop(chat_id, None)
    if not data:
        log.info(f"⏭ No pending single for chat {chat_id}")
        return

    caption = extract_linked_caption(data.get("caption") or "")
    log.info(f"🚀 Flushing single {data['type']} to {chat_id} | file_id={data['file_id']}")

    try:
        if data["type"] == "photo":
            sent = await context.bot.send_photo(
                chat_id, photo=data["file_id"], caption=caption, parse_mode="HTML"
            )
        else:
            sent = await context.bot.send_video(
                chat_id, video=data["file_id"], caption=caption, parse_mode="HTML"
            )
        log.info(f"✅ Sent single {data['type']} to {chat_id} | message_id={sent.message_id}")
    except Exception as e:
        log.error(f"❌ Failed to send single media to {chat_id}: {e}")
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
                log.info(f"🗑 Deleted raw message {getattr(m,'message_id',None)} in {chat_id}")
            except Exception as e:
                log.warning(f"⚠️ Could not delete raw message {getattr(m,'message_id',None)} in {chat_id}: {e}")

async def flush_group(group_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = pending_groups.pop(group_id, None)
    if not data or not data["media"]:
        log.info(f"⏭ No pending media for group {group_id} in chat {chat_id}")
        return

    caption = extract_linked_caption(data.get("caption") or "")
    log.info(f"🚀 Flushing media group {group_id} ({len(data['media'])} items) to {chat_id}")

    first = data["media"][0]
    if isinstance(first, InputMediaPhoto):
        data["media"][0] = InputMediaPhoto(first.media, caption=caption, parse_mode="HTML")
    elif isinstance(first, InputMediaVideo):
        data["media"][0] = InputMediaVideo(first.media, caption=caption, parse_mode="HTML")

    try:
        res = await context.bot.send_media_group(chat_id, media=data["media"])
        first_id = res[0].message_id if res else None
        log.info(f"✅ Sent media group {group_id} to {chat_id} | first_message_id={first_id}")
    except Exception as e:
        log.error(f"❌ Failed to send media group {group_id} to {chat_id}: {e}")
    finally:
        for m in data.get("raw_msgs", []):
            try:
                await m.delete()
                log.info(f"🗑 Deleted raw message {getattr(m,'message_id',None)} in {chat_id}")
            except Exception as e:
                log.warning(f"⚠️ Could not delete raw message {getattr(m,'message_id',None)} in {chat_id}: {e}")

# ---------------------------
# Debounce timers
# ---------------------------
async def single_timer_task(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    log.info(f"⏳ Starting single debounce timer for chat {chat_id} ({SINGLE_DEBOUNCE_SECS}s)")
    try:
        await asyncio.sleep(SINGLE_DEBOUNCE_SECS)
    except asyncio.CancelledError:
        log.info(f"⏹ Single debounce timer cancelled for chat {chat_id}")
        return
    await flush_single(chat_id, context)

async def group_timer_task(group_id: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    log.info(f"⏳ Starting group debounce timer for {group_id} in chat {chat_id} ({GROUP_DEBOUNCE_SECS}s)")
    try:
        await asyncio.sleep(GROUP_DEBOUNCE_SECS)
    except asyncio.CancelledError:
        log.info(f"⏹ Group debounce timer cancelled for {group_id} in chat {chat_id}")
        return
    await flush_group(group_id, chat_id, context)
    if last_group_by_chat.get(chat_id) == group_id:
        last_group_by_chat.pop(chat_id, None)

# ---------------------------
# Main handler
# ---------------------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    chat_id = update.effective_chat.id
    button_url_in = extract_button_url(msg)

    try:
        if msg.media_group_id:
            group_id = f"group_{msg.media_group_id}"
            log.info(f"📥 Received media group item in chat {chat_id}, group_id={group_id}")

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
                log.info(f"➕ New group buffer created for {group_id}")

            grp["raw_msgs"].append(msg)

            if msg.photo:
                fid = msg.photo[-1].file_id
                grp["media"].append(InputMediaPhoto(fid))
                log.info(f"🖼 Added photo to group {group_id} | file_id={fid}")
            elif msg.video:
                fid = msg.video.file_id
                grp["media"].append(InputMediaVideo(fid))
                log.info(f"🎞 Added video to group {group_id} | file_id={fid}")

            if msg.caption and not grp["caption"]:
                grp["caption"] = msg.caption
                log.info(f"✍️ Caption set for group {group_id}")
            if button_url_in and not grp["button_url"]:
                grp["button_url"] = button_url_in
                log.info(f"🔗 Button URL set for group {group_id}")

            last_group_by_chat[chat_id] = group_id

            if grp["timer"]:
                grp["timer"].cancel()
                log.info(f"⏹ Reset group timer for {group_id}")
            grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
            return

        # تک‌مدیا (single photo/video)
        if msg.photo or msg.video:
            media_type = "photo" if msg.photo else "video"
            log.info(f"📥 Received single {media_type} in chat {chat_id}")

            if chat_id in pending_single:
                t = pending_single[chat_id].get("timer")
                if t:
                    t.cancel()
                    log.info(f"⏹ Cancelled previous single timer in chat {chat_id}")
                await flush_single(chat_id, context)

            file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id
            pending_single[chat_id] = {
                "file_id": file_id,
                "type": media_type,
                "caption": msg.caption or None,
                "button_url": button_url_in or None,
                "raw_msgs": [msg],
                "timer": None,
            }
            log.info(f"➕ Added pending single {media_type} in chat {chat_id} | file_id={file_id}")

            t = asyncio.create_task(single_timer_task(chat_id, context))
            pending_single[chat_id]["timer"] = t
            return

        # کپشن جدا (text که بعد از مدیا می‌آید)
        if msg.text:
            text = msg.text
            log.info(f"📥 Received text in chat {chat_id}: {text[:40]}...")

            if chat_id in pending_single:
                data = pending_single[chat_id]
                t = data.get("timer")
                if t:
                    t.cancel()
                    log.info(f"⏹ Cancelled single timer in chat {chat_id} (caption arrived)")
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
                    log.info(f"⏹ Cancelled group timer for {group_id} (caption arrived)")
                grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
                return

    except Exception as e:
        log.error(f"❌ Handle failed in chat {chat_id}: {e}")

# ---------------------------
# Handler registration
# ---------------------------
app.add_handler(MessageHandler(filters.ALL, handle))

log.info("🤖 Bot is running on Railway...")

# ---------------------------
# Webhook runner
# ---------------------------
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
)
