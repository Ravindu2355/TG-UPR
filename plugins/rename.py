import os, asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from plugins.authers import is_authorized
from plugins.tgdw import download_file
from plugins.tgup import upload_file

download_dir = "/forRename"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

@Client.on_message(filters.command("rename"))
async def rename_file(client, message: Message):
    if not message.reply_to_message:
        await message.reply("❌ Reply to a file with:\n`/rename newname.ext`")
        return

    if not is_authorized(message.chat.id):
        await message.reply("**❌️You are not authorized to use me!❌️**")
        return

    # Get new name
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("❌ Usage:\n`/rename newname.ext`")
        return

    new_name = args[1].strip()

    # Validate filename
    if "/" in new_name or "\\" in new_name:
        await message.reply("❌ Invalid file name.")
        return

    r_msg = message.reply_to_message

    # Detect media
    media = (
        r_msg.video or r_msg.document or r_msg.audio
        or r_msg.photo or r_msg.voice
    )

    if not media:
        await message.reply("❌ Unsupported file type.")
        return

    status = await message.reply("⬇️ Downloading file...")

    # Download
    file_path = await download_file(client, r_msg, download_dir, status)
    if not file_path or not os.path.exists(file_path):
        await status.edit_text("❌ Download failed.")
        return

    # Rename
    new_path = os.path.join(download_dir, new_name)
    try:
        os.rename(file_path, new_path)
    except Exception as e:
        await status.edit_text(f"❌ Rename failed:\n`{e}`")
        return

    await status.edit_text("⬆️ Uploading renamed file...")

    # Upload (reuse your uploader)
    await upload_file(
        client=client,
        chat_id=message.chat.id,
        file_path=new_path,
        msg=status,
        as_document=True  # safest for all file types
  )
