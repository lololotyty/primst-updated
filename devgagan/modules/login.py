# ---------------------------------------------------
# File Name: login.py
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

from pyrogram import filters
from devgagan import app
from devgagan.core.mongo.db import sessions, users
from config import OWNER_ID
import asyncio

def generate_random_name(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))  

async def delete_session_files(user_id):
    session_file = f"session_{user_id}.session"
    memory_file = f"session_{user_id}.session-journal"

    session_file_exists = os.path.exists(session_file)
    memory_file_exists = os.path.exists(memory_file)

    if session_file_exists:
        os.remove(session_file)
    
    if memory_file_exists:
        os.remove(memory_file)

    # Delete session from the database
    if session_file_exists or memory_file_exists:
        await db.remove_session(user_id)
        return True  # Files were deleted
    return False  # No files found

@app.on_message(filters.command("login"))
async def login_handler(client, message):
    """Handle user login and session management."""
    try:
        user_id = message.from_user.id
        
        # Only owner can use login command
        if user_id != OWNER_ID:
            await message.reply("⚠️ Only the bot owner can use this command.")
            return
            
        # Check if session string is provided
        if len(message.command) < 2:
            await message.reply("❌ Please provide your session string.\n\nUsage: `/login <session_string>`")
            return
            
        session_string = message.command[1]
        
        # Store session
        try:
            await sessions.update_one(
                {"user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "session_string": session_string,
                    "active": True
                }},
                upsert=True
            )
            
            # Also ensure user exists in users collection
            await users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
            
            await message.reply("✅ Login successful! Your session has been saved.")
            
        except Exception as e:
            print(f"Database error during login: {e}")
            await message.reply("❌ Failed to save session. Please try again later.")
            
    except Exception as e:
        print(f"Error in login handler: {e}")
        await message.reply("❌ An error occurred. Please try again later.")

@app.on_message(filters.command("logout"))
async def logout_handler(client, message):
    """Handle user logout."""
    try:
        user_id = message.from_user.id
        
        # Only owner can use logout command
        if user_id != OWNER_ID:
            await message.reply("⚠️ Only the bot owner can use this command.")
            return
            
        # Remove session
        try:
            result = await sessions.update_one(
                {"user_id": user_id},
                {"$set": {"active": False}}
            )
            
            if result.modified_count > 0:
                await message.reply("✅ Logout successful! Your session has been deactivated.")
            else:
                await message.reply("❌ No active session found.")
                
        except Exception as e:
            print(f"Database error during logout: {e}")
            await message.reply("❌ Failed to process logout. Please try again later.")
            
    except Exception as e:
        print(f"Error in logout handler: {e}")
        await message.reply("❌ An error occurred. Please try again later.")
