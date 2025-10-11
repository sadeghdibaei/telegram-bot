# 🛠️ Utility functions for caption formatting

def clean_caption(text: str) -> str:
    if not text:
        return ""
    blacklist = [
        "🤖 Downloaded with @iDownloadersBot",
        "🤖 دریافت شده توسط @iDownloadersBot",
        "Join the Download videos from «Instagram, Twitter and YouTube» bot",
        "ID: @Multi_Media_Downloader_bot",
        "به ربات «دانلود ویدیو از اینستاگرام، توییتر و یوتیوب» ملحق شوید"
    ]
    for phrase in blacklist:
        text = text.replace(phrase, "")
    return text.strip()

def build_final_caption(link: str, original_caption: str = "") -> str:
    cleaned = clean_caption(original_caption)
    if not link:
        print("⚠️ Empty link passed to build_final_caption")
        return cleaned or "⚠️ No link available"

    # Build anchor and escape so Telegram won’t auto-hyperlink it
    raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
    escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")

    # Caption: cleaned text + escaped anchor block
    return f"{cleaned}\n\n{escaped}" if cleaned else escaped
