import os, asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from plugins.authers import is_authorized
from plugins.tgup import upload_file
from Func.downloader import dl
from Func.utils import mention_user, generate_thumbnail, get_tg_filename, is_direct_download
from log import logger as lg
import aiohttp
from sites.ext import run_extractor
from Func.json_filehandle import save_json, get_json
from plugins.pixup import pixurl_command_handler


"""
@Client.on_message(filters.regex(r'https?://[^\s]+'))
async def handle_link(client, message):
  link = message.text
  if "|" in link:
    link, newName = link.split("|")
  else:
    newName = None
    
  if not is_authorized(message.chat.id):
      await message.reply("**❌️You are not my auther for use me!...❌️**")
      return
  stT = f"🛠**Processing...**"
  msg = await message.reply(stT)
  dl_file = await dl(url=link, msg=msg, custom_filename=newName)
  if dl_file and not "error" in dl_file:
    res = await upload_file(client, message.chat.id, dl_file["file_path"], msg, as_document=False, thumb=None) #try upload
    if res:
      lg.info(f"Uploaded {dl_file['filename']}")
    else:
      lg.info(f"Err on Uploading...")
  else:
    lg.info(f"Err on dl...{dl_file['error']}")
"""  

@Client.on_message(filters.regex(r'https?://[^\s]+'))
async def handle_link(client, message):
    link = message.text
    if "/pixurl" in link:
      return await pixurl_command_handler(client,message)
    if "|" in link:
        link, newName = link.split("|")
    else:
        newName = None

    # Check if the user is authorized
    if not is_authorized(message.chat.id):
        await message.reply("**❌️You are not authorized to use me!❌️**")
        return

    # Show processing message
    stT = f"🛠 **Processing...**"
    msg = await message.reply(stT)

    # Check if the URL is a direct download link
    if await is_direct_download(link):
        # Proceed to download the file
        dl_file = await dl(url=link, msg=msg, custom_filename=newName)
        if dl_file and not "error" in dl_file:
            res = await upload_file(client, message.chat.id, dl_file["file_path"], msg, as_document=False, thumb=None)  # try upload
            if res:
                lg.info(f"Uploaded {dl_file['filename']}")
            else:
                lg.info(f"Error on Uploading...")
        else:
            lg.info(f"Error on download...{dl_file['error']}")
    else:
        # Inform the user that the link is not a direct download
        await msg.edit_text("**❌️This is not a direct link so I'm trying to extract!...**")
        data = run_extractor(link)
        if not "error" in data:
          jsonf = save_json(data)
          rtext = f'**📃Extracted✅️\n\n'#🟢**Name**: {data.get("name","N/A")}\n🟢**Discription**: {data.get("discription","N/A")}\n🟢Duration: {data.get("duration","N/A")}'
          for key in data:
            if key != "links" and key != "thumbnail":
              rtext+=f'🟢**{key}**: {data.get(key,"N/A")}\n'
          bar = []
          links = data["links"]
          for qs in data["links"]:
            qty = data["links"][qs]
            for k in qty:
              button = [InlineKeyboardButton(f"{qs}({k})",callback_data=f"ext_{jsonf}_{qs}_{k}")]
              bar.append(button)
          
          keyboard=InlineKeyboardMarkup(bar)
          if data["thumbnail"]:
            await msg.reply_photo(
              photo=data["thumbnail"],
              caption=rtext,
              reply_markup=keyboard
              )
            await msg.delete()
          else:
            await msg.edit_text(
              text=rtext,
              reply_markup=keyboard
            )
      
        else:
          await msg.edit_text(f"**Error: {data['error']}")
        
