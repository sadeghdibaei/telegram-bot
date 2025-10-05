import os
import asyncio
import logging
from typing import Dict, Optional
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from aiohttp import web
import json

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

def shorten_caption(text: Optional[str], limit: int) -> str:
    if not text:
        return ""
    return text[:limit - 3] + "..." if len(text) > limit else text

def build_caption(base_caption: str, url: Optional[str]) -> str:
    caption = shorten_caption(base_caption, MAX_CAPTION)
    if url:
        caption += f"\n\n<a href=\"{url}\">O P E N P O S T ⎋</a>"
    return caption

# -------------------------
# هندلر برای پیام‌های POST از یوزربات
# -------------------------
async def userbot_handler(request):
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        log.info(f"Received from userbot: {data}")

        # اگر مدیا بود
        if "file_id" in data:
            caption = build_caption(data.get("caption") or "", data.get("url"))
            if data["type"] == "photo":
                await app.bot.send_photo(chat_id, photo=data["file_id"], caption=caption, parse_mode="HTML")
            elif data["type"] == "video":
                await app.bot.send_video(chat_id, video=data["file_id"], caption=caption, parse_mode="HTML")

        # اگر متن بود
        elif "text" in data:
            caption = build_caption(data["text"], data.get("url"))
            await app.bot.send_message(chat_id, text=caption, parse_mode="HTML")

        return web.Response(text="ok")

    except Exception as e:
        log.error(f"userbot_handler error: {e}")
        return web.Response(status=500, text="error")

# -------------------------
# هندلر معمولی (برای تست مستقیم)
# -------------------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id

    if msg.photo:
        caption = build_caption(msg.caption or "", None)
        await context.bot.send_photo(chat_id, photo=msg.photo[-1].file_id, caption=caption, parse_mode="HTML")
    elif msg.video:
        caption = build_caption(msg.caption or "", None)
        await context.bot.send_video(chat_id, video=msg.video.file_id, caption=caption, parse_mode="HTML")
    elif msg.text:
        caption = build_caption(msg.text, None)
        await context.bot.send_message(chat_id, text=caption, parse_mode="HTML")

# -------------------------
# ثبت هندلرها
# -------------------------
app.add_handler(MessageHandler(filters.ALL, handle))

# اضافه کردن روت برای /userbot
async def on_startup(app_):
    app_.router.add_post("/userbot", userbot_handler)

web_app = web.Application()
web_app.router.add_post("/userbot", userbot_handler)

print("🤖 Bot is running on Railway...")

# اجرای وبهوک
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    web_app=web_app
)
