from pyrogram import Client, filters
from sites.ext import run_extractor
from Func.json_filehandle import save_json, get_json, delete_json
from plugins.tgup import upload_file
from Func.downloader import dl
import os

@Client.on_callback_query(filters.regex(r'ext_'))
async def handle_callback(client, callback_query):
    # Get the callback data
    callback_data = callback_query.data
    message = callback_query.message
    msg = await message.reply("Starting...")
    await message.delete()
    # You can split the callback data if needed
    parts = callback_data.split("_")

    # Example of how to handle the callback data
    if not len(parts) >= 4:
      await msg.edit_text("No data 4")
      return
    
    ext = parts[0]  # 'ext'
    jsonf = parts[1]  # {jsonf}
    mk = parts[2]  # mp4
    k = parts[3]  # {k}

    json_data = get_json(jsonf)
    link = json_data["links"][mk][k]
    if ".mp4" in link and "H" in mk:
        mk = "mp4"
    newName = f"{json_data['name']}.{mk}"
    dl_file = await dl(url=link, msg=msg, custom_filename=newName)
    if dl_file and not "error" in dl_file:
        res = await upload_file(client, message.chat.id, dl_file["file_path"], msg, as_document=False, thumb=None) #try upload
        if res:
          lg.info(f"Uploaded {dl_file['filename']}")
        else:
          lg.info(f"Err on Uploading...")
    else:
        lg.info(f"Err on dl...{dl_file['error']}")
    delete_json(jsonf)
    # Do something with these values
    #print(f"ext: {ext}, jsonf: {jsonf}, mp4: {mp4}, k: {k}")
    
    #await callback_query.answer("Received your callback!")

