import re, os, asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from plugins.authers import is_authorized
from plugins.tgdw import download_file
from plugins.tgup import upload_file
from plugins.git_up import get_media_info

download_dir = "/forH264"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)


async def convert_to_h264(input_video_path, output_dir, msg):
    """
    Convert video (H.265 / MKV / etc.) to H.264 MP4
    with real-time FFmpeg progress updates.
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

        # VIDEO → H.264
        "-c:v", "libx264",
        "-preset", "ultrafast",     # very fast, low CPU
        "-profile:v", "main",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",      # required for compatibility
        "-movflags", "+faststart",

        # AUDIO (copy if possible, else AAC)
        "-c:a", "aac",
        "-b:a", "128k",

        output_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )

    last_percent = 0

    while True:
        line = await process.stderr.readline()
        if not line:
            break

        text = line.decode(errors="ignore")

        match = re.search(r"time=(\d+):(\d+):([\d.]+)", text)
        if match:
            h, m, s = map(float, match.groups())
            elapsed = h * 3600 + m * 60 + s
            percent = min((elapsed / total_duration) * 100, 100)

            # update only if changed (prevents flood)
            if int(percent) != last_percent:
                last_percent = int(percent)
                await u_msg(
                    msg,
                    f"🎬 H.264 Converting...\n"
                    f"📊 Progress: {percent:.2f}%"
                )

    await process.wait()

    if not os.path.exists(output_file):
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
        await message.reply("**❌️You are not authorized to use me!❌️**")
        return

    v_msg = message.reply_to_message

    # Fallback filename safety
    if v_msg.video.file_name:
        input_name = v_msg.video.file_name
    else:
        input_name = f"{v_msg.video.file_id}.mp4"

    input_path = os.path.join(download_dir, input_name)

    msg = await message.reply("⬇️ Downloading video...")

    # Download video
    file_path = await download_file(client, v_msg, download_dir, msg)
    if not file_path or not os.path.exists(file_path):
        await msg.edit_text("❌ Download failed.")
        return

    # Convert to H.264
    output_file = await convert_to_h264(
        input_video_path=file_path,
        output_dir=download_dir,
        msg=msg
    )

    # Remove original file after conversion
    try:
        os.remove(file_path)
    except Exception:
        pass

    if not output_file or not os.path.exists(output_file):
        await msg.edit_text("❌ H.264 conversion failed.")
        return

    # Upload converted file
    await upload_file(
        client=client,
        chat_id=message.chat.id,
        file_path=output_file,
        msg=msg,
        as_document=False  # uploads as streamable video
    )
