# 🛠️ Utility functions for caption formatting

import re

def clean_caption(text: str) -> str:
    if not text:
        return ""

    # Known bot signatures (both Persian & English)
    signatures = [
        r"🤖\s*Downloaded with @iDownloadersBot",
        r"🤖\s*دریافت شده توسط @iDownloadersBot",
        r"Join the Download videos from «Instagram, Twitter and YouTube» bot",
        r"ID:\s*@Multi_Media_Downloader_bot",
        r"به ربات «دانلود ویدیو از اینستاگرام، توییتر و یوتیوب» ملحق شوید",
        r"🤖\s*Downloaded with @Multi_Media_Downloader_bot",
        r"🤖\s*دریافت شده توسط @Multi_Media_Downloader_bot",
    ]

    cleaned = text
    for sig in signatures:
        cleaned = re.sub(sig, "", cleaned, flags=re.IGNORECASE)

    # Normalize whitespace: remove empty lines, trim spaces
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def build_final_caption(link: str, original_caption: str = "") -> str:
    """
    Build final caption for media attachment.
    Rules:
    - Telegram media caption limit: 1024 chars.
    - Reserve 21 chars for: "..." (3) + newline (1) + "O P E N P O S T ⎋" (17).
    - If caption exceeds 1003 chars, truncate and append "...".
    - Final output ends with a newline + "O P E N P O S T ⎋".
    - The downstream bot will convert "O P E N P O S T ⎋" into a hyperlink.
    """
    from utils import clean_caption

    LINK_TEXT = "O P E N P O S T ⎋"
    MAX_MEDIA_CAPTION = 1024
    RESERVED = 21  # 3 ("...") + 1 (newline) + 17 (LINK_TEXT)
    ALLOWED = MAX_MEDIA_CAPTION - RESERVED  # 1003

    cleaned = clean_caption(original_caption) or ""

    # Truncate if needed, keeping room for "..." + newline + LINK_TEXT
    if len(cleaned) > ALLOWED:
        cleaned = cleaned[:ALLOWED] + "..."

    # If no caption, just LINK_TEXT
    if not cleaned:
        return LINK_TEXT

    # Single newline before link (counts as 1 char in RESERVED)
    return f"{cleaned}\n{LINK_TEXT}"
