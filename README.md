📦 Telegram Instagram Relay Bot
A modular Pyrogram-based userbot that automatically downloads Instagram posts shared in a Telegram group and re-posts the media with a clean caption and link. It uses external bots like @iDownloadersBot and @urluploadxbot to fetch and deliver content.

🧠 Project Logic Overview
🔗 Group Input
Detects Instagram links posted in a Telegram group

Deletes the original message for cleanliness

Sends the link to @iDownloadersBot

📥 Bot Response Handling
Buffers incoming media (photo/video)

Extracts CDN links from inline buttons (if present)

Cleans and stores captions

Sends CDN links to @urluploadxbot for final delivery

📤 Final Output
Sends media in chunks (max 10 per group)

Sends caption separately, combining original text (if any) + Instagram link

Falls back to sending only the link if no caption arrives within 10 seconds

🧩 File Structure
File	Purpose
config.py	Bot usernames, regex patterns, constants
state.py	Shared buffers and tracking dictionaries
utils.py	Caption cleaning and formatting helpers
userbot_forwarder.py	Handles group input and media forwarding
cdn_handler.py	Handles CDN link responses and final media delivery
⚙️ Setup Instructions
Clone the repo and create a new Python virtual environment

Install dependencies:

bash
pip install pyrogram tgcrypto
Create a config.env or use environment variables for:

API_ID

API_HASH

SESSION_STRING (from Pyrogram userbot login)

Run the bot:

bash
python userbot_forwarder.py
🧪 Testing Tips
Send an Instagram link in your test group

Watch the bot delete the message and forward it to @iDownloadersBot

Confirm media arrives and caption is built correctly

Try links with and without captions to test fallback logic

Test media groups with more than 10 items to confirm chunking

📌 Notes
Telegram limits media groups to 10 items — handled automatically

Captions are always sent separately for consistency

CDN links are routed through @urluploadxbot and clicked automatically

All logic is modular and easy to extend
