import os
import time
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from config import Config

GRAPH_URL = "https://graph.facebook.com/v19.0"
CHUNK_SIZE = 1024 * 1024 * 8  # 8MB


# ===== SAFE MESSAGE EDIT =====
async def safe_edit(msg: Message, text: str):
    try:
        await msg.edit_text(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await msg.edit_text(text)
        except:
            pass
    except:
        pass


# ===== PROGRESS UPDATE =====
async def progress_update(done, total, msg, data, label):
    now = time.time()
    if now - data["last"] >= 4:
        percent = done * 100 / total
        speed = done / (now - data["start"] + 1)
        eta = (total - done) / speed if speed > 0 else 0

        await safe_edit(
            msg,
            f"{label}\n"
            f"**{percent:.2f}%** completed\n"
            f"⚡ `{speed/1024/1024:.2f} MB/s`\n"
            f"⏳ ETA: `{int(eta)}s`"
        )
        data["last"] = now


# ===== FACEBOOK GROUP UPLOAD CORE =====
async def upload_to_fb_group(file_path, title, desc, msg: Message):
    token = Config.FB_USER_TOKEN
    group_id = Config.FB_GROUP_ID

    size = os.path.getsize(file_path)
    uploaded = 0
    tdata = {"start": time.time(), "last": time.time()}

    async with aiohttp.ClientSession() as session:

        # ===== START =====
        async with session.post(
            f"{GRAPH_URL}/{group_id}/videos",
            params={
                "access_token": token,
                "upload_phase": "start",
                "file_size": size
            }
        ) as r:
            start_res = await r.json()

        if "error" in start_res:
            raise Exception(start_res["error"]["message"])

        session_id = start_res["upload_session_id"]
        start_offset = int(start_res["start_offset"])
        end_offset = int(start_res["end_offset"])

        # ===== TRANSFER =====
        with open(file_path, "rb") as f:
            while start_offset < end_offset:
                f.seek(start_offset)
                chunk = f.read(CHUNK_SIZE)

                data = aiohttp.FormData()
                data.add_field("video_file_chunk", chunk)

                async with session.post(
                    f"{GRAPH_URL}/{group_id}/videos",
                    params={
                        "access_token": token,
                        "upload_phase": "transfer",
                        "upload_session_id": session_id,
                        "start_offset": start_offset
                    },
                    data=data
                ) as r:
                    res = await r.json()

                if "error" in res:
                    raise Exception(res["error"]["message"])

                uploaded += len(chunk)
                start_offset = int(res["start_offset"])
                end_offset = int(res["end_offset"])

                await progress_update(uploaded, size, msg, tdata, "⬆️ Uploading")

        # ===== FINISH =====
        async with session.post(
            f"{GRAPH_URL}/{group_id}/videos",
            params={
                "access_token": token,
                "upload_phase": "finish",
                "upload_session_id": session_id,
                "title": title,
                "description": desc
            }
        ) as r:
            finish_res = await r.json()

        if "error" in finish_res:
            raise Exception(finish_res["error"]["message"])

        return finish_res


# ===== COMMAND HANDLER =====
async def fb_group_handler(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("❗ Reply to a **video**.")

    parts = message.text.split(" ", 2)
    title = parts[1] if len(parts) > 1 else "Uploaded via Bot"
    desc = parts[2] if len(parts) > 2 else ""

    status = await message.reply("⬇️ **Downloading video...**")
    ddata = {"start": time.time(), "last": time.time()}

    try:
        file_path = await message.reply_to_message.download(
            progress=lambda c, t: client.loop.create_task(
                progress_update(c, t, status, ddata, "⬇️ Downloading")
            )
        )
    except Exception as e:
        return await safe_edit(status, f"❌ Download failed:\n`{e}`")

    await safe_edit(status, "✅ Download complete!\n\n⬆️ Uploading to Facebook Group...")

    try:
        res = await upload_to_fb_group(file_path, title, desc, status)
        video_id = res.get("video_id")

        await safe_edit(
            status,
            f"✅ **Upload complete!**\n"
            f"👥 Group Video\n"
            f"🔗 https://www.facebook.com/{video_id}"
        )
    except Exception as e:
        await safe_edit(status, f"❌ Upload failed:\n`{e}`")

    try:
        os.remove(file_path)
    except:
        pass


# ===== COMMAND =====
@Client.on_message(filters.command("fb_group") & filters.reply)
async def fb_group(client: Client, message: Message):
    await fb_group_handler(client, message)


