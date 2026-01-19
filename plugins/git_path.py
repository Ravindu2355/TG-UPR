import os
from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.authers import is_authorized

# Structures to store user repo and path
user_repos = {}
user_paths = {}
default_path = "files"

def git_path(user_id: int) -> str:
    """Return the user's path for GitHub storage."""
    path = user_paths.get(str(user_id), default_path)
    return f"{path}"

def git_repo(user_id: int) -> str:
    """Return the user's repo for GitHub storage."""
    return user_repos.get(str(user_id), "")

# Command to set user GitHub repo
@Client.on_message(filters.command("setgitrepo"))
async def set_git_repo(client: Client, message: Message):
    if not is_authorized(message.chat.id):
        await message.reply("❌ You are not authorized!")
        return
    try:
        repo_name = message.text.split(" ", 1)[1]
    except IndexError:
        await message.reply("Usage: /setgitrepo <repo_name>")
        return

    user_repos[str(message.chat.id)] = repo_name
    await message.reply(f"✅ **Your GitHub repo is now:** `{repo_name}`")

# Command to get user GitHub repo
@Client.on_message(filters.command("gitrepo"))
async def get_git_repo(client: Client, message: Message):
    repo = git_repo(message.chat.id)
    if repo:
        await message.reply(f"Your GitHub repo: `{repo}`")
    else:
        await message.reply("❌ No repo set. Use /setgitrepo <repo_name>")

# Command to set user GitHub path
@Client.on_message(filters.command("setgitpath"))
async def set_git_path(client: Client, message: Message):
    if not is_authorized(message.chat.id):
        await message.reply("❌ You are not authorized!")
        return
    try:
        path = message.text.split(" ", 1)[1]
    except IndexError:
        await message.reply("Usage: /setgitpath <path>")
        return

    user_paths[str(message.chat.id)] = path
    await message.reply(f"✅ Your GitHub path is now: `{git_path(message.chat.id)}`")

# Command to get user GitHub path
@Client.on_message(filters.command("gitpath"))
async def get_git_path(client: Client, message: Message):
    await message.reply(f"Your GitHub path: `{git_path(message.chat.id)}`")
