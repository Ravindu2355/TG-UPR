import os
import subprocess
import requests
import base64
import time
import re
import ffmpeg
import asyncio
from config import Config
from moviepy.editor import VideoFileClip

last_msg = ""
last_upt = 0


def get_media_info(file_path, thumb_path=None):
    try:
        probe = ffmpeg.probe(file_path)
        duration = int(float(probe["format"]["duration"])) if "duration" in probe["format"] else 0
        if not thumb_path:
            thumb_path = f"{file_path}.jpg"
            (
                ffmpeg.input(file_path, ss=1)
                .output(thumb_path, vframes=1)
                .run(capture_stdout=True, capture_stderr=True)
            )
        return duration, thumb_path
    except Exception as e:
        print(f"FFmpeg Error: {e}")
        return 0, None


async def u_msg(msg, txt):
    """Update Telegram message every 10 seconds to avoid spam."""
    global last_msg, last_upt
    if txt != last_msg and (time.time() - last_upt) >= 10:
        await msg.edit_text(txt)
        last_msg = txt
        last_upt = time.time()


async def convert_to_hls2(input_video_path, output_dir, msg, threads=None, extra_args=None):
    """Convert video to HLS with custom threads and additional FFmpeg arguments."""
    await msg.edit_text("Starting conversion...")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get video duration
    total_duration, thumb = get_media_info(input_video_path)
    if not total_duration:
        await msg.edit_text("Error: Unable to determine video duration.")
        return None, None

    output_m3u8 = os.path.join(output_dir, "output.m3u8")
    
    # Base FFmpeg command
    cmd = [
        "ffmpeg", "-i", input_video_path,
        "-preset", "ultrafast", "-g", "48", "-sc_threshold", "0",
        "-hls_time", "10", "-hls_list_size", "0",
        "-hls_segment_filename", os.path.join(output_dir, "segment_%03d.ts"),
        output_m3u8
    ]
    
    # Add custom threads argument if specified
    #if threads:
        #cmd.insert(2, f"-threads {threads}")
    if threads:
        cmd.extend(["-threads", str(threads)])
    # Add any additional arguments provided by the user
    if extra_args:
        cmd.extend(extra_args)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        output = await process.stderr.readline()
        if not output:
            break

        output = output.decode().strip()
        match = re.search(r"time=(\d+):(\d+):([\d.]+)", output)
        if match:
            hours, minutes, seconds = map(float, match.groups())
            elapsed_seconds = hours * 3600 + minutes * 60 + seconds
            percentage = (elapsed_seconds / total_duration) * 100
            progress_msg = f"FFmpeg Progress: {percentage:.2f}% complete"
            await u_msg(msg, progress_msg)

    await process.wait()
    await msg.edit_text("Conversion completed!")
    return output_m3u8, output_dir

async def convert_to_hls(input_video_path, output_dir, msg):
    """Convert video to HLS and show FFmpeg progress in real-time."""
    await msg.edit_text("Starting conversion...")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get video duration
    total_duration, thumb = get_media_info(input_video_path)
    if not total_duration:
        await msg.edit_text("Error: Unable to determine video duration.")
        return None, None

    output_m3u8 = os.path.join(output_dir, "output.m3u8")
    cmd = [
        "ffmpeg", "-i", input_video_path,
        "-preset", "ultrafast", "-g", "48", "-sc_threshold", "0",
        "-hls_time", "10", "-hls_list_size", "0",
        "-hls_segment_filename", os.path.join(output_dir, "segment_%03d.ts"),
        output_m3u8
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        output = await process.stderr.readline()
        if not output:
            break

        output = output.decode().strip()
        match = re.search(r"time=(\d+):(\d+):([\d.]+)", output)
        if match:
            hours, minutes, seconds = map(float, match.groups())
            elapsed_seconds = hours * 3600 + minutes * 60 + seconds
            percentage = (elapsed_seconds / total_duration) * 100
            progress_msg = f"FFmpeg Progress: {percentage:.2f}% complete"
            await u_msg(msg, progress_msg)

    await process.wait()
    await msg.edit_text("Conversion completed!")
    return output_m3u8, output_dir

#old up
def uypload_to_github(file_path, upload_dir):
    """Upload a file to GitHub with progress tracking."""
    url = f"https://api.github.com/repos/{Config.GIT_UN}/{Config.GIT_REPO}/contents/{upload_dir}/{os.path.basename(file_path)}"

    with open(file_path, "rb") as file:
        content = file.read()

    content_b64 = base64.b64encode(content).decode("utf-8")
    payload = {
        "message": f"Upload {os.path.basename(file_path)}",
        "branch": Config.GIT_BRANCH,
        "content": content_b64
    }

    headers = {
        "accept": "application/vnd.github+json",
        "Authorization": f"token {Config.GIT_TK}",
        'X-GitHub-Api-Version': '2022-11-28'
    }

    response = requests.put(url, json=payload, headers=headers)

    if response.status_code == 201:
        print(f"Successfully uploaded: {file_path}")
        return f"Uploaded {os.path.basename(file_path)}"
    else:
        error_msg = f"Failed to upload {file_path}. Error {response.status_code}: {response.text}"
        print(error_msg)
        return {"error": error_msg}


def upload_to_github(file_path, upload_dir, max_retries=3):
    """Upload a file to GitHub with retry mechanism for error 500."""
    url = f"https://api.github.com/repos/{Config.GIT_UN}/{Config.GIT_REPO}/contents/{upload_dir}/{os.path.basename(file_path)}"

    with open(file_path, "rb") as file:
        content = file.read()

    content_b64 = base64.b64encode(content).decode("utf-8")
    payload = {
        "message": f"Upload {os.path.basename(file_path)}",
        "branch": Config.GIT_BRANCH,
        "content": content_b64
    }

    headers = {
        "accept": "application/vnd.github+json",
        "Authorization": f"token {Config.GIT_TK}",
        'X-GitHub-Api-Version': '2022-11-28'
    }

    for attempt in range(1, max_retries + 1):
        response = requests.put(url, json=payload, headers=headers)

        if response.status_code == 201:
            print(f"Successfully uploaded: {file_path}")
            return f"Uploaded {os.path.basename(file_path)}"
        
        elif response.status_code == 500:
            print(f"GitHub 500 Error: Retrying {attempt}/{max_retries}...")
            time.sleep(2 ** attempt)  # Exponential backoff (2s, 4s, 8s)
        
        else:
            error_msg = f"Failed to upload {file_path}. Error {response.status_code}: {response.text}"
            print(error_msg)
            return {"error": error_msg}

    return {"error": f"Failed to upload {file_path} after {max_retries} retries due to repeated 500 errors."}
    

def delete_dir(directory):
    """Delete directory and its contents."""
    if os.path.exists(directory):
        for root, _, files in os.walk(directory, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
        os.rmdir(directory)
        print(f"Deleted directory: {directory}")


async def to_git(video_path, msg, trs=None, extra=None):
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = f"{video_name}"

    #await msg.reply(f"Processing: {video_path}")
    # Convert video to HLS
    if trs:
        if extra:
            m3u8_file, ts_dir = await convert_to_hls2(video_path, video_dir, msg, threads=trs, extra_args=extra)
        else:
            m3u8_file, ts_dir = await convert_to_hls2(video_path, video_dir, msg, threads=trs)
    else:
        if extra:
            m3u8_file, ts_dir = await convert_to_hls2(video_path, video_dir, msg, extra_args=extra)
        else:
            m3u8_file, ts_dir = await convert_to_hls(video_path, video_dir, msg)
    if not m3u8_file:
        return

    # Upload m3u8 file
    upload_result = upload_to_github(m3u8_file, video_name)
    if "error" in upload_result:
        await msg.edit_text(f'{upload_result["error"]}\n{os.path.exists(m3u8_file)}')
        return

    # Upload .ts segments with progress
    ts_files = [f for f in os.listdir(ts_dir) if f.endswith(".ts")]
    total_segments = len(ts_files)
    uploaded_segments = 0

    for ts_file in ts_files:
        ts_file_path = os.path.join(ts_dir, ts_file)
        upload_result = upload_to_github(ts_file_path, video_name)

        if "error" in upload_result:
            await msg.edit_text(upload_result["error"])
            break

        uploaded_segments += 1
        progress_percentage = (uploaded_segments / total_segments) * 100
        progress_msg = f"Uploading... {uploaded_segments}/{total_segments} files ({progress_percentage:.2f}%)"
        await u_msg(msg, progress_msg)
        await asyncio.sleep(0.2)

    # Cleanup
    #lurl = f"https://github.com/{Config.GIT_UN}/{Config.GIT_REPO}/blob/{Config.GIT_BRANCH}/{m3u8_file}"
    lurl = f"https://raw.githubusercontent.com/{Config.GIT_UN}/{Config.GIT_REPO}/refs/heads/{Config.GIT_BRANCH}/{m3u8_file}"
    delete_dir(video_dir)
    await msg.edit_text(f"Upload completed!\n\nUrl: {lurl}")
    if os.path.exists(video_path):
        os.remove(video_path)

#async def to_git(file_path, msg):
    #await main(file_path, msg)
