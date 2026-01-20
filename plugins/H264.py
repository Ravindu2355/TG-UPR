import os
import re
import asyncio

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
