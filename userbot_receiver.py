import os
from fastapi import FastAPI, Request
from telegram import Bot

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

    if not chat_id or not file_id:
        return {"error": "Missing chat_id or file_id"}

    try:
        if len(caption) > MAX_CAPTION:
            short_caption = caption[:MAX_CAPTION]
            rest = caption[MAX_CAPTION:]
            await bot.send_video(chat_id=chat_id, video=file_id, caption=short_caption)
            await bot.send_message(chat_id=chat_id, text=rest)
        else:
            await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}
