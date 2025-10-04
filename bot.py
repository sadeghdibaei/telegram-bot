import os
import asyncio
from typing import Dict, List, Optional
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

# Env vars
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 5000))

# App
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Config
MAX_CAPTION = 1024
SINGLE_DEBOUNCE_SECS = 3     # منتظر کپشن برای تک‌مدیا
GROUP_DEBOUNCE_SECS = 2      # جمع‌آوری آیتم‌های آلبوم

# State
pending_single: Dict[int, Dict] = {}     # key = chat_id
pending_groups: Dict[str, Dict] = {}     # key = group_id string
last_group_by_chat: Dict[int, str] = {}  # آخرین گروه مرتبط با هر چت (برای کپشن جدا)

def shorten_caption(text: Optional[str]) -> str:
    if not text:
        return ""
    return text[:MAX_CAPTION - 3] + "..." if len(text) > MAX_CAPTION else text

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

    caption = shorten_caption(data.get("caption"))
    button_url = data.get("button_url")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("مشاهده در اینستاگرام", url=button_url)]]) if button_url else None

    try:
        if data["type"] == "photo":
            await context.bot.send_photo(chat_id, photo=data["file_id"], caption=caption, reply_markup=reply_markup)
        else:
            await context.bot.send_video(chat_id, video=data["file_id"], caption=caption, reply_markup=reply_markup)
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

    media_list = data["media"]
    caption = shorten_caption(data.get("caption"))
    button_url = data.get("button_url")

    try:
        # آلبوم را بدون دکمه ارسال کن (تلگرام اجازه دکمه روی آلبوم نمی‌دهد)
        await context.bot.send_media_group(chat_id, media=media_list)

        # اگر کپشن یا دکمه داریم → پیام جدا
        if caption or button_url:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("مشاهده در اینستاگرام", url=button_url)]]) if button_url else None
            await context.bot.send_message(chat_id, text=caption or "مشاهده در اینستاگرام", reply_markup=reply_markup)
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

    # 1) Media group (آلبوم)
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

        # ذخیره مدیا
        if msg.photo:
            grp["media"].append(InputMediaPhoto(msg.photo[-1].file_id))
        elif msg.video:
            grp["media"].append(InputMediaVideo(msg.video.file_id))

        # کپشن روی یکی از آیتم‌ها (forward شده) یا جدا می‌آید
        if msg.caption and not grp["caption"]:
            grp["caption"] = msg.caption  # کوتاه‌سازی را هنگام flush انجام می‌دهیم

        # دکمه اگر در یکی از پیام‌ها باشد
        if button_url_in and not grp["button_url"]:
            grp["button_url"] = button_url_in

        # برای کپشن جدا بعد از آلبوم
        last_group_by_chat[chat_id] = group_id

        # Debounce: هر بار که آیتمی رسید، تایمر را ریست کن
        if grp["timer"]:
            grp["timer"].cancel()
        grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
        return

    # 2) تک‌مدیا (عکس یا ویدیو)
    if msg.photo or msg.video:
        # اگر قبلاً تک‌مدیا در انتظار بود، اول همان را flush کن تا تداخل نشود
        if chat_id in pending_single:
            # پیشگیری از مسابقه: اگر تایمر در حال اجراست، کنسل و فوری flush کن
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

        # اگر کپشن همراه مدیا نبود، منتظر کپشن جدا شو
        # اگر بود، باز هم ۳ ثانیه صبر می‌کنیم تا شاید کپشن کامل‌تر جدا برسد
        t = asyncio.create_task(single_timer_task(chat_id, context))
        pending_single[chat_id]["timer"] = t
        return

    # 3) متن (احتمالاً کپشن جدا یا پیام دکمه)
    if msg.text:
        text = msg.text

        # اگر تک‌مدیا در انتظار داریم → بچسبان و flush
        if chat_id in pending_single:
            data = pending_single[chat_id]
            # ریست تایمر و ارسال
            t = data.get("timer")
            if t:
                t.cancel()
            # به‌روزرسانی کپشن و دکمه (اگر تازه رسید)
            if text:
                data["caption"] = text
            if button_url_in and not data["button_url"]:
                data["button_url"] = button_url_in
            # پیام متن هم جزء raw_msgs برای پاک کردن
            data["raw_msgs"].append(msg)
            await flush_single(chat_id, context)
            return

        # اگر آخرین گروه این چت هنوز باز است → این متن را کپشن گروه در نظر بگیر
        group_id = last_group_by_chat.get(chat_id)
        if group_id and group_id in pending_groups:
            grp = pending_groups[group_id]
            grp["caption"] = text
            if button_url_in and not grp["button_url"]:
                grp["button_url"] = button_url_in
            grp["raw_msgs"].append(msg)
            # ریست تایمر تا پس از این متن آلبوم ارسال شود
            if grp["timer"]:
                grp["timer"].cancel()
            grp["timer"] = asyncio.create_task(group_timer_task(group_id, chat_id, context))
            return

        # در غیر این صورت: متن مستقل است (کاری نمی‌کنیم)
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
    # پس از ارسال گروه، پاک‌سازی نشانگر آخرین گروه
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
