import os
import time
import json
import asyncio
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from config import Config


GRAPH_URL = "https://graph.facebook.com/v19.0"
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

FB_SETTINGS_FILE = "fb_settings.json"


# =========================================================
# SETTINGS DATABASE
# =========================================================

def load_fb_settings():
    try:
        if os.path.exists(FB_SETTINGS_FILE):
            with open(FB_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, dict):
                    return data
    except Exception as e:
        print(f"FB settings database error: {e}")

    return {}


def save_fb_settings(data):
    temp_file = FB_SETTINGS_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(temp_file, FB_SETTINGS_FILE)


def get_fb_settings(user_id):
    data = load_fb_settings()

    user_settings = data.get(str(user_id), {})

    return {
        "token": user_settings.get("token") or Config.FB_PAGE_TOKEN,
        "page_id": user_settings.get("page_id") or Config.FB_PAGE_ID,
        "custom_token": bool(user_settings.get("token")),
        "custom_page": bool(user_settings.get("page_id"))
    }


def set_fb_token(user_id, token):
    data = load_fb_settings()

    user_settings = data.setdefault(str(user_id), {})
    user_settings["token"] = token

    save_fb_settings(data)


def set_fb_page(user_id, page_id):
    data = load_fb_settings()

    user_settings = data.setdefault(str(user_id), {})
    user_settings["page_id"] = page_id

    save_fb_settings(data)


def reset_fb_settings(user_id):
    data = load_fb_settings()

    data.pop(str(user_id), None)

    save_fb_settings(data)


# =========================================================
# SAFE MESSAGE EDIT
# =========================================================

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


# =========================================================
# PROGRESS UPDATE
# =========================================================

async def progress_update(
    uploaded,
    total,
    msg,
    start_data,
    label="⬆️ Uploading"
):

    now = time.time()

    if now - start_data["last"] >= 4:

        percent = uploaded * 100 / total if total else 0

        speed = uploaded / (now - start_data["start"] + 1)

        eta = (total - uploaded) / speed if speed > 0 else 0

        await safe_edit(
            msg,
            f"{label}\n\n"
            f"**{percent:.2f}%** completed\n"
            f"📦 `{uploaded / 1024 / 1024:.2f} / "
            f"{total / 1024 / 1024:.2f} MB`\n"
            f"⚡ Speed: `{speed / 1024 / 1024:.2f} MB/s`\n"
            f"⏳ ETA: `{int(eta)}s`"
        )

        start_data["last"] = now


# =========================================================
# FACEBOOK UPLOAD CORE
# =========================================================

async def upload_to_facebook(
    file_path,
    title,
    desc,
    published,
    msg,
    token,
    page_id
):

    size = os.path.getsize(file_path)

    time_data = {
        "start": time.time(),
        "last": time.time()
    }

    uploaded = 0

    stres = {}

    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        # =================================================
        # START
        # =================================================

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

            stres = start_res

        if "error" in start_res:

            raise Exception(
                start_res["error"].get("message", "Start failed")
            )

        session_id = start_res["upload_session_id"]

        start_offset = int(start_res["start_offset"])

        end_offset = int(start_res["end_offset"])

        # =================================================
        # TRANSFER
        # =================================================

        with open(file_path, "rb") as f:

            while start_offset < end_offset:

                f.seek(start_offset)

                chunk = f.read(CHUNK_SIZE)

                if not chunk:
                    break

                data = aiohttp.FormData()

                data.add_field(
                    "video_file_chunk",
                    chunk,
                    filename="video.mp4",
                    content_type="application/octet-stream"
                )

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

                    raise Exception(
                        res["error"].get("message", "Transfer failed")
                    )

                uploaded += len(chunk)

                start_offset = int(res["start_offset"])

                end_offset = int(res["end_offset"])

                await progress_update(
                    uploaded,
                    size,
                    msg,
                    time_data
                )

        # =================================================
        # FINISH
        # =================================================

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

            raise Exception(
                finish_res["error"].get("message", "Finish failed")
            )

        if not finish_res.get("video_id"):

            return stres

        return finish_res


# =========================================================
# COMMON FB HANDLER
# =========================================================

async def fb_handler(
    client: Client,
    message: Message,
    published: bool
):

    if not message.reply_to_message or not message.reply_to_message.video:

        return await message.reply(
            "❗ Reply to a **video** with this command."
        )

    user_id = message.from_user.id

    settings = get_fb_settings(user_id)

    token = settings["token"]

    page_id = settings["page_id"]

    if not token or not page_id:

        return await message.reply(
            "❌ Facebook configuration missing!\n\n"
            "Set your Facebook token and Page ID first:\n\n"
            "`/fb_settoken YOUR_ACCESS_TOKEN`\n"
            "`/fb_setpage YOUR_PAGE_ID`"
        )

    # Parse command

    parts = message.text.split(" ", 2)

    title = parts[1] if len(parts) > 1 else "Uploaded via Bot"

    desc = parts[2] if len(parts) > 2 else ""

    status = await message.reply(
        "⬇️ **Downloading video...**"
    )

    start_data = {
        "start": time.time(),
        "last": time.time()
    }

    file_path = None

    try:

        file_path = await message.reply_to_message.download(
            progress=lambda c, t: client.loop.create_task(
                progress_update(
                    c,
                    t,
                    status,
                    start_data,
                    "⬇️ Downloading"
                )
            )
        )

    except Exception as e:

        return await safe_edit(
            status,
            f"❌ Download failed:\n`{e}`"
        )

    await safe_edit(
        status,
        "✅ Download complete!\n\n"
        "⬆️ Uploading to Facebook..."
    )

    try:

        res = await upload_to_facebook(
            file_path=file_path,
            title=title,
            desc=desc,
            published=published,
            msg=status,
            token=token,
            page_id=page_id
        )

        video_id = res.get("video_id")

        if not video_id:

            return await safe_edit(
                status,
                "⚠️ Upload finished, but Facebook didn't return a video ID.\n\n"
                f"Response:\n`{res}`"
            )

        visibility = "Public" if published else "Unpublished"

        await safe_edit(
            status,
            f"✅ **Facebook Upload Complete!**\n\n"
            f"📌 Title: `{title}`\n"
            f"🔓 Visibility: **{visibility}**\n"
            f"🆔 Video ID: `{video_id}`\n\n"
            f"🔗 https://www.facebook.com/{page_id}/videos/{video_id}/"
        )

    except Exception as e:

        await safe_edit(
            status,
            f"❌ **Upload failed!**\n\n"
            f"`{str(e)}`"
        )

    finally:

        if file_path:

            try:
                os.remove(file_path)
            except:
                pass


# =========================================================
# SET FACEBOOK TOKEN
# =========================================================

@Client.on_message(filters.command("fb_settoken"))
async def fb_settoken(client, message):

    if not message.from_user:
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:

        return await message.reply(
            "❗ **Usage:**\n"
            "`/fb_settoken YOUR_ACCESS_TOKEN`"
        )

    token = parts[1].strip()

    set_fb_token(
        message.from_user.id,
        token
    )

    await message.reply(
        "✅ **Facebook Access Token Updated!**\n\n"
        "Your custom token has been saved."
    )


# =========================================================
# SET FACEBOOK PAGE ID
# =========================================================

@Client.on_message(filters.command("fb_setpage"))
async def fb_setpage(client, message):

    if not message.from_user:
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:

        return await message.reply(
            "❗ **Usage:**\n"
            "`/fb_setpage YOUR_PAGE_ID`"
        )

    page_id = parts[1].strip()

    set_fb_page(
        message.from_user.id,
        page_id
    )

    await message.reply(
        "✅ **Facebook Page ID Updated!**\n\n"
        f"🆔 Page ID: `{page_id}`"
    )


# =========================================================
# FB SETTINGS
# =========================================================

@Client.on_message(filters.command("fb_settings"))
async def fb_settings(client, message):

    if not message.from_user:
        return

    settings = get_fb_settings(message.from_user.id)

    token = settings["token"]

    page_id = settings["page_id"]

    # Don't expose the full token

    if token:

        token_display = (
            token[:8] + "..." + token[-5:]
            if len(token) > 15
            else "Configured"
        )

    else:

        token_display = "❌ Not configured"

    if page_id:

        page_display = page_id

    else:

        page_display = "❌ Not configured"

    await message.reply(
        "⚙️ **Facebook Settings**\n\n"
        f"🔑 Token: `{token_display}`\n"
        f"🆔 Page ID: `{page_display}`\n\n"
        f"🔑 Custom token: "
        f"{'✅' if settings['custom_token'] else '❌ Default'}\n"
        f"🆔 Custom Page ID: "
        f"{'✅' if settings['custom_page'] else '❌ Default'}"
    )


# =========================================================
# RESET SETTINGS
# =========================================================

@Client.on_message(filters.command("fb_reset"))
async def fb_reset(client, message):

    if not message.from_user:
        return

    reset_fb_settings(
        message.from_user.id
    )

    await message.reply(
        "♻️ **Facebook settings reset!**\n\n"
        "Your custom Token and Page ID have been removed.\n"
        "The bot will now use the default values from `Config`."
    )


# =========================================================
# PUBLIC UPLOAD
# =========================================================

@Client.on_message(filters.command("fb_public") & filters.reply)
async def fb_public(client, message):

    await fb_handler(
        client,
        message,
        published=True
    )


# =========================================================
# UNPUBLISHED UPLOAD
# =========================================================

@Client.on_message(filters.command("fb_unlisted") & filters.reply)
async def fb_unlisted(client, message):

    await fb_handler(
        client,
        message,
        published=False
             )
