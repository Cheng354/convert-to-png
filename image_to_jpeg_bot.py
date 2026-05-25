import os
import io
import logging
from threading import Thread
from flask import Flask
from PIL import Image
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Config ----------
# WARNING: Hardcoding tokens is insecure. Prefer setting BOT_TOKEN as an
# environment variable on Render instead of leaving it in code.
BOT_TOKEN = os.getenv("BOT_TOKEN", "8781608884:AAEv_O12Eq53boV6WkgKVo_Ja5nf-yRc1H4")

PORT = int(os.getenv("PORT", "10000"))  # Render injects PORT automatically

# ---------- Tiny web server (keeps Render web service alive) ----------
flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    return "Image-to-JPEG bot is running.", 200


def run_web():
    flask_app.run(host="0.0.0.0", port=PORT)


# ---------- Bot handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 សួស្តី! ខ្ញុំជា Bot បំលែងរូបភាពទៅជា JPEG។\n\n"
        "📸 គ្រាន់តែផ្ញើរូបភាពមកខ្ញុំ (PNG, WebP, BMP, GIF ។ល។) "
        "ខ្ញុំនឹងបំលែងវាទៅជា JPEG ភ្លាមៗ!\n\n"
        "💡 គន្លឹះ: អ្នកអាចផ្ញើជា *រូបភាព* ឬ *ឯកសារ/ហ្វាល់* ក៏បានដែរ។\n\n"
        "វាយ /help ដើម្បីមើលការណែនាំបន្ថែម។"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 របៀបប្រើប្រាស់:\n\n"
        "1️⃣ ផ្ញើរូបភាពមកខ្ញុំ\n"
        "2️⃣ ខ្ញុំនឹងបំលែងវាទៅជា JPEG ហើយផ្ញើត្រឡប់ទៅអ្នកវិញ\n\n"
        "📋 បញ្ជាដែលអាចប្រើបាន:\n"
        "/start - ចាប់ផ្តើម\n"
        "/help  - មើលការណែនាំ\n\n"
        "❓ មានបញ្ហា? សាកល្បងផ្ញើរូបជាឯកសារ (file) ជំនួសវិញ។"
    )


async def convert_to_jpeg(image_bytes: bytes) -> io.BytesIO:
    """Open image bytes, convert to JPEG, return as BytesIO."""
    img = Image.open(io.BytesIO(image_bytes))

    # JPEG doesn't support transparency — flatten onto white background
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=95, optimize=True)
    output.seek(0)
    return output


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images sent as photos (compressed by Telegram)."""
    try:
        await update.message.reply_chat_action("upload_document")
        photo = update.message.photo[-1]  # highest resolution
        file = await photo.get_file()
        image_bytes = bytes(await file.download_as_bytearray())

        jpeg_buf = await convert_to_jpeg(image_bytes)
        await update.message.reply_document(
            document=jpeg_buf,
            filename="converted.jpg",
            caption="✅ បំលែងជា JPEG រួចរាល់!",
        )
    except Exception as e:
        logger.exception("Photo conversion failed")
        await update.message.reply_text(
            f"❌ សុំទោស! ការបំលែងមិនបានជោគជ័យទេ។\nមូលហេតុ: {e}"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images sent as files/documents (uncompressed)."""
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        await update.message.reply_text(
            "⚠️ ឯកសារនេះមិនមែនជារូបភាពទេ។\n"
            "សូមផ្ញើតែឯកសារដែលជារូបភាពប៉ុណ្ណោះ។"
        )
        return

    try:
        await update.message.reply_chat_action("upload_document")
        file = await doc.get_file()
        image_bytes = bytes(await file.download_as_bytearray())

        jpeg_buf = await convert_to_jpeg(image_bytes)
        original_name = os.path.splitext(doc.file_name or "image")[0]
        await update.message.reply_document(
            document=jpeg_buf,
            filename=f"{original_name}.jpg",
            caption="✅ បំលែងជា JPEG រួចរាល់!",
        )
    except Exception as e:
        logger.exception("Document conversion failed")
        await update.message.reply_text(
            f"❌ សុំទោស! ការបំលែងមិនបានជោគជ័យទេ។\nមូលហេតុ: {e}"
        )


# ---------- Main ----------
def main():
    # Start tiny web server in background so Render keeps the service alive
    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))

    logger.info("Bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
