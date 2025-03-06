# ---------------------------------------------------
# File Name: stats.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# ---------------------------------------------------



import time
import sys
from devgagan import app
from pyrogram import filters
from devgagan.core.mongo.db import users, premium_users, watermark_users
from config import OWNER_ID
from devgagan.core.mongo.users_db import get_users, add_user, get_user

start_time = time.time()

@app.on_message(group=10)
async def chat_watcher_func(_, message):
    """Watch chat messages and add new users to database."""
    try:
        if message.from_user:
            user_id = message.from_user.id
            username = message.from_user.username
            
            us_in_db = await get_user(user_id)
            if not us_in_db:
                await add_user(user_id, username)
    except Exception as e:
        print(f"Error in chat watcher: {e}")

def time_formatter(seconds: float) -> str:
    """Format time duration into weeks, days, hours, minutes, seconds."""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    
    parts = []
    if weeks > 0:
        parts.append(f"{weeks}w")
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")
        
    return ":".join(parts) if parts else "0s"

@app.on_message(filters.command("stats"))
async def stats_handler(_, message):
    """Handle the /stats command."""
    try:
        # Only owner can view stats
        if message.from_user.id != OWNER_ID:
            await message.reply("⚠️ Only the bot owner can view statistics.")
            return
            
        # Get counts
        total_users = len(await get_users())
        premium_count = await premium_users.count_documents({})
        watermark_count = await watermark_users.count_documents({})
        
        # Calculate uptime
        uptime = time_formatter(time.time() - start_time)
        
        # Format stats message
        stats = f"""
📊 **Bot Statistics**

👥 Total Users: `{total_users}`
⭐️ Premium Users: `{premium_count}`
🖼 Watermark Users: `{watermark_count}`
⚡️ Python Version: `{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}`
⏰ Uptime: `{uptime}`
"""
        await message.reply(stats)
        
    except Exception as e:
        print(f"Error in stats handler: {e}")
        await message.reply("❌ An error occurred while fetching statistics.")
