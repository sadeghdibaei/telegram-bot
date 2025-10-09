# 🛠️ Utility functions for caption formatting

def clean_caption(text: str) -> str:
    """
    🧼 Removes unwanted formatting, emojis, hashtags, and extra whitespace.
    """
    if not text:
        return ""
    return text.strip().replace("#", "").replace("🔥", "").replace("📸", "")

def build_final_caption(link: str, original_caption: str = "") -> str:
    """
    🧵 Combines cleaned caption with the original Instagram link.
    """
    cleaned = clean_caption(original_caption)
    raw_html = f'<a href="{link}">O P E N P O S T ⎋</a>'
    escaped = raw_html.replace("<", "&lt;").replace(">", "&gt;")
    return f"{cleaned}\n\n{escaped}" if cleaned else escaped
