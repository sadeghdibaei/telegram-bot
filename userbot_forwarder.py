import os
import re
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

            # ارسال پیام Processing...⏳ به گروه
            processing_msg = await client.send_message(
                message.chat.id,
                "Processing...⏳"
            )
            
            # ذخیره وضعیت برای مراحل بعدی
            upload_state[message.chat.id] = {
                "step": "waiting",
                "link": link,
                "processing_msg_id": processing_msg.id
            }

        except Exception as e:
            print("❌ Error sending to bot:", e)

# ---------------------------
# Step 2: Handle response from iDownloadersBot and extract CDN link
# ---------------------------
@app.on_message(filters.private & filters.user("iDownloadersBot"))
async def handle_bot_response(client: Client, message: Message):
    try:
        # مرحله فوری: اگر پیام شامل "Please wait..." بود، ارسال و حذف بعدی
        if message.text and "please wait" in message.text.lower():
            import re
            match = re.search(r"please wait (\d+) second", message.text.lower())
            wait_seconds = int(match.group(1)) if match else 11
    
            for group_id in last_instagram_link:
                temp_msg = await client.send_message(group_id, message.text)
    
                import asyncio
                await asyncio.sleep(min(wait_seconds, 15))  # محدود به ۱۵ ثانیه برای اطمینان
                await client.delete_messages(group_id, temp_msg.id)
    
            return

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

                        # مرحله ۲: استخراج لینک CDN از دکمه
                        if url and "cdn" in url:
                            cdn_link = url
                            print(f"✅ Found CDN link: {cdn_link}")

                            # مرحله ۳: پاک‌سازی کپشن
                            cleaned = clean_caption(message.text or message.caption or "")

                            # مرحله ۴: ذخیره وضعیت برای مرحله بعدی
                            upload_state[group_id] = {
                                "step": "waiting",
                                "link": link,
                                "caption": cleaned
                            }

                            # حذف پیام Processing...⏳ اگر وجود داشت
                            old_msg_id = upload_state[group_id].get("processing_msg_id")
                            if old_msg_id:
                                await client.delete_messages(group_id, old_msg_id)
                            
                            # ارسال پیام مخصوص پست‌های حجیم
                            cdn_notice = await client.send_message(
                                group_id,
                                "⏳ Large post detected. Processing via alternate CDN route..."
                            )
                            
                            # ذخیره وضعیت جدید
                            upload_state[group_id] = {
                                "step": "waiting",
                                "link": link,
                                "caption": cleaned,
                                "cdn_notice_id": cdn_notice.id
                            }

                            # مرحله ۵: ارسال لینک به @urluploadxbot
                            await client.send_message("urluploadxbot", cdn_link)
                            print(f"📤 Sent CDN link to @urluploadxbot")
                            return

            # مرحله ۶: اگر پیام شامل مدیا بود، ذخیره در بافر
            if message.photo:
                media_buffer.append(InputMediaPhoto(media=message.photo.file_id))
                print("📥 Buffered photo")

            elif message.video:
                media_buffer.append(InputMediaVideo(media=message.video.file_id))
                print("📥 Buffered video")

            # مرحله ۷: اگر کپشن داشت، ارسال همراه با مدیا
            if message.text or message.caption:
                cleaned = clean_caption(message.caption or message.text or "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"
            
                MAX_MEDIA_PER_GROUP = 10
            
                if media_buffer:
                    # تقسیم آلبوم به دسته‌های 10‌تایی
                    chunks = [media_buffer[i:i + MAX_MEDIA_PER_GROUP] for i in range(0, len(media_buffer), MAX_MEDIA_PER_GROUP)]
            
                    for index, chunk in enumerate(chunks):
                        await client.send_media_group(group_id, media=chunk)
                        print(f"📤 Sent media group chunk {index + 1}/{len(chunks)}")
            
                    # ارسال کپشن نهایی بعد از آخرین chunk
                    await client.send_message(group_id, final_caption)
                    print("📥 Sent caption with link")
            
                    media_buffer.clear()
                    return  # جلوگیری از اجرای مرحله شکست
                else:
                    print("⚠️ No media found, caption skipped")

            # مرحله آخر: اگر نه دکمه بود، نه مدیا، فقط کپشن → پردازش شکست خورده
            else:
                # حذف پیام موقت
                cdn_notice_id = upload_state.get(group_id, {}).get("cdn_notice_id")
                if cdn_notice_id:
                    await client.delete_messages(group_id, cdn_notice_id)
            
                processing_msg_id = upload_state.get(group_id, {}).get("processing_msg_id")
                if processing_msg_id:
                    await client.delete_messages(group_id, processing_msg_id)
            
                # ارسال پیام خطا
                await client.send_message(group_id, "❌ Failed to process the post. No media found.")
                upload_state.pop(group_id, None)

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
                # حذف پیام‌های موقت
                cdn_notice_id = state.get("cdn_notice_id")
                if cdn_notice_id:
                    await client.delete_messages(group_id, cdn_notice_id)
        
                processing_msg_id = state.get("processing_msg_id")
                if processing_msg_id:
                    await client.delete_messages(group_id, processing_msg_id)
        
                # ساخت کپشن نهایی
                link = state.get("link")
                cleaned = state.get("caption", "")
                raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
                escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
                final_caption = f"{cleaned}\n\n{escaped}"
        
                # ارسال ویدیو با کپشن نهایی
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

        for group_id, state in upload_state.items():
            cdn_notice_id = state.get("cdn_notice_id")
            if cdn_notice_id:
                await client.delete_messages(group_id, cdn_notice_id)
        
            processing_msg_id = state.get("processing_msg_id")
            if processing_msg_id:
                await client.delete_messages(group_id, processing_msg_id)
        
            await client.send_message(group_id, "❌ Failed to process the post. Please try again.")

    except Exception as e:
        print("❌ Error handling upload response:", e)

# ---------------------------
# Run
# ---------------------------
print("🚀 Userbot is running with full CDN fallback logic...")
app.run()
