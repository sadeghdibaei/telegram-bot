from fastapi import FastAPI, Request
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = Bot(token=BOT_TOKEN)
app = FastAPI()

MAX_CAPTION = 1024

@app.post("/userbot")
async def receive_userbot(request: Request):
    data = await request.json()
    chat_id = data.get("chat_id")
    file_id = data.get("file_id")
    caption = data.get("caption", "")
    instagram_url = data.get("instagram_url")

    if not chat_id or not file_id:
        return {"error": "Missing chat_id or file_id"}

    # ساخت دکمه کلیکی
    keyboard = None
    if instagram_url:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("مشاهده در اینستاگرام", url=instagram_url)]
        ])

    # برش کپشن اگر طولانی بود
    if len(caption) > MAX_CAPTION:
        caption = caption[:MAX_CAPTION - 3] + "..."

    try:
        await bot.send_video(chat_id=chat_id, video=file_id, caption=caption, reply_markup=keyboard)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}
