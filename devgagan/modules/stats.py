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
import motor
from devgagan import app
from pyrogram import filters
from devgagan.core.mongo.db import users, premium_users, watermark_users
from config import OWNER_ID
from devgagan.core.mongo.users_db import get_users, add_user, get_user
from devgagan.core.mongo.plans_db import premium_users



start_time = time.time()

@app.on_message(group=10)
async def chat_watcher_func(_, message):
    try:
        if message.from_user:
            us_in_db = await get_user(message.from_user.id)
            if not us_in_db:
                await add_user(message.from_user.id)
    except:
        pass



def time_formatter():
    minutes, seconds = divmod(int(time.time() - start_time), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    tmp = (
        ((str(weeks) + "w:") if weeks else "")
        + ((str(days) + "d:") if days else "")
        + ((str(hours) + "h:") if hours else "")
        + ((str(minutes) + "m:") if minutes else "")
        + ((str(seconds) + "s") if seconds else "")
    )
    if tmp != "":
        if tmp.endswith(":"):
            return tmp[:-1]
        else:
            return tmp
    else:
        return "0 s"


@app.on_message(filters.command("stats"))
async def stats_handler(client, message):
    """Handle the /stats command to show bot statistics."""
    try:
        user_id = message.from_user.id
        
        # Only owner can view stats
        if user_id != OWNER_ID:
            await message.reply("⚠️ Only the bot owner can view statistics.")
            return
            
        # Get counts from each collection
        total_users = await users.count_documents({})
        premium_count = await premium_users.count_documents({})
        watermark_count = await watermark_users.count_documents({})
        
        # Format statistics message
        stats_text = (
            "📊 **Bot Statistics**\n\n"
            f"👥 Total Users: `{total_users}`\n"
            f"💎 Premium Users: `{premium_count}`\n"
            f"🖼 Watermark Users: `{watermark_count}`\n"
        )
        
        await message.reply(stats_text)
        
    except Exception as e:
        print(f"Error in stats handler: {e}")
        await message.reply("❌ Failed to fetch statistics. Please try again later.")
