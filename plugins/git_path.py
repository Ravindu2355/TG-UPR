import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from globals import AuthU, settings
from Func.utils import mention_user

# sturcure:
#    {user_id}/{user_path}

user_paths={}
defalt="files"

def git_path(id):
  if not str(id) in user_paths:
    Fp = defalt
  else:
    Fp = user_paths[str(id)]
  return f"{id}/{Fp}"

@Client.on_message(filters.command("gitpath"))
async def st_git_p(client,message):
  npath = message.text.split(" ")[1]
  if not is_authorized(message.chat.id):
    await message.reply
    return
  user_paths[str(message.chat.id)] = npath
  await message.reply(f"✅️**Now path is:** {git_path(message.chat.id)}")


  
