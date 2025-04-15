import os
import time
import asyncio
import subprocess
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# Store ongoing download sessions
active_sessions = {}

@Client.on_message(filters.command("bili") & filters.private)
async def bili_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Please provide a Bilibili video URL.\n\nUsage: `/bili <url>`", quote=True)

    url = message.command[1]
    user_id = message.from_user.id
    active_sessions[user_id] = {"message": None}

    await message.reply("Fetching available formats...", quote=True)

    # Get video format list using yt_dlp
    ydl_opts = {"quiet": True, "listformats": True, "skip_download": True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    try:
        info_dict = ydl.extract_info(url, download=False)
    except Exception as e:
        return await message.reply(f"Failed to fetch formats: `{str(e)}`")

    video_formats = [
        (f"{f['format_id']} - {f['format_note']} - {f.get('height', '?')}p - {round(f['filesize'] / 1024 / 1024, 1)}MB"
         if f.get('filesize') else f"{f['format_id']} - {f['format_note']} - {f.get('height', '?')}p")
        for f in info_dict["formats"]
        if f.get("vcodec", "none") != "none" and f.get("acodec", "none") == "none"
    ]

    buttons = [
        [InlineKeyboardButton(text=format_desc, callback_data=f"bili_{user_id}_{format_desc.split(' - ')[0]}")]
        for format_desc in video_formats[:10]
    ]

    await message.reply(
        "Select a video quality:",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )


@Client.on_callback_query(filters.regex(r"^bili_(\d+)_(\d+)$"))
async def bili_download(client, callback_query):
    user_id, format_id = callback_query.matches[0].groups()
    user_id = int(user_id)

    if callback_query.from_user.id != user_id:
        return await callback_query.answer("This is not your session.", show_alert=True)

    await callback_query.answer()
    await callback_query.message.edit_text("Starting download...")

    msg = await callback_query.message.reply("Preparing...", quote=True)
    active_sessions[user_id]["message"] = msg

    url = callback_query.message.reply_to_message.command[1]
    video_file = "video.mp4"
    audio_file = "audio.m4a"
    output_file = "merged.mp4"

    try:
        # Get best audio format
        ydl = yt_dlp.YoutubeDL({"quiet": True})
        info_dict = ydl.extract_info(url, download=False)
        audio_format_id = sorted(
            [f for f in info_dict["formats"] if f.get("acodec", "none") != "none" and f.get("vcodec") == "none"],
            key=lambda f: f.get("abr", 0),
            reverse=True
        )[0]["format_id"]

        # Download video
        await download_progress(url, format_id, video_file, msg, "Video")

        # Download audio
        await download_progress(url, audio_format_id, audio_file, msg, "Audio")

        # Merge with FFmpeg
        await merge_video_audio(video_file, audio_file, output_file, msg)

        # Upload to Telegram
        await upload_file(client, callback_query.message.chat.id, output_file, msg)

    except Exception as e:
        await msg.edit_text(f"Error: `{str(e)}`")

    finally:
        for f in [video_file, audio_file, output_file]:
            if os.path.exists(f):
                os.remove(f)


async def download_progress(url, format_id, filename, msg, label):
    start = time.time()

    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'quiet': True,
        'progress_hooks': [lambda d: asyncio.create_task(update_progress(d, msg, label, start))]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def update_progress(d, msg, label, start):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '').strip()
        total = d.get('_total_bytes_str', '')
        speed = d.get('_speed_str', '')
        eta = d.get('eta', '?')
        text = (
            f"**{label} Downloading...**\n"
            f"Progress: `{percent}`\n"
            f"Size: `{total}`\n"
            f"Speed: `{speed}`\n"
            f"ETA: `{eta}s`\n"
        )
        await msg.edit_text(text)

async def merge_video_audio(video_file, audio_file, output_file, msg):
    await msg.edit_text("Merging video and audio with FFmpeg...")

    command = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-map", "0:v?", "-map", "1:a?",
        "-c:v", "copy", "-c:a", "aac",
        "-shortest", output_file
    ]

    process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        await asyncio.sleep(5)
        if process.returncode is not None:
            break
        await msg.edit_text("Still merging...")

    await process.communicate()
    await msg.edit_text("Merge complete!")


async def upload_file(client, chat_id, filepath, msg):
    await msg.edit_text("Uploading to Telegram...")
    file_size = os.path.getsize(filepath)
    sent = await client.send_document(
        chat_id=chat_id,
        document=filepath,
        caption="Here's your merged video.",
        progress=upload_progress,
        progress_args=(msg, time.time(), file_size)
    )
    await msg.delete()

async def upload_progress(current, total, msg, start_time, file_size):
    percent = (current / total) * 100
    elapsed = time.time() - start_time
    speed = current / elapsed if elapsed > 0 else 0
    remaining = (total - current) / speed if speed > 0 else 0
    text = (
        f"**Uploading...**\n"
        f"Progress: `{percent:.2f}%`\n"
        f"Uploaded: `{current / 1024 / 1024:.2f}MB / {total / 1024 / 1024:.2f}MB`\n"
        f"Speed: `{speed / 1024:.2f} KB/s`\n"
        f"ETA: `{int(remaining)}s`\n"
    )
    await msg.edit_text(text)
