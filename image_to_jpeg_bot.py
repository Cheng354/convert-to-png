"""
Image to JPEG Converter Bot v2.0 - Khmer Edition
- All messages in Khmer
- Polished UX for Telegram Ads "destination quality" review
- Stats tracking, feedback system, inline buttons
"""

import os
import io
import json
import logging
from datetime import datetime
from threading import Thread, Lock
from flask import Flask
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8781608884:AAEv_O12Eq53boV6WkgKVo_Ja5nf-yRc1H4")
PORT = int(os.getenv("PORT", "10000"))
STATS_FILE = "/tmp/bot_stats.json"

# ---------- Stats (thread-safe) ----------
stats_lock = Lock()


def load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_conversions": 0, "users": [], "started": str(datetime.utcnow())}


def save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
        logger.warning(f"Could not save stats: {e}")


def increment_stats(user_id):
    with stats_lock:
        s = load_stats()
        s["total_conversions"] = s.get("total_conversions", 0) + 1
        if user_id not in s.get("users", []):
            s.setdefault("users", []).append(user_id)
        save_stats(s)
        return s


# ---------- Khmer texts ----------
START_TEXT = (
    "👋 *សូមស្វាគមន៍មកកាន់ Bot បំលែងរូបភាពទៅជា JPEG!*\n\n"
    "ខ្ញុំជួយបំលែងរូបភាពគ្រប់ប្រភេទទៅជា JPEG ភ្លាមៗ។\n\n"
    "*✨ លក្ខណៈពិសេស:*\n"
    "✅ គាំទ្រ PNG, WebP, BMP, GIF, TIFF និងច្រើនទៀត\n"
    "✅ គុណភាពខ្ពស់ (JPEG ៩៥%)\n"
    "✅ អាចផ្ញើជារូបភាព ឬជាឯកសារ\n"
    "✅ រក្សាឈ្មោះឯកសារដើម\n"
    "✅ ដោះស្រាយផ្ទៃថ្លាដោយស្វ័យប្រវត្តិ\n"
    "✅ ឥតគិតថ្លៃ ឥតចុះឈ្មោះ ឥតពាណិជ្ជកម្ម\n\n"
    "*📥 របៀបចាប់ផ្តើម:*\n"
    "គ្រាន់តែផ្ញើរូបភាពមកខ្ញុំ!\n\n"
    "វាយ /help សម្រាប់ការណែនាំពេញលេញ ឬ /about ដើម្បីស្វែងយល់បន្ថែម។"
)

HELP_TEXT = (
    "📌 *របៀបប្រើប្រាស់ Bot នេះ:*\n\n"
    "*វិធីទី ១ — ផ្ញើជារូបភាព* 📸\n"
    "ចុចលើ 📎 → Photo → ជ្រើសរើសរូបភាព → ផ្ញើ។\n"
    "_(Telegram នឹងបង្ហាប់បន្តិច)_\n\n"
    "*វិធីទី ២ — ផ្ញើជាឯកសារ* 📁\n"
    "ចុចលើ 📎 → File → ជ្រើសរើសរូបភាព → ផ្ញើ។\n"
    "_(គុណភាពល្អបំផុត — មិនបង្ហាប់)_\n\n"
    "*ប្រភេទរូបភាពដែលគាំទ្រ:*\n"
    "PNG • WebP • BMP • GIF • TIFF • HEIC • ICO\n\n"
    "*ទិន្នផល:* JPEG គុណភាព ៩៥%\n\n"
    "*បញ្ជាដែលអាចប្រើ:*\n"
    "/start — សារស្វាគមន៍\n"
    "/help — ការណែនាំ\n"
    "/about — អំពី Bot នេះ\n"
    "/stats — ស្ថិតិ\n"
    "/feedback — រាយការណ៍បញ្ហា ឬផ្តល់យោបល់"
)

ABOUT_TEXT = (
    "ℹ️ *អំពី Bot នេះ*\n\n"
    "*ឈ្មោះ:* Image to JPEG Converter\n"
    "*កំណែ:* ២.០\n"
    "*គោលបំណង:* បំលែងរូបភាពលឿន និងឥតគិតថ្លៃ\n\n"
    "*ហេតុអ្វីប្រើ JPEG?*\n"
    "JPEG គឺជាប្រភេទរូបភាពដែលគេទទួលយកច្រើនបំផុត។ "
    "គេហទំព័រ អ៊ីមែល និងសេវាបោះពុម្ពភាគច្រើនទទួលយកតែ JPEG។ "
    "Bot នេះនឹងបំលែងពីប្រភេទផ្សេងៗ (PNG, WebP ។ល។) ភ្លាមៗ។\n\n"
    "*ឯកជនភាព:*\n"
    "រូបភាពត្រូវបានដំណើរការក្នុង memory ហើយមិនត្រូវបានរក្សាទុកទេ។ "
    "យើងមិនរក្សារូបភាពរបស់អ្នកទេ។\n\n"
    "*តម្លៃ:* ឥតគិតថ្លៃ ១០០% ឥតពាណិជ្ជកម្ម\n\n"
    "បង្កើតដោយ ❤️ សម្រាប់អ្នកបង្កើតមាតិកា និងអ្នកប្រើទូទៅ។"
)

FEEDBACK_PROMPT = (
    "💬 *ផ្ញើយោបល់របស់អ្នក*\n\n"
    "មានយោបល់ បញ្ហា ឬគំនិតផ្តួចផ្តើម? "
    "ផ្ញើសារខាងក្រោម យើងនឹងពិនិត្យមើល។\n\n"
    "_(ឬវាយ /cancel ដើម្បីត្រឡប់ក្រោយ)_"
)

FEEDBACK_RECEIVED = (
    "✅ អរគុណ! យោបល់របស់អ្នកត្រូវបានកត់ត្រា។\n"
    "យើងពេញចិត្តដែលអ្នកជួយឱ្យ Bot នេះល្អប្រសើរឡើង។"
)

STATS_TEXT = (
    "📊 *ស្ថិតិ Bot*\n\n"
    "🖼️ ការបំលែងសរុប: *{conversions:,}*\n"
    "👥 អ្នកប្រើសរុប: *{users:,}*\n"
    "📅 Bot ដំណើរការតាំងពី: {started}"
)

CONVERTED_CAPTION = "✅ *បំលែងជា JPEG រួចរាល់*"
NOT_IMAGE = "⚠️ ឯកសារនេះមិនមែនជារូបភាពទេ។ សូមផ្ញើតែឯកសារដែលជារូបភាព (PNG, WebP, BMP, GIF ។ល។)"
ERROR_TEMPLATE = "❌ សុំទោស ការបំលែងមិនបានជោគជ័យ។\nមូលហេតុ: `{error}`\n\nសាកល្បងផ្ញើជាឯកសារជំនួសវិញ ឬប្រើ /feedback ដើម្បីរាយការណ៍។"

# ---------- Tiny web server ----------
flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    s = load_stats()
    return f"Image-to-JPEG bot running. Conversions: {s.get('total_conversions', 0)}", 200


def run_web():
    flask_app.run(host="0.0.0.0", port=PORT)


# ---------- Inline keyboard ----------
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❓ ជំនួយ", callback_data="cmd:help"),
            InlineKeyboardButton("ℹ️ អំពី", callback_data="cmd:about"),
        ],
        [
            InlineKeyboardButton("📊 ស្ថិតិ", callback_data="cmd:stats"),
            InlineKeyboardButton("💬 យោបល់", callback_data="cmd:feedback"),
        ],
    ])


# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        START_TEXT, parse_mode="Markdown", reply_markup=main_menu()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT, parse_mode="Markdown")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = load_stats()
    started = s.get("started", "unknown")[:10]
    text = STATS_TEXT.format(
        conversions=s.get("total_conversions", 0),
        users=len(s.get("users", [])),
        started=started,
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def feedback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text(FEEDBACK_PROMPT, parse_mode="Markdown")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting_feedback", None)
    await update.message.reply_text("✅ យល់ព្រម", reply_markup=main_menu())


# ---------- Callback (inline buttons) ----------
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cmd:help":
        await query.edit_message_text(HELP_TEXT, parse_mode="Markdown")
    elif data == "cmd:about":
        await query.edit_message_text(ABOUT_TEXT, parse_mode="Markdown")
    elif data == "cmd:stats":
        s = load_stats()
        started = s.get("started", "unknown")[:10]
        text = STATS_TEXT.format(
            conversions=s.get("total_conversions", 0),
            users=len(s.get("users", [])),
            started=started,
        )
        await query.edit_message_text(text, parse_mode="Markdown")
    elif data == "cmd:feedback":
        context.user_data["awaiting_feedback"] = True
        await query.edit_message_text(FEEDBACK_PROMPT, parse_mode="Markdown")


# ---------- Image conversion ----------
async def convert_to_jpeg(image_bytes: bytes) -> io.BytesIO:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95, optimize=True)
    out.seek(0)
    return out


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_chat_action("upload_document")
        photo = update.message.photo[-1]
        file = await photo.get_file()
        image_bytes = bytes(await file.download_as_bytearray())
        jpeg_buf = await convert_to_jpeg(image_bytes)
        await update.message.reply_document(
            document=jpeg_buf, filename="converted.jpg",
            caption=CONVERTED_CAPTION, parse_mode="Markdown",
        )
        increment_stats(update.effective_user.id)
    except Exception as e:
        logger.exception("Photo conversion failed")
        await update.message.reply_text(
            ERROR_TEMPLATE.format(error=str(e)), parse_mode="Markdown"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        await update.message.reply_text(NOT_IMAGE)
        return
    try:
        await update.message.reply_chat_action("upload_document")
        file = await doc.get_file()
        image_bytes = bytes(await file.download_as_bytearray())
        jpeg_buf = await convert_to_jpeg(image_bytes)
        original_name = os.path.splitext(doc.file_name or "image")[0]
        await update.message.reply_document(
            document=jpeg_buf, filename=f"{original_name}.jpg",
            caption=CONVERTED_CAPTION, parse_mode="Markdown",
        )
        increment_stats(update.effective_user.id)
    except Exception as e:
        logger.exception("Document conversion failed")
        await update.message.reply_text(
            ERROR_TEMPLATE.format(error=str(e)), parse_mode="Markdown"
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches feedback messages or general text."""
    if context.user_data.get("awaiting_feedback"):
        msg = update.message.text or ""
        logger.info(f"FEEDBACK from {update.effective_user.id}: {msg}")
        context.user_data["awaiting_feedback"] = False
        await update.message.reply_text(FEEDBACK_RECEIVED, reply_markup=main_menu())
        return
    await update.message.reply_text(
        "👋 សួស្តី! សូមផ្ញើរូបភាពមកខ្ញុំដើម្បីបំលែងជា JPEG។",
        reply_markup=main_menu(),
    )


# ---------- Set up command menu in Telegram ----------
async def setup_commands(app):
    commands = [
        BotCommand("start", "ចាប់ផ្តើម"),
        BotCommand("help", "របៀបប្រើ"),
        BotCommand("about", "អំពី Bot នេះ"),
        BotCommand("stats", "ស្ថិតិ"),
        BotCommand("feedback", "ផ្ញើយោបល់"),
    ]
    await app.bot.set_my_commands(commands)


# ---------- Main ----------
def main():
    if not BOT_TOKEN or BOT_TOKEN == "8781608884:AAEv_O12Eq53boV6WkgKVo_Ja5nf-yRc1H4":
        raise RuntimeError("BOT_TOKEN not set! Set it as an environment variable on Render.")

    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).post_init(setup_commands).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("feedback", feedback_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Image-to-JPEG Bot v2.0 (Khmer) started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
