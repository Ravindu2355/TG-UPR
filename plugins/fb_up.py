import os
import time
import math
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
async def progress_update(uploaded, total, msg, start_data, label="⬆️ Uploading"):
    now = time.time()
    if now - start_data["last"] >= 4:
        percent = uploaded * 100 / total
        speed = uploaded / (now - start_data["start"] + 1)
        eta = (total - uploaded) / speed if speed > 0 else 0

        await safe_edit(
            msg,
            f"{label}\n"
            f"**{percent:.2f}%** completed\n"
            f"⚡ Speed: `{speed / 1024 / 1024:.2f} MB/s`\n"
            f"⏳ ETA: `{int(eta)}s`"
        )
        start_data["last"] = now


# ===== FACEBOOK UPLOAD CORE =====
async def upload_to_facebook(file_path, title, desc, published, msg: Message):
    token = Config.FB_PAGE_TOKEN
    page_id = Config.FB_PAGE_ID

    size = os.path.getsize(file_path)
    time_data = {"start": time.time(), "last": time.time()}
    uploaded = 0

    async with aiohttp.ClientSession() as session:

        # ===== START =====
        async with session.post(
            f"{GRAPH_URL}/{page_id}/videos",
            params={
                "access_token": token,
                "upload_phase": "start",
                "file_size": size,
                "published": str(published).lower()
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
                    f"{GRAPH_URL}/{page_id}/videos",
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

                await progress_update(uploaded, size, msg, time_data)

        # ===== FINISH =====
        async with session.post(
            f"{GRAPH_URL}/{page_id}/videos",
            params={
                "access_token": token,
                "upload_phase": "finish",
                "upload_session_id": session_id,
                "title": title,
                "description": desc,
                "published": str(published).lower()
            }
        ) as r:
            finish_res = await r.json()

        if "error" in finish_res:
            raise Exception(finish_res["error"]["message"])

        return finish_res


# ===== COMMAND HANDLER (COMMON) =====
async def fb_handler(client: Client, message: Message, published: bool):
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply("❗ Reply to a **video**.")

    parts = message.text.split(" ", 2)
    title = parts[1] if len(parts) > 1 else "Uploaded via Bot"
    desc = parts[2] if len(parts) > 2 else ""

    status = await message.reply("⬇️ **Downloading video...**")
    start_data = {"start": time.time(), "last": time.time()}

    try:
        file_path = await message.reply_to_message.download(
            progress=lambda c, t: client.loop.create_task(
                progress_update(c, t, status, start_data, "⬇️ Downloading")
            )
        )
    except Exception as e:
        return await safe_edit(status, f"❌ Download failed: `{e}`")

    await safe_edit(status, "✅ Download complete!\n\n⬆️ Uploading to Facebook...")

    try:
        res = await upload_to_facebook(file_path, title, desc, published, status)
        video_id = res.get("video_id")

        visibility = "Public" if published else "Unlisted"
        await safe_edit(
            status,
            f"✅ **Upload complete!**\n"
            f"🔓 Visibility: **{visibility}**\n"
            f"🔗 https://www.facebook.com/{Config.FB_PAGE_ID}/videos/{video_id}/"
        )
    except Exception as e:
        await safe_edit(status, f"❌ Upload failed:\n`{str(e)}`")

    try:
        os.remove(file_path)
    except:
        pass


# ===== COMMANDS =====
@Client.on_message(filters.command("fb_public") & filters.reply)
async def fb_public(client: Client, message: Message):
    await fb_handler(client, message, published=True)


@Client.on_message(filters.command("fb_unlisted") & filters.reply)
async def fb_unlisted(client: Client, message: Message):
    await fb_handler(client, message, published=False)
