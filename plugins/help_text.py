from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from globals import AuthU, settings
from Func.utils import mention_user

@Client.on_message(filters.command("start"))
async def st_rep(client,message:Message):
    await message.reply(f"**🔰RVX Downloader🔰\n\n❤️Welcome {mention_user(message)}💪!\n😎I am an simple link uploader bot.\n😊Give me a link and \n😇I will upload it to telegram...😎**")

@Client.on_message(filters.command("help"))
async def st_help(client,message:Message):
    await message.reply("🫠**No avalable!**\n\n**Commands: **\n\n  /start\n  /help\n  /checkauth\n  /addauth\n  /removeauth\n  /m3u8\n  /logo : use carefully")

@Client.on_callback_query(filters.regex(r"cancel"))
async def cancelQ(client,query):
    await query.message.edit_text("🔰Operation cancelled.🪚")

@Client.on_callback_query(filters.regex(r"lang_"))
async def ch_lang(client,query):
  global settings
  msg = query.message
  lang= query.data.split("_", 1)[1]  # Get the part after "_"
  settings["lang"] = lang  # Get the part after "_"
  await msg.edit_text(f"**Language** : **{lang.upper()}**")
