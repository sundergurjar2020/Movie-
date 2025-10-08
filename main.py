# =========================================
# Telegram Merge Bot (HLS Video + Audio)
# Author: Vicky Style 😎
# =========================================
# Features:
#  - /start command to begin
#  - Asks for video URL, then audio URL
#  - Downloads and merges using ffmpeg
#  - Sends merged file back (up to 2GB)
# =========================================

import os
import asyncio
import requests
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# Telegram bot token
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

# Conversation steps
VIDEO_URL, AUDIO_URL = range(2)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me the *video URL* first.", parse_mode="Markdown")
    return VIDEO_URL

# Step 1: get video URL
async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["video_url"] = update.message.text.strip()
    await update.message.reply_text("✅ Got video URL. Now send me the *audio URL*.", parse_mode="Markdown")
    return AUDIO_URL

# Step 2: get audio URL and start merging
async def get_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio_url = update.message.text.strip()
    video_url = context.user_data.get("video_url")
    if not video_url:
        await update.message.reply_text("❌ Missing video URL. Please send /start again.")
        return ConversationHandler.END

    await update.message.reply_text("🎬 Merging your video and audio... Please wait ⏳")

    # filenames
    output_file = "merged.mp4"

    # merge command
    cmd = f'ffmpeg -y -i "{video_url}" -i "{audio_url}" -c copy -map 0:v:0 -map 1:a:0 "{output_file}"'
    process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists(output_file):
        await update.message.reply_text("❌ Failed to merge. Check URLs or try again.")
        print(process.stderr.decode())
        return ConversationHandler.END

    size = os.path.getsize(output_file)
    mb = size / 1024 / 1024

    await update.message.reply_text(f"✅ Merge complete! File size: {mb:.2f} MB\n📤 Uploading to Telegram...")

    # Upload file
    with open(output_file, "rb") as f:
        await update.message.reply_document(f, caption="🎥 Your merged video file")

    # Clean up
    os.remove(output_file)
    await update.message.reply_text("✅ Done! Send /start to merge another video.")
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send /start to begin again.")
    return ConversationHandler.END

# Main function
def main():
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
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
