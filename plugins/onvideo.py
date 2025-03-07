import os, asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from plugins.authers import is_authorized
from plugins.tgdw import download_file
from plugins.git_up import to_git

download_dir = "/forGit"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)
"""
@Client.on_message(filters.command("git"))
async def up_to_git(client, message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply("Please reply to video message with this command")
        return
    
    if not is_authorized(message.chat.id):
        await message.reply("**❌️You are not authorized to use me!❌️**")
        return
    
    v_msg = message.reply_to_message
    v_path = os.path.join(download_dir, v_msg.video.file_name)
    msg = await message.reply(f"Trying to start!...\n {v_path}")
    
    # Parse additional arguments (threads, extra arguments)
    command_args = message.text.split(maxsplit=1)
    
    threads = None
    extra_args = []
    
    if len(command_args) > 1:
        params = command_args[1].split()
        for param in params:
            if param.startswith("-threads"):
                # Extract the number of threads after '-threads'
                threads = int(param.split("=")[1]) if "=" in param else 4  # default to 4 if not specified
            else:
                extra_args.append(param)
    
    # Download the video file
    file_path = await download_file(client, v_msg, download_dir, msg)
    if file_path:
        # Pass threads and extra_args to the to_git function
        r = await to_git(file_path, msg, trs=threads, extra=extra_args)

"""


@Client.on_message(filters.command("git"))
async def up_to_git(client, message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply("Please reply to video message with this command")
        return
    
    if not is_authorized(message.chat.id):
        await message.reply("**❌️You are not authorized to use me!❌️**")
        return
    
    v_msg = message.reply_to_message
    # Check if file_name exists
    if v_msg.video and v_msg.video.file_name:
        v_path = os.path.join(download_dir, v_msg.video.file_name)
    else:
        # Generate a fallback name if file_name is None
        v_path = os.path.join(download_dir, f"{v_msg.video.file_id}.mp4")  # Using file_id as fallback name
    msg = await message.reply(f"Trying to start!...\n {v_path}")
    
    # Parse additional arguments (threads, extra arguments)
    command_args = message.text.split(maxsplit=1)
    
    threads = None
    extra_args = []
    
    if len(command_args) > 1:
        params = command_args[1].split()
        for param in params:
            if param.startswith("-threads"):
                # Extract the number of threads after '-threads'
                threads = int(param.split("=")[1]) if "=" in param else 4  # default to 4 if not specified
            else:
                extra_args.append(param)
    
    # Download the video file
    file_path = await download_file(client, v_msg, download_dir, msg)
    if file_path:
        # Pass threads and extra_args to the to_git function
        r = await to_git(file_path, msg, trs=threads, extra=extra_args)
