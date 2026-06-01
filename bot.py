import os
import asyncio
import logging
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

BOT_TOKEN = "8582129257:AAEVJOF_EWD0uJBwXLAxGPdNVrwwHlQgs6I"
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE_MB = 50

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def is_facebook_url(url: str) -> bool:
    return any(domain in url for domain in [
        "facebook.com", "fb.com", "fb.watch", "m.facebook.com"
    ])

def download_video(url: str, quality: str = "hd") -> str | None:
    if quality == "hd":
        format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        format_selector = "worstvideo[ext=mp4]+worstaudio/worst[ext=mp4]/worst"

    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "format": format_selector,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
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
        "🎬 *Facebook Video Downloader Bot*\n\n"
        "ফেসবুক ভিডিওর লিংক পাঠান, আমি HD ভিডিও ডাউনলোড করে দেব!\n\n"
        "✅ Public ভিডিও সাপোর্ট করে\n"
        "✅ Reels সাপোর্ট করে\n"
        "✅ Watch ভিডিও সাপোর্ট করে\n\n"
        "👨‍💻 *Developer:* [Riaz](https://www.facebook.com/share/1BGBVAyguV/)\n\n"
        "⚠️ শুধুমাত্র Public ভিডিও ডাউনলোড করা যাবে।",
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_facebook_url(url):
        await update.message.reply_text(
            "❌ এটা ফেসবুক লিংক না!\n"
            "ফেসবুক ভিডিওর লিংক দিন।"
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("🔵 HD", callback_data=f"hd|{url}"),
            InlineKeyboardButton("🟡 SD", callback_data=f"sd|{url}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✅ কোন কোয়ালিটিতে ডাউনলোড করবেন?",
        reply_markup=reply_markup,
    )

async def handle_quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality, url = query.data.split("|", 1)
    quality_label = "HD" if quality == "hd" else "SD"

    status_msg = await query.message.reply_text(f"⏳ {quality_label} তে ডাউনলোড হচ্ছে...")

    loop = asyncio.get_event_loop()
    filepath = await loop.run_in_executor(None, download_video, url, quality)

    if not filepath or not os.path.exists(filepath):
        await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে!")
        return

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        await status_msg.edit_text(f"⚠️ ফাইল অনেক বড় ({file_size_mb:.1f} MB)!")
        os.remove(filepath)
        return

    await status_msg.edit_text(f"📤 আপলোড হচ্ছে...")

    try:
        with open(filepath, "rb") as video_file:
            await query.message.reply_video(
                video=video_file,
                caption=f"✅ ডাউনলোড সম্পন্ন! [{quality_label}]\n\n👨‍💻 Developer: https://www.facebook.com/share/1BGBVAyguV/",
                supports_streaming=True,
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Send error: {e}")
        await status_msg.edit_text("❌ ভিডিও পাঠাতে সমস্যা হয়েছে।")
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
