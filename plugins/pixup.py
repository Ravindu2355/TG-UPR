import os
import time, random
import requests
import base64
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
import aiohttp
import asyncio
import json
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

PIXELDRAIN_API_KEY = Config.PixKey

# ====== Progress Utils ======
async def progress_callback(current, total, message: Message, start_data, label="Progress"):
    now = time.time()
    if now - start_data["last_update"] >= 5:
        percent = current * 100 / total
        speed = current / (now - start_data["start"] + 1)
        eta = (total - current) / speed if speed > 0 else 0
        try:
            await message.edit_text(
                f"{label}...\n"
                f"`{percent:.2f}%` done\n"
                f"Speed: `{speed / 1024:.2f} KB/s`\n"
                f"ETA: `{int(eta)}s`"
            )
            start_data["last_update"] = now
        except Exception:
            pass


async def upload_to_pixeldrain(app: Client, file_path, file_name, message: Message):
    time_data = {"start": time.time(), "last_update": time.time()}
    total_size = os.path.getsize(file_path)
    try:
        def create_callback(encoder):
            def callback(monitor):
                app.loop.create_task(progress_callback(
                    monitor.bytes_read, total_size, message, time_data, label="Uploading"
                ))
            return callback

        with open(file_path, "rb") as f:
            encoder = MultipartEncoder(fields={
                "file": (file_name, f, "application/octet-stream")
            })

            monitor = MultipartEncoderMonitor(encoder, create_callback(encoder))

            headers = {
                "Content-Type": monitor.content_type,
                "Authorization": "Basic " + base64.b64encode(f':{PIXELDRAIN_API_KEY}'.encode()).decode()
            }

            response = requests.post(
                "https://pixeldrain.com/api/file",
                data=monitor,
                headers=headers
            )

        return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}



# ====== Command Handler ======
@Client.on_message(filters.command("pix") & filters.reply)
async def pix_command_handler(client: Client, message: Message):
    media = message.reply_to_message

    if not (media.video or media.document or media.audio or media.voice):
        return await message.reply("Reply to a supported file (video, document, audio, or voice).")

    file_name = (
        media.video.file_name if media.video else
        media.document.file_name if media.document else
        media.audio.file_name if media.audio else
        "voice_note.ogg"
    )
    random_str = str(random.randint(1000000000, 9999999999))
    if not file_name:
        file_name = (
        f"video_{random_str}.mp4" if media.video else
        f"doc_{random_str}.text" if media.document else
        f"audio_{random_str}.mp3" if media.audio else
        "voice_note.ogg"
        )
    status = await message.reply(f"Downloading `{file_name}`...")
    time_data = {"start": time.time(), "last_update": time.time()}

    try:
        file_path = await media.download(
    progress=lambda cur, tot: client.loop.create_task(
        progress_callback(cur, tot, status, time_data, "Downloading")
    ))
    except Exception as e:
        return await status.edit_text(f"Download failed: `{str(e)}`")

    await status.edit_text("Download complete! Uploading to PixelDrain...")

    result = await upload_to_pixeldrain(client, file_path, file_name, status)

    if result.get("success"):
        await status.edit_text(f"**Upload complete!**\n\n**Link:** https://pixeldrain.com/u/{result['id']}")
    else:
        await status.edit_text(f"Upload failed: `{result.get('message')}`")

    try:
        os.remove(file_path)
    except:
        pass
