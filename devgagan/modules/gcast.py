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
from devgagan.core.mongo.db import users, broadcast_list
from config import OWNER_ID
from datetime import datetime

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_handler(client, message):
    """Handle broadcasting messages to all users."""
    try:
        # Check if there's a message to broadcast
        if not message.reply_to_message:
            await message.reply(
                "❌ Please reply to a message to broadcast it.\n\n"
                "Usage: Reply to any message with `/broadcast`"
            )
            return
            
        # Get all users
        all_users = await users.find().to_list(length=None)
        broadcast_msg = message.reply_to_message
        
        if not all_users:
            await message.reply("❌ No users found in database.")
            return
            
        # Initialize counters
        success = 0
        failed = 0
        
        # Send status message
        status_msg = await message.reply("🚀 Broadcasting message...")
        
        # Broadcast to each user
        for user in all_users:
            try:
                user_id = user.get('_id')
                if not user_id:
                    continue
                    
                await broadcast_msg.copy(user_id)
                success += 1
                
                # Log broadcast
                await broadcast_list.insert_one({
                    'user_id': user_id,
                    'message_id': broadcast_msg.id,
                    'timestamp': datetime.utcnow(),
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"Failed to broadcast to {user_id}: {e}")
                failed += 1
                
                # Log failed broadcast
                await broadcast_list.insert_one({
                    'user_id': user_id,
                    'message_id': broadcast_msg.id,
                    'timestamp': datetime.utcnow(),
                    'status': 'failed',
                    'error': str(e)
                })
                
            # Update status every 20 users
            if (success + failed) % 20 == 0:
                try:
                    await status_msg.edit(
                        f"🚀 Broadcasting message...\n\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed}\n"
                        f"⏳ Progress: {((success + failed) / len(all_users)) * 100:.1f}%"
                    )
                except:
                    pass
                    
        # Send final status
        await status_msg.edit(
            f"✅ Broadcast completed!\n\n"
            f"📊 Statistics:\n"
            f"👥 Total Users: {len(all_users)}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}"
        )
        
    except Exception as e:
        print(f"Error in broadcast handler: {e}")
        await message.reply("❌ An error occurred while broadcasting.")

@app.on_message(filters.command("broadcaststats") & filters.user(OWNER_ID))
async def broadcast_stats_handler(client, message):
    """Show statistics about past broadcasts."""
    try:
        # Get total broadcasts
        total_broadcasts = await broadcast_list.count_documents({})
        success_count = await broadcast_list.count_documents({'status': 'success'})
        failed_count = await broadcast_list.count_documents({'status': 'failed'})
        
        # Get recent broadcasts
        recent = await broadcast_list.find().sort('timestamp', -1).limit(5).to_list(length=None)
        
        # Format stats message
        stats = f"""
📊 **Broadcast Statistics**

📨 Total Broadcasts: `{total_broadcasts}`
✅ Successful: `{success_count}`
❌ Failed: `{failed_count}`

🕒 Recent Broadcasts:
"""
        
        for item in recent:
            status = "✅" if item['status'] == 'success' else "❌"
            stats += f"{status} User `{item['user_id']}` - {item['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}\n"
            
        await message.reply(stats)
        
    except Exception as e:
        print(f"Error in broadcast stats handler: {e}")
        await message.reply("❌ An error occurred while fetching broadcast statistics.")
