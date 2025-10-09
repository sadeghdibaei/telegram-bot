import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from cdn_handler import handle_cdn_link

# ---------------------------
# Config & Session
# ---------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
TARGET_GROUP_ID = int(os.environ["TARGET_GROUP_ID"])

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------------------------
# State & Buffers
# ---------------------------
INSTAGRAM_REGEX = re.compile(r"(https?://)?(www\.)?instagram\.com/[^\s]+")
last_instagram_link = {}  # chat_id → link
media_buffer = []         # list of InputMediaPhoto/Video
upload_state = {}         # group_id → {"step": "waiting"|"processing"}
pending_caption = {}      # group_id → asyncio.Task

# ---------------------------
# Caption Cleaning
# ---------------------------
def clean_caption(text: str) -> str:
    blacklist = [
        "🤖 Downloaded with @iDownloadersBot",
        "🤖 دریافت شده توسط @iDownloadersBot"
    ]
    for phrase in blacklist:
        text = text.replace(phrase, "")
    return text.strip()

@app.on_message(filters.command("testme"))
async def test_me(client: Client, message: Message):
    await client.send_message("me", "✅ تست ارسال به Saved Messages")

# ---------------------------
# Step 3: Delegate all messages from @urluploadxbot to cdn_handler
# ---------------------------
@app.on_message(filters.private & filters.user("urluploadxbot"))
async def handle_upload_response(client: Client, message: Message):
    await handle_cdn_link(client, message)

# ---------------------------
# Utility: Forward any inline-button message to Saved Messages
# ---------------------------
async def forward_message_and_buttons(client: Client, message: Message):
    try:
        print("📤 Forwarding message to Saved Messages...")
        await message.forward("me")

        lines = ["🔘 دکمه‌های شیشه‌ای موجود در پیام:"]
        for row_index, row in enumerate(message.reply_markup.inline_keyboard):
            for col_index, btn in enumerate(row):
                label = btn.text
                url = getattr(btn, "url", None)
                callback = getattr(btn, "callback_data", None)

                line = f"▪️ [{row_index},{col_index}] '{label}'"
                if url:
                    line += f"\n   🌐 URL: {url}"
                if callback:
                    line += f"\n   📦 Callback: {callback}"
                lines.append(line)

        summary = "\n".join(lines)
        await client.send_message("me", summary)
        print("📤 Sent button summary to Saved Messages")

    except Exception as e:
        print("❌ Error in forward_message_and_buttons:", e)

# ---------------------------
# Step 1: Detect Instagram link in group
# ---------------------------
@app.on_message(filters.group & filters.text)
async def handle_instagram_link(client: Client, message: Message):
    match = INSTAGRAM_REGEX.search(message.text)
    if match:
        try:
            link = match.group(0)
            last_instagram_link[message.chat.id] = link
            media_buffer.clear()

            await client.send_message("iDownloadersBot", link)
            print("📤 Sent link to iDownloadersBot")

            await message.delete()
            print("🗑️ Deleted original message")

        except Exception as e:
            print("❌ Error sending to bot:", e)

# ---------------------------
# Step 2: Handle response from iDownloadersBot and extract CDN link
# ---------------------------
@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        for group_id, link in last_instagram_link.items():
            # مرحله ۱: بررسی وجود دکمه‌ها
            if message.reply_markup:
                print("🔍 reply_markup detected, analyzing buttons...")

                for row_index, row in enumerate(message.reply_markup.inline_keyboard):
                    for col_index, btn in enumerate(row):
                        label = btn.text
                        url = getattr(btn, "url", None)
                        callback = getattr(btn, "callback_data", None)

                        print(f"🔘 Button [{row_index},{col_index}]: '{label}'")
                        print(f"   🌐 URL: {url}")
                        print(f"   📦 Callback: {callback}")

                        if url and "cdn" in url:
                            cdn_link = url
                            print(f"✅ Found CDN link: {cdn_link}")

                            cleaned = clean_caption(message.text or message.caption or "")
                            upload_state[group_id] = {
                                "step": "waiting",
                                "link": link,
                                "caption": cleaned
                            }

                            await client.send_message("urluploadxbot", cdn_link)
                            print(f"📤 Sent CDN link to @urluploadxbot")
                            return

            # مرحله ۲: اگر کپشن داشت، اول پردازش کن
            if message.text or message.caption:
                cleaned = clean_caption(message.caption or message.text or "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"

                if pending_caption.get(group_id):
                    pending_caption[group_id].cancel()
                    del pending_caption[group_id]
                    print("🛑 Caption arrived: Cancelled timeout")

                if media_buffer:
                    MAX_MEDIA_PER_GROUP = 10
                    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]

                    for index, chunk in enumerate(chunks):
                        await client.send_media_group(group_id, media=chunk)
                        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")

                    await client.send_message(group_id, final_caption)
                    print("📥 Sent caption with link")

                    media_buffer.clear()
                else:
                    print("⚠️ No media found, caption skipped")
                return  # چون کپشن رسید، ادامه نده

            # مرحله ۳: اگر مدیا بود، بافر کن و تایمر بذار
            if message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")
            elif message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")

            if group_id not in pending_caption:
                async def send_without_caption():
                    await asyncio.sleep(10)

                    if media_buffer:
                        raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                        escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                        final_caption = escaped

                        if len(media_buffer) == 1:
                            media = media_buffer[0]
                            if isinstance(media, InputMediaPhoto):
                                await client.send_photo(group_id, photo=media.media)
                            elif isinstance(media, InputMediaVideo):
                                await client.send_video(group_id, video=media.media)
                            await client.send_message(group_id, final_caption)
                            print("⏱️ Timeout: Sent single media + separate link caption")
                        else:
                            await client.send_media_group(group_id, media=media_buffer)
                            await client.send_message(group_id, final_caption)
                            print("⏱️ Timeout: Sent media group + separate link caption")

                        media_buffer.clear()
                        pending_caption.pop(group_id, None)

                pending_caption[group_id] = asyncio.create_task(send_without_caption())

    except Exception as e:
        print("❌ Error handling iDownloadersBot response:", e)

# ---------------------------
# Step 3: Forward all inline-button messages from @urluploadxbot to Saved Messages
# ---------------------------
@app.on_message(filters.private & filters.user("urluploadxbot"))
async def handle_upload_response(client: Client, message: Message):
    try:
        if "rename" in message.text.lower() and message.reply_markup:
            clicked = False
            for row in message.reply_markup.inline_keyboard:
                for i, btn in enumerate(row):
                    if "default" in btn.text.lower():
                        await message.click(i)
                        print(f"✅ Clicked 'Default' button: {btn.text}")
                        clicked = True
                        for group_id in upload_state:
                            upload_state[group_id]["step"] = "processing"
                        break
                if clicked:
                    break

            if not clicked:
                print("⚠️ No 'Default' button found, skipping rename step")
            return

        if message.video:
            for group_id, state in upload_state.items():
                link = state.get("link")
                cleaned = state.get("caption", "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"

                await client.send_video(
                    group_id,
                    video=message.video.file_id,
                    caption=final_caption
                )
                print("📥 Final video + caption sent")

            upload_state.clear()
            return

        if message.photo or "۴ دقیقه" in message.text:
            print("⏭ Skipped non-video message from @urluploadxbot")
            return

    except Exception as e:
        print("❌ Error handling upload response:", e)

# ---------------------------
# Run
# ---------------------------
print("🚀 Userbot is running with full CDN fallback logic...")
app.run()
