from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from state import media_buffer, pending_caption, upload_state, last_instagram_link
from utils import build_final_caption
import asyncio

def register_handlers(app: Client):
    @app.on_message(filters.private & filters.user("iDownloadersBot"))
    async def handle_bot_response(client: Client, message: Message):
        # 🔁 Full logic for media, caption, CDN, fallback...
        ...
