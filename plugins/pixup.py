import os
import time
import random
import base64
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from Func.downloader import dl
from Func.utils import is_direct_download

PIXELDRAIN_API_KEY = Config.PixKey

# ================= Progress Utility ===================
async def progress_callback(current, total, message: Message, start_data, label="Progress"):
    now = time.time()
    if now - start_data["last_update"] >= 5:
        percent = current * 100 / total
        speed = current / (now - start_data["start"] + 1)
        eta = (total - current) / speed if speed > 0 else 0
        try:
            await message.edit_text(
                f"**{label}...**\n"
                f"📊 `{percent:.2f}%` done\n"
                f"⚡ Speed: `{speed / 1024:.2f} KB/s`\n"
                f"⏳ ETA: `{int(eta)}s`"
            )
            start_data["last_update"] = now
        except Exception:
            pass

# ============== Upload to PixelDrain ==================
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
                return await resp.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============ /pixurl command =========================
@Client.on_message(filters.command("pixurl"))
async def pixurl_command_handler(client: Client, message: Message):
    parts = message.text.split(" ")
    if len(parts) < 2:
        return await message.reply("❗ **Usage:** `/pixurl <url> [custom_filename]`")

    url = parts[1]
    new_name = parts[2] if len(parts) >= 3 else None
    msg = await message.reply("🔍 Checking URL...")

    if await is_direct_download(url):
        dl_msg = await msg.edit("⏬ Downloading file...")
        dl_file = await dl(url=url, msg=dl_msg, custom_filename=new_name)

        if dl_file and not "error" in dl_file:
            file_path = dl_file['file_path']
            file_name = dl_file['filename']
            await dl_msg.edit("✅ Download complete!\n\n⬆️ Uploading to PixelDrain...")
            res = await upload_to_pixeldrain(client, file_path, file_name, dl_msg)

            if res.get("success"):
                await dl_msg.edit(f"✅ **Upload complete!**\n\n🔗 [PixelDrain Link](https://pixeldrain.com/u/{res['id']})")
            else:
                await dl_msg.edit(f"❌ Upload failed: `{res.get('message')}`")
            try:
                os.remove(file_path)
            except:
                pass
        else:
            await dl_msg.edit(f"❌ Download error: `{dl_file.get('error')}`")
    else:
        await msg.edit("❗ This command only supports direct download links.")

# ============ /pix reply command ======================
@Client.on_message(filters.command("pix") & filters.reply)
async def pix_command_handler(client: Client, message: Message):
    media = message.reply_to_message

    if not (media.video or media.document or media.audio or media.voice):
        return await message.reply("❗ Reply to a supported file (video, document, audio, or voice).")

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

    status = await message.reply(f"⏬ Downloading `{file_name}`...")
    time_data = {"start": time.time(), "last_update": time.time()}

    try:
        file_path = await media.download(
            progress=lambda cur, tot: client.loop.create_task(
                progress_callback(cur, tot, status, time_data, "⬇️ Downloading")
            )
        )
    except Exception as e:
        return await status.edit(f"❌ Download failed: `{str(e)}`")

    await status.edit("✅ Download complete!\n\n⬆️ Uploading to PixelDrain...")

    result = await upload_to_pixeldrain(client, file_path, file_name, status)

    if result.get("success"):
        await status.edit(f"✅ **Upload complete!**\n\n🔗 [PixelDrain Link](https://pixeldrain.com/u/{result['id']})")
    else:
        await status.edit(f"❌ Upload failed: `{result.get('message')}`")

    try:
        os.remove(file_path)
    except:
        pass
