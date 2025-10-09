# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃         CDN Handler for Userbot         ┃
# ┃   Handles fallback media via @urluploadxbot ┃
# ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

import re
from pyrogram import Client
from pyrogram.types import Message

# 📦 Shared upload state (imported from main file)
upload_state = {}

# ─────────────────────────────────────────────
# 📥 MAIN HANDLER FUNCTION
# ─────────────────────────────────────────────
async def handle_cdn_link(client: Client, message: Message):
    chat_id = message.chat.id

    # ─────────────────────────────────────────────
    # 🔍 STEP 1: Detect CDN link in inline buttons
    # ─────────────────────────────────────────────
    if message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url and "cdninstagram.com" in btn.url:
                    cdn_link = btn.url

                    # 🧹 Remove previous "Processing..." message
                    processing_msg_id = upload_state.get(chat_id, {}).get("processing_msg_id")
                    if processing_msg_id:
                        await client.delete_messages(chat_id, processing_msg_id)

                    # ⏳ Notify about large post
                    cdn_notice = await client.send_message(
                        chat_id,
                        "⏳ Large post detected. Processing via alternate CDN route..."
                    )

                    # 🧠 Save state
                    upload_state[chat_id] = {
                        "step": "waiting",
                        "cdn_notice_id": cdn_notice.id
                    }

                    # 📤 Send CDN link to @urluploadxbot
                    await client.send_message("urluploadxbot", cdn_link)
                    print(f"📤 Sent CDN link to @urluploadxbot")
                    return

    # ─────────────────────────────────────────────
    # 🖱️ STEP 2: Auto-click "Default" button if rename prompt appears
    # ─────────────────────────────────────────────
    if message.text and "rename" in message.text.lower() and message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for i, btn in enumerate(row):
                if "default" in btn.text.lower():
                    await message.click(i)
                    print(f"✅ Clicked 'Default' button: {btn.text}")
                    for group_id in upload_state:
                        upload_state[group_id]["step"] = "processing"
                    return

    # ─────────────────────────────────────────────
    # 🎬 STEP 3: Final video received
    # ─────────────────────────────────────────────
    if message.video and chat_id in upload_state:
        print("📥 Final video received from @urluploadxbot")

        # 🧹 Remove temporary messages
        cdn_notice_id = upload_state[chat_id].get("cdn_notice_id")
        if cdn_notice_id:
            await client.delete_messages(chat_id, cdn_notice_id)

        processing_msg_id = upload_state[chat_id].get("processing_msg_id")
        if processing_msg_id:
            await client.delete_messages(chat_id, processing_msg_id)

        # ✅ Return video file ID for final delivery
        upload_state.pop(chat_id, None)
        return message.video.file_id

    # ─────────────────────────────────────────────
    # ⏭ STEP 4: Skip irrelevant messages
    # ─────────────────────────────────────────────
    if message.photo or "۴ دقیقه" in message.text:
        print("⏭ Skipped non-video message from @urluploadxbot")
        return

    # ─────────────────────────────────────────────
    # ❌ STEP 5: Fallback failure
    # ─────────────────────────────────────────────
    cdn_notice_id = upload_state.get(chat_id, {}).get("cdn_notice_id")
    if cdn_notice_id:
        await client.delete_messages(chat_id, cdn_notice_id)

    processing_msg_id = upload_state.get(chat_id, {}).get("processing_msg_id")
    if processing_msg_id:
        await client.delete_messages(chat_id, processing_msg_id)

    await client.send_message(chat_id, "❌ Failed to process the post. Please try again.")
    upload_state.pop(chat_id, None)
