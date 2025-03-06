# ---------------------------------------------------
# File Name: gcast.py
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
from devgagan.core.mongo.db import users
from config import OWNER_ID

@app.on_message(filters.command("gcast"))
async def broadcast_handler(client, message):
    """Handle global broadcast to all users."""
    try:
        user_id = message.from_user.id
        
        # Only owner can broadcast
        if user_id != OWNER_ID:
            await message.reply("⚠️ Only the bot owner can broadcast messages.")
            return
            
        # Check if there's a message to broadcast
        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply("❌ Please provide a message to broadcast or reply to a message.")
            return
            
        # Get broadcast message
        if message.reply_to_message:
            broadcast_msg = message.reply_to_message
        else:
            broadcast_msg = message
            broadcast_msg.text = " ".join(message.command[1:])
            
        # Get all users
        all_users = await users.find().to_list(length=None)
        
        if not all_users:
            await message.reply("❌ No users found in database.")
            return
            
        # Send status message
        status_msg = await message.reply("🚀 Broadcasting message...")
        
        # Track success/failure
        success = 0
        failed = 0
        
        # Broadcast to each user
        for user in all_users:
            try:
                if message.reply_to_message:
                    await broadcast_msg.copy(user['user_id'])
                else:
                    await client.send_message(user['user_id'], broadcast_msg.text)
                success += 1
                await asyncio.sleep(0.1)  # Prevent flooding
            except Exception as e:
                print(f"Failed to send to {user['user_id']}: {e}")
                failed += 1
                
        # Update status message
        await status_msg.edit(
            f"✅ Broadcast completed!\n\n"
            f"📤 Successfully sent: `{success}`\n"
            f"📥 Failed: `{failed}`\n"
            f"📊 Total users: `{len(all_users)}`"
        )
        
    except Exception as e:
        print(f"Error in broadcast handler: {e}")
        await message.reply("❌ Failed to process broadcast. Please try again later.")


@app.on_message(filters.command("acast") & filters.user(OWNER_ID))
async def announced(_, message):
    if message.reply_to_message:
      to_send=message.reply_to_message.id
    if not message.reply_to_message:
      return await message.reply_text("Reply To Some Post To Broadcast")
    users = await users.find().to_list(length=None)
    print(users)
    failed_user = 0
  
    for user in users:
      try:
        await _.forward_messages(chat_id=int(user['user_id']), from_chat_id=message.chat.id, message_ids=to_send)
        await asyncio.sleep(1)
      except Exception as e:
        failed_user += 1
          
    if failed_user == 0:
        await message.reply_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{len(users)}` **ᴜsᴇʀs**",
        )
    else:
        await message.reply_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{len(users) - failed_user}` **ᴜsᴇʀs**\n\n**ɴᴏᴛᴇ:-** `ᴅᴜᴇ ᴛᴏ sᴏᴍᴇ ɪssᴜᴇ ᴄᴀɴ'ᴛ ᴀʙʟᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ` `{failed_user}` **ᴜsᴇʀs**",
        )
