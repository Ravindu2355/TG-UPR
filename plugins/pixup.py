import os
import time
import random
import base64
import json
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from Func.downloader import dl
from Func.utils import is_direct_download

PIXELDRAIN_API_KEY = Config.PixKey

# ====== Progress Callback ======
async def progress_callback(current, total, message: Message, start_data, label="Progress"):
    now = time.time()
    if now - start_data["last_update"] >= 5:
        percent = current * 100 / total
        speed = current / (now - start_data["start"] + 1)
        eta = (total - current) / speed if speed > 0 else 0
        try:
            await message.edit_text(
                f"{label}\n"
                f"**{percent:.2f}%** completed\n"
                f"⚡ Speed: `{speed / 1024:.2f} KB/s`\n"
                f"⏳ ETA: `{int(eta)}s`"
            )
            start_data["last_update"] = now
        except Exception:
            pass

# ====== Upload to PixelDrain ======
async def upload_to_pixeldrain(app: Client, file_path, file_name, message: Message):
    time_data = {"start": time.time(), "last_update": time.time()}
    total_size = os.path.getsize(file_path)

    async def file_reader():
        with open(file_path, 'rb') as f:
            chunk_size = 65536
            bytes_read = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                await progress_callback(bytes_read, total_size, message, time_data, label="⬆️ Uploading")
                yield chunk

    try:
        data = aiohttp.FormData()
        data.add_field('file', file_reader(), filename=file_name, content_type='application/octet-stream')

        headers = {
            "Authorization": "Basic " + base64.b64encode(f':{PIXELDRAIN_API_KEY}'.encode()).decode()
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://pixeldrain.com/api/file", data=data, headers=headers) as resp:
                text = await resp.text()
                try:
                    res = json.loads(text)
                except Exception:
                    if resp.status == 200:
                        return {"success": True, "id": "UNKNOWN"}
                    else:
                        return {"success": False, "message": text}
                return res
    except Exception as e:
        return {"success": False, "message": str(e)}

# ====== /pixurl command ======
@Client.on_message(filters.command("pixurl"))
async def pixurl_command_handler(client: Client, message: Message):
    text = message.text
    parts = text.split(" ")

    if len(parts) < 2:
        return await message.reply("❗ **Usage:** `/pixurl <url> [optional_filename]`")

    url = parts[1]
    custom_filename = parts[2] if len(parts) >= 3 else None

    await message.reply(f"🔗 **URL:** `{url}`\n📝 **Filename:** `{custom_filename or 'Default'}`")

    if await is_direct_download(url):
        status_msg = await message.reply("⬇️ **Downloading file...** Please wait.")
        dl_file = await dl(url=url, msg=status_msg, custom_filename=custom_filename)

        if dl_file and not "error" in dl_file:
            file_path = dl_file['file_path']
            file_name = dl_file['filename']

            await status_msg.edit_text("✅ **Download complete!**\n\n⬆️ Now uploading to PixelDrain...")

            result = await upload_to_pixeldrain(client, file_path, file_name, status_msg)

            if result.get("success"):
                file_id = result.get("id", "UNKNOWN")
                if file_id == "UNKNOWN":
                    await status_msg.edit_text("✅ **Upload complete!**\n⚠️ But couldn't fetch file ID.\nPlease check PixelDrain manually.")
                else:
                    await status_msg.edit_text(
                        f"✅ **Upload complete!**\n\n🔗 [PixelDrain Link](https://pixeldrain.com/u/{file_id})"
                    )
            else:
                await status_msg.edit_text(f"❌ **Upload failed:** `{result.get('message')}`")

            try:
                os.remove(file_path)
            except:
                pass
        else:
            await status_msg.edit_text(f"❌ **Download failed:** `{dl_file.get('error')}`")
    else:
        await message.reply("⚠️ **This command only supports direct download links.**")

# ====== /pix command (Reply to media) ======
@Client.on_message(filters.command("pix") & filters.reply)
async def pix_command_handler(client: Client, message: Message):
    media = message.reply_to_message

    if not (media.video or media.document or media.audio or media.voice):
        return await message.reply("❗ **Reply to a supported file:** video, document, audio, or voice.")

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
            f"doc_{random_str}.txt" if media.document else
            f"audio_{random_str}.mp3" if media.audio else
            "voice_note.ogg"
        )

    status = await message.reply(f"⬇️ **Downloading `{file_name}`...**")

    time_data = {"start": time.time(), "last_update": time.time()}

    try:
        file_path = await media.download(
            progress=lambda cur, tot: client.loop.create_task(
                progress_callback(cur, tot, status, time_data, "⬇️ Downloading")
            )
        )
    except Exception as e:
        return await status.edit_text(f"❌ **Download failed:** `{str(e)}`")

    await status.edit_text("✅ **Download complete!**\n\n⬆️ Uploading to PixelDrain...")

    result = await upload_to_pixeldrain(client, file_path, file_name, status)

    if result.get("success"):
        file_id = result.get("id", "UNKNOWN")
        if file_id == "UNKNOWN":
            await status.edit_text("✅ **Upload complete!**\n⚠️ But couldn't fetch file ID.\nCheck PixelDrain manually.")
        else:
            await status.edit_text(
                f"✅ **Upload complete!**\n\n🔗 [PixelDrain Link](https://pixeldrain.com/u/{file_id})"
            )
    else:
        await status.edit_text(f"❌ **Upload failed:** `{result.get('message')}`")

    try:
        os.remove(file_path)
    except:
        pass
