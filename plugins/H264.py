import re
import os
import asyncio
import time

from pyrogram import Client, filters
from pyrogram.types import Message

from plugins.authers import is_authorized
from plugins.tgdw import download_file
from plugins.tgup import upload_file
from plugins.git_up import get_media_info

download_dir = "/forH264"
os.makedirs(download_dir, exist_ok=True)


async def safe_edit(msg: Message, text: str, delay=5):
    """
    Edit message safely (prevents FloodWait & edit spam)
    """
    now = time.time()
    last = getattr(msg, "_last_edit", 0)

    if now - last >= delay:
        try:
            await msg.edit_text(text)
            msg._last_edit = now
        except Exception:
            pass


async def convert_to_h264(input_video_path, output_dir, msg):
    """
    Convert video to H.264 MP4 with SAFE FFmpeg progress parsing
    """

    await msg.edit_text("🔄 Starting H.264 conversion...")

    os.makedirs(output_dir, exist_ok=True)

    total_duration, thumb = get_media_info(input_video_path)
    if not total_duration:
        await msg.edit_text("❌ Unable to determine video duration.")
        return None

    video_name = os.path.splitext(os.path.basename(input_video_path))[0]
    output_file = os.path.join(output_dir, f"{video_name}_h264.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video_path,

        # Video
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-profile:v", "main",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",

        # Audio
        "-c:a", "aac",
        "-b:a", "128k",

        # Progress
        "-progress", "pipe:1",
        "-nostats",

        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    last_percent = -1

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        text = line.decode(errors="ignore").strip()

        if text.startswith("out_time_ms="):
            out_time_ms = int(text.split("=")[1])
            elapsed = out_time_ms / 1_000_000
            percent = min(int((elapsed / total_duration) * 100), 100)

            if percent != last_percent:
                last_percent = percent
                await safe_edit(
                    msg,
                    f"🎬 H.264 Converting...\n"
                    f"📊 Progress: {percent}%"
                )

    await process.wait()

    if process.returncode != 0 or not os.path.exists(output_file):
        await msg.edit_text("❌ Conversion failed.")
        return None

    await msg.edit_text("✅ H.264 conversion completed!")
    return output_file


@Client.on_message(filters.command("h264"))
async def h264_convert(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply("❌ Reply to a video with:\n`/h264`")
        return

    if not is_authorized(message.chat.id):
        await message.reply("❌ You are not authorized to use this bot.")
        return

    v_msg = message.reply_to_message

    input_name = (
        v_msg.video.file_name
        if v_msg.video.file_name
        else f"{v_msg.video.file_id}.mp4"
    )

    msg = await message.reply("⬇️ Downloading video...")

    file_path = await download_file(client, v_msg, download_dir, msg)
    if not file_path or not os.path.exists(file_path):
        await msg.edit_text("❌ Download failed.")
        return

    output_file = await convert_to_h264(
        input_video_path=file_path,
        output_dir=download_dir,
        msg=msg
    )

    try:
        os.remove(file_path)
    except Exception:
        pass

    if not output_file:
        await msg.edit_text("❌ H.264 conversion failed.")
        return

    await upload_file(
        client=client,
        chat_id=message.chat.id,
        file_path=output_file,
        msg=msg,
        as_document=False
        )
