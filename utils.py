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
    from utils import clean_caption  # use existing cleaner if defined elsewhere

    cleaned = clean_caption(original_caption)
    if not link:
        print("⚠️ Empty link passed to build_final_caption")
        return cleaned or "⚠️ No link available"

    # Build escaped link text (Telegram won't auto-hyperlink it)
    raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
    escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")

    # Telegram caption limit when attached to media
    MAX_CAPTION_LEN = 1024
    reserved = len("\n\n" + escaped) if cleaned else len(escaped)
    allowed = MAX_CAPTION_LEN - reserved

    # Truncate caption if too long
    if cleaned and len(cleaned) > allowed:
        if allowed > 3:
            cleaned = cleaned[:allowed - 3] + "..."
        else:
            cleaned = ""

    # Final caption: cleaned text + escaped link
    return f"{cleaned}\n\n{escaped}" if cleaned else escaped
