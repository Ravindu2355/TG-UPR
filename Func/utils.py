import os, re
import time
import requests
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from globals import AuthU
import urllib.parse
import aiohttp
from log import logger as lg


def url_decode(encoded_string):
    return urllib.parse.unquote(encoded_string)

def url_encode(string):
    return urllib.parse.quote(string)

def mention_user(message:Message):
    user = message.from_user
    user_name = user.first_name
    user_id = user.id
    mention = f"[{user_name}](tg://user?id={user_id})"
    return mention

async def get_tg_filename(message:Message):
    if message.video:
        file_name = message.video.file_name
    elif message.document:
        file_name = message.document.file_name

    if not file_name:
        file_name = f"video_{time.time()}.mp4"
    # Reply with the file name
    return file_name

# Generate thumbnail using ffmpeg
"""
def generate_thumbnail(video_path, thumb_path, time_stamp="00:00:05"):
    command = [
        "ffmpeg", "-i", video_path, "-ss", time_stamp, "-vframes", "1", thumb_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
"""

def generate_thumbnail(video_path, thumb_path):
    # Get video duration using ffprobe
    command = [
        "ffprobe", "-i", video_path, "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        raise Exception("Could not determine video duration.")
    
    # Calculate 1% timestamp
    time_stamp = max(1, int(duration * 0.01))  # Ensure at least 1 second
    
    # Generate thumbnail
    command = [
        "ffmpeg", "-i", video_path, "-ss", str(time_stamp), "-vframes", "1", thumb_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return duration  # Return total duration


async def is_direct_download(url):
    """Function to check if the URL is a direct download link."""
    # List of common file extensions for download links (you can expand this as needed)
    valid_extensions = ['.mp4', '.m3u8', '.jpg', '.png', '.zip', '.pdf', '.rar', '.txt']
    
    # Check if the URL ends with a valid file extension
    if any(url.endswith(ext) for ext in valid_extensions):
        return True
    
    # You can also perform an HTTP HEAD request to check if the URL points to a downloadable resource
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(url) as response:
                # If the response status is OK (200), and the content type is a file type (e.g., video, pdf)
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application' in content_type or 'video' in content_type or 'audio' in content_type:
                        return True
        except Exception as e:
            lg.info(f"Error checking direct download URL: {e}")
    
    return False

        
# Example usage:
# duration = generate_thumbnail("video.mp4", "thumb.jpg")
# print(f"Video Duration: {duration} seconds")
