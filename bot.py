import os
import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import yt_dlp

BOT_TOKEN = os.environ.get("8582129257:AAEVJOF_EWD0uJBwXLAxGPdNVrwwHlQgs6I")
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE_MB = 50
FOLLOW_TEXT = "👉 আমাকে ফলো দিন: https://www.facebook.com/share/1BGBVAyguV/"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_facebook_url(url: str) -> str:
    url = url.strip()
    # সব ধরনের Facebook লিংক সাপোর্ট
    patterns = [
        r'https?://(www\.|m\.|web\.)?facebook\.com/\S+',
        r'https?://fb\.watch/\S+',
        r'https?://fb\.com/\S+',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(0)
    return url

def is_facebook_url(url: str) -> bool:
    return any(domain in url for domain in [
        "facebook.com", "fb.com", "fb.watch",
        "m.facebook.com", "web.facebook.com"
    ])

def download_video(url: str, quality: str = "hd") -> str | None:
    if quality == "hd":
        format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        format_selector = "worst[ext=mp4]/worst"

    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "format": format_selector,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "extractor_args": {
            "facebook": {
                "webpage_url_basename": "video",
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4"):
                filename = filename.rsplit(".", 1)[0] + ".mp4"
            return filename if os.path.exists(filename) else None
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Facebook Video Downloader*\n\n"
        "যেকোনো ফেসবুক ভিডিওর লিংক পাঠান!\n\n"
        "✅ Reels সাপোর্ট\n"
        "✅ Normal ভিডিও সাপোর্ট\n"
        "✅ Watch ভিডিও সাপোর্ট\n"
        "✅ সব ব্রাউজার ও অ্যাপের লিংক সাপোর্ট\n\n"
        f"⬇️ *ডাউনলোড*\n{FOLLOW_TEXT}",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = clean_facebook_url(update.message.text)

    if not is_facebook_url(url):
        await update.message.reply_text(
            "❌ ফেসবুক লিংক দিন!\n\n"
            f"⬇️ *ডাউনলোড*\n{FOLLOW_TEXT}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return

    keyboard = [[
        InlineKeyboardButton("🔵 HD", callback_data=f"hd|{url}"),
        InlineKeyboardButton("🟡 SD", callback_data=f"sd|{url}"),
    ]]
    await update.message.reply_text(
        "✅ কোন কোয়ালিটিতে ডাউনলোড করবেন?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def handle_quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality, url = query.data.split("|", 1)
    quality_label = "HD" if quality == "hd" else "SD"

    status_msg = await query.message.reply_text(f"⏳ {quality_label} ডাউনলোড হচ্ছে...")

    loop = asyncio.get_event_loop()
    filepath = await loop.run_in_executor(None, download_video, url, quality)

    if not filepath or not os.path.exists(filepath):
        await status_msg.edit_text(
            "❌ ডাউনলোড ব্যর্থ হয়েছে!\n\n"
            f"⬇️ *ডাউনলোড*\n{FOLLOW_TEXT}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        await status_msg.edit_text(f"⚠️ ফাইল অনেক বড় ({file_size_mb:.1f} MB)! SD তে ট্রাই করুন।")
        os.remove(filepath)
        return

    await status_msg.edit_text(f"📤 আপলোড হচ্ছে...")

    try:
        with open(filepath, "rb") as video_file:
            await query.message.reply_video(
                video=video_file,
                caption=f"✅ ডাউনলোড সম্পন্ন! [{quality_label}]\n\n⬇️ ডাউনলোড\n👉 আমাকে ফলো দিন: https://www.facebook.com/share/1BGBVAyguV/",
                supports_streaming=True,
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Send error: {e}")
        await status_msg.edit_text("❌ আপলোড ব্যর্থ হয়েছে!")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_quality_choice))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
