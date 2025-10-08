# =========================================
# Telegram Merge Bot (HLS Video + Audio)
# Safe Version (Token via Colab)
# =========================================

import os
import asyncio
import requests
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# 🔹 These will be filled at runtime from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

VIDEO_URL, AUDIO_URL = range(2)

# 🟢 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Please send me the *video URL* first.", parse_mode="Markdown")
    return VIDEO_URL

# 🟢 Step 1: Get Video URL
async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["video_url"] = update.message.text.strip()
    await update.message.reply_text("✅ Got video URL. Now send me the *audio URL*.", parse_mode="Markdown")
    return AUDIO_URL

# 🟢 Step 2: Get Audio URL and Merge
async def get_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio_url = update.message.text.strip()
    video_url = context.user_data.get("video_url")
    if not video_url:
        await update.message.reply_text("❌ Missing video URL. Please send /start again.")
        return ConversationHandler.END

    await update.message.reply_text("🎬 Merging your video and audio... Please wait ⏳")

    output_file = "merged_output.mp4"
    cmd = f'ffmpeg -y -i "{video_url}" -i "{audio_url}" -c copy -map 0:v:0 -map 1:a:0 "{output_file}"'
    process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists(output_file):
        await update.message.reply_text("❌ Merge failed. Check URLs and try again.")
        print(process.stderr.decode())
        return ConversationHandler.END

    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    await update.message.reply_text(f"✅ Merge complete! File size: {size_mb:.1f} MB\n📤 Uploading to Telegram...")

    with open(output_file, "rb") as f:
        await update.message.reply_document(f, caption="🎥 Your merged video")

    os.remove(output_file)
    await update.message.reply_text("✅ Done! Send /start for another merge.")
    return ConversationHandler.END

# 🟠 /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send /start again anytime.")
    return ConversationHandler.END

# 🧠 main function
def main():
    if not BOT_TOKEN:
        raise ValueError("⚠️ BOT_TOKEN not set! Please define it before running.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VIDEO_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_video)],
            AUDIO_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_audio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("🤖 Bot started successfully.")
    app.run_polling()

if __name__ == "__main__":
    main()
