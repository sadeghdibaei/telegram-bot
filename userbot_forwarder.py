import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo

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

# ---------------------------
# Utility: Forward inline buttons to Saved Messages
# ---------------------------
async def forward_message_and_buttons(client: Client, message: Message):
    try:
        # مرحله اول: فوروارد خود پیام
        await message.forward("me")
        print("📤 Forwarded message to Saved Messages")

        # مرحله دوم: استخراج دکمه‌ها
        if not message.reply_markup:
            await client.send_message("me", "⛔ پیام دکمه‌ی شیشه‌ای نداشت.")
            return

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
        print("📤 Sent inline button summary to Saved Messages")

    except Exception as e:
        print("❌ Error forwarding or extracting buttons:", e)

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
# Step 2: Handle response from iDownloadersBot
# ---------------------------
@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        for group_id, link in last_instagram_link.items():
            # Case: oversized file → only button with CDN link
            if message.reply_markup and not (message.photo or message.video):
                for row in message.reply_markup.inline_keyboard:
                    for btn in row:
                        if btn.url and "cdninstagram.com" in btn.url:
                            cdn_link = btn.url
                            cleaned = clean_caption(message.text or message.caption or "")
                            upload_state[group_id] = {
                                "step": "waiting",
                                "link": link,
                                "caption": cleaned
                            }

                            await client.send_message("urluploadxbot", cdn_link)
                            print("📤 Sent CDN link to @urluploadxbot")
                            return

            # Case: media content
            if message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")

            elif message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")

            elif message.text or message.caption:
                cleaned = clean_caption(message.caption or message.text or "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"

                if media_buffer:
                    await client.send_media_group(group_id, media=media_buffer)
                    print("📤 Sent media group")

                    await client.send_message(group_id, final_caption)
                    print("📥 Sent caption with link")

                    media_buffer.clear()
                else:
                    print("⚠️ No media found, caption skipped")


    except Exception as e:
        print("❌ Error forwarding bot response:", e)

# ---------------------------
# Step 3: Handle response from urluploadxbot
# ---------------------------
@app.on_message(filters.private & filters.user("urluploadxbot"))
async def handle_upload_response(client: Client, message: Message):
    try:
        # فقط پیام‌هایی که واقعاً دکمه‌ی آپلود دارن رو تحلیل کن
        if message.reply_markup and (
            "rename" in message.text.lower() or
            "how would you like to upload" in message.text.lower()
        ):
            await forward_message_and_buttons(client, message)

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

        # دریافت ویدیو و ارسال همراه با کپشن
        if message.video and upload_state:
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

        # رد کردن پیام‌های غیرمفید
        if message.photo or "processing" in message.text.lower() or "۴ دقیقه" in message.text:
            print("⏭ Skipped non-actionable message from @urluploadxbot")
            return

    except Exception as e:
        print("❌ Error handling upload response:", e)


# ---------------------------
# Run
# ---------------------------
print("🚀 Userbot is running with full CDN fallback logic...")
app.run()
