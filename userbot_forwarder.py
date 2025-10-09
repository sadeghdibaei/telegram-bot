# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃        Telegram Userbot Forwarder       ┃
# ┃   Handles Instagram links, CDN fallback ┃
# ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from cdn_handler import handle_cdn_link

# ─────────────────────────────────────────────
# 🔧 CONFIGURATION
# ─────────────────────────────────────────────
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
TARGET_GROUP_ID = int(os.environ["TARGET_GROUP_ID"])

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ─────────────────────────────────────────────
# 📦 STATE & BUFFERS
# ─────────────────────────────────────────────
INSTAGRAM_REGEX = re.compile(r"(https?://)?(www\.)?instagram\.com/[^\s]+")
last_instagram_link = {}  # group_id → link
media_buffer = []         # list of InputMediaPhoto/Video
upload_state = {}         # group_id → {"step": ..., "link": ..., "caption": ..., "processing_msg_id": ..., "cdn_notice_id": ...}

# ─────────────────────────────────────────────
# 🧼 CAPTION CLEANER
# ─────────────────────────────────────────────
def clean_caption(text: str) -> str:
    blacklist = [
        "🤖 Downloaded with @iDownloadersBot",
        "🤖 دریافت شده توسط @iDownloadersBot"
    ]
    for phrase in blacklist:
        text = text.replace(phrase, "")
    return text.strip()

# ─────────────────────────────────────────────
# 🧪 TEST COMMAND
# ─────────────────────────────────────────────
@app.on_message(filters.command("testme"))
async def test_me(client: Client, message: Message):
    await client.send_message("me", "✅ تست ارسال به Saved Messages")

# ─────────────────────────────────────────────
# 📥 STEP 1: Detect Instagram link in group
# ─────────────────────────────────────────────
@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        link = match.group(0)
        group_id = message.chat.id

        last_instagram_link[group_id] = link
        media_buffer.clear()

        await client.send_message("iDownloadersBot", link)
        await message.delete()

        # ⏳ Show processing message
        processing_msg = await client.send_message(group_id, "Processing...⏳")

        # 🧠 Save state
        upload_state[group_id] = {
            "step": "waiting",
            "link": link,
            "processing_msg_id": processing_msg.id
        }

# ─────────────────────────────────────────────
# 📤 STEP 2: Handle response from @iDownloadersBot
# ─────────────────────────────────────────────
@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    for group_id, link in last_instagram_link.items():
        # 🕒 Handle "Please wait..." messages
        if message.text and "please wait" in message.text.lower():
            match = re.search(r"please wait (\d+) second", message.text.lower())
            wait_seconds = int(match.group(1)) if match else 11

            temp_msg = await client.send_message(group_id, message.text)
            await asyncio.sleep(min(wait_seconds, 15))
            await client.delete_messages(group_id, temp_msg.id)
            return

        # 🧹 Clean up processing message
        processing_msg_id = upload_state.get(group_id, {}).get("processing_msg_id")
        if processing_msg_id:
            await client.delete_messages(group_id, processing_msg_id)

        # 🔍 Check for CDN button
        if message.reply_markup:
            for row in message.reply_markup.inline_keyboard:
                for btn in row:
                    url = getattr(btn, "url", None)
                    if url and "cdn" in url:
                        cdn_link = url
                        cleaned = clean_caption(message.text or message.caption or "")

                        # 🧠 Save state for CDN fallback
                        upload_state[group_id] = {
                            "step": "waiting",
                            "link": link,
                            "caption": cleaned
                        }

                        cdn_notice = await client.send_message(group_id, "⏳ Large post detected. Processing via alternate CDN route...")
                        upload_state[group_id]["cdn_notice_id"] = cdn_notice.id

                        await client.send_message("urluploadxbot", cdn_link)
                        return

        # 📥 Buffer media
        if message.photo:
            media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
        elif message.video:
            media_buffer.append(InputMediaVideo(media=message.video.file_id))

        # 📝 Send media + final caption
        if media_buffer:
            # 🧹 Remove temporary messages before sending
            cdn_notice_id = upload_state.get(group_id, {}).get("cdn_notice_id")
            if cdn_notice_id:
                await client.delete_messages(group_id, cdn_notice_id)
        
            processing_msg_id = upload_state.get(group_id, {}).get("processing_msg_id")
            if processing_msg_id:
                await client.delete_messages(group_id, processing_msg_id)
        
            # ⏳ Short delay to ensure cleanup
            await asyncio.sleep(0.5)
        
            # 📤 Send media group in chunks of 10
            chunks = [media_buffer[i:i + 10] for i in range(0, len(media_buffer), 10)]
            for chunk in chunks:
                await client.send_media_group(group_id, media=chunk)
                print("📤 Sent media group chunk")
        
            # 📝 Build final caption from upload_state
            cleaned = upload_state[group_id].get("caption", "")
            link = upload_state[group_id].get("link", "")
            raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
            escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
            final_caption = f"{cleaned}\n\n{escaped}"
        
            # 📥 Send final caption
            await client.send_message(group_id, final_caption)
            print("📥 Sent caption with link")
        
            # 🧼 Clear buffer and state
            media_buffer.clear()
            upload_state.pop(group_id, None)
            return

        # ❌ No media, no CDN → fail
        await client.send_message(group_id, "❌ Failed to process the post. No media or CDN link found.")
        upload_state.pop(group_id, None)

# ─────────────────────────────────────────────
# 📦 STEP 3: Handle response from @urluploadxbot
# ─────────────────────────────────────────────
@app.on_message(filters.private & filters.user("urluploadxbot"))
async def handle_upload_response(client: Client, message: Message):
    # 🖱️ Auto-click "Default" button if rename prompt appears
    if message.text and "rename" in message.text.lower() and message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for i, btn in enumerate(row):
                if "default" in btn.text.lower():
                    await message.click(i)
                    for group_id in upload_state:
                        upload_state[group_id]["step"] = "processing"
                    return

    # 🎬 Final video delivery
    if message.video:
        for group_id, state in upload_state.items():
            # 🧹 Remove temporary messages before sending
            cdn_notice_id = state.get("cdn_notice_id")
            if cdn_notice_id:
                await client.delete_messages(group_id, cdn_notice_id)
    
            processing_msg_id = state.get("processing_msg_id")
            if processing_msg_id:
                await client.delete_messages(group_id, processing_msg_id)
    
            # ⏳ Short delay to ensure cleanup
            await asyncio.sleep(0.5)
    
            # 📝 Build final caption from upload_state
            cleaned = state.get("caption", "")
            link = state.get("link", "")
            raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
            escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
            final_caption = f"{cleaned}\n\n{escaped}"
    
            # 📤 Send video with final caption
            await client.send_video(
                group_id,
                video=message.video.file_id,
                caption=final_caption
            )
            print("📥 Final video + caption sent")
    
        # 🧼 Clear upload state
        upload_state.clear()
        return

    # 🧼 Skip irrelevant messages
    if message.photo or "۴ دقیقه" in message.text:
        return

    # ❌ Fallback failure
    for group_id, state in upload_state.items():
        cdn_notice_id = state.get("cdn_notice_id")
        if cdn_notice_id:
            await client.delete_messages(group_id, cdn_notice_id)

        processing_msg_id = state.get("processing_msg_id")
        if processing_msg_id:
            await client.delete_messages(group_id, processing_msg_id)

        await client.send_message(group_id, "❌ Failed to process the post. Please try again.")

# ─────────────────────────────────────────────
# 🚀 RUN
# ─────────────────────────────────────────────
print("🚀 Userbot is running with clean logic and CDN fallback...")
app.run()
