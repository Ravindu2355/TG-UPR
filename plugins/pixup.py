import os
import time
import requests
import base64
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config

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

# ====== PixelDrain Upload Function ======
async def uupload_to_pixeldrain(app: Client, file_path, file_name, message: Message):
    time_data = {"start": time.time(), "last_update": time.time()}
    total_size = os.path.getsize(file_path)

    def file_gen():
        with open(file_path, "rb") as f:
            sent = 0
            while chunk := f.read(1024 * 1024):
                sent += len(chunk)
                app.loop.create_task(progress_callback(sent, total_size, message, time_data, label="Uploading"))
                yield chunk

    try:
        response = requests.post(
            "https://pixeldrain.com/api/file",
            files={"file": (file_name, file_gen())}
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


async def upload_to_pixeldrain(app: Client, file_path, file_name, message: Message):
    time_data = {"start": time.time(), "last_update": time.time()}
    total_size = os.path.getsize(file_path)

    try:
        with open(file_path, "rb") as f:
            class ProgressReader:
                def __init__(self, file_obj):
                    self.file = file_obj
                    self.sent = 0

                def read(self, size=-1):
                    chunk = self.file.read(size)
                    if chunk:
                        self.sent += len(chunk)
                        app.loop.create_task(progress_callback(
                            self.sent, total_size, message, time_data, label="Uploading"
                        ))
                    return chunk

            monitored_file = ProgressReader(f)
            encodedK = base64.b64encode(f':{PIXELDRAIN_API_KEY}'.encode()).decode()
            headers = {
                "Authorization": f"Basic {encodedK}"
            }

            response = requests.post(
                "https://pixeldrain.com/api/file",
                files={"file": (file_name, monitored_file)},
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
