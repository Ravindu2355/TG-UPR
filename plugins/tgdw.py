import os
import time
import asyncio
from pyrogram.errors import FloodWait
from humanize import naturalsize
from log import logger as lg

async def download_file(client, message, file_path, msg):
    """Downloads media with progress updates."""
    
    # Check if the message contains a valid media type
    if not (message.document or message.video or message.audio or message.photo):
        await msg.edit_text("❌ No valid media found in the message.")
        return None

    # Get file details
    if message.document:
        file_name = message.document.file_name or "document"
        file_size = message.document.file_size
        file_info = message.document
    elif message.video:
        file_name = message.video.file_name or "video.mp4"
        file_size = message.video.file_size
        file_info = message.video
    elif message.audio:
        file_name = message.audio.file_name or "audio.mp3"
        file_size = message.audio.file_size
        file_info = message.audio
    else:  # Photo
        file_name = f"{message.photo.file_id}.jpg"
        file_size = 0  # Telegram handles photo sizes internally
        file_info = message.photo

    file_path = os.path.join(file_path, file_name)

    # Track last progress update
    last_msg, last_t = "", 0
    start_time = time.time()

    async def progress_func(current, total):
        nonlocal last_msg, last_t
        percent = (current / total) * 100 if total else 0
        speed = current / (time.time() - start_time) if current else 0
        eta = (total - current) / speed if speed > 0 else 0

        msg_text = (
            f"**Downloading...**\n\n"
            f"📂 Name: `{file_name}`\n"
            f"📏 Size: {naturalsize(file_size)}\n"
            f"📤 Downloaded: {naturalsize(current)}/{naturalsize(total)} ({percent:.2f}%)\n"
            f"⚡ Speed: {naturalsize(speed)}/s\n"
            f"⏳ ETA: {int(eta)}s"
        )

        # Update message every 10 seconds or if text changes
        if last_t == 0 or time.time() - last_t >= 10:
            if msg_text != last_msg:
                try:
                    await msg.edit_text(msg_text)
                    last_msg = msg_text
                    last_t = time.time()
                except FloodWait as e:
                    await asyncio.sleep(e.value)

    try:
        # Download the file with progress updates
        await client.download_media(
            message=file_info,
            file_name=file_path,
            progress=progress_func
        )

        # Final message update
        await msg.edit_text(f"✅ **Download Complete!**\n📂 `{file_name}`\n📏 Size: {naturalsize(file_size)}")
        return file_path

    except Exception as e:
        await msg.edit_text(f"❌ Error while downloading the file: {e}")
        lg.error(f"Error downloading file: {e}")
        return None
