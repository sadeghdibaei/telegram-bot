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


def build_final_caption(link: str, caption: str) -> str:
    """
    Build final caption with safe length and mandatory link.
    - Telegram caption limit when attached to media is 1024 chars.
    - If caption is too long, truncate and add "..."
    - Always append the link part at the end.
    """
    # Always add the link at the end
    link_part = f'\n\n<a href="{link}">O P E N P O S T ⎋</a>' if link else ""

    # Telegram caption limit when attached to media
    MAX_CAPTION_LEN = 1024

    # Reserve space for link part
    reserved = len(link_part)
    allowed = MAX_CAPTION_LEN - reserved

    # If caption is too long, truncate and add "..."
    if len(caption) > allowed:
        caption = caption[:allowed - 3] + "..."

    return f"{caption}{link_part}"
