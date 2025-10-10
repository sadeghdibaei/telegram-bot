# 🛠️ Utility functions for caption formatting

def clean_caption(text: str) -> str:
    if not text:
        return ""
    blacklist = [
        "🤖 Downloaded with @iDownloadersBot",
        "🤖 دریافت شده توسط @iDownloadersBot"
    ]
    for phrase in blacklist:
        text = text.replace(phrase, "")
    return text.strip()

def build_final_caption(link: str, original_caption: str = "") -> str:
    cleaned = clean_caption(original_caption)
    if not link:
        print("⚠️ Empty link passed to build_final_caption")
        return cleaned or "⚠️ No link available"
    return f"{cleaned}\n\n<a href=\"{link}\">O P E N P O S T ⎋</a>" if cleaned else f"<a href=\"{link}\">O P E N P O S T ⎋</a>"
