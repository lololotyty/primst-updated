import logging
from pyrogram import filters
from devgagan import app
from devgagan.core.mongo.db import watermark_users
from config import OWNER_ID
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Store user watermark text preferences in memory
user_watermarks = {}

async def is_watermark_user(user_id: int) -> bool:
    """Check if a user has watermark permission."""
    try:
        user = await watermark_users.find_one({'user_id': user_id})
        return bool(user)
    except Exception as e:
        logger.error(f"Error checking watermark permission for user {user_id}: {e}")
        return False

async def add_watermark_user(user_id: int) -> bool:
    """Add watermark permission for a user."""
    try:
        await watermark_users.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'added_on': datetime.utcnow(),
                'active': True
            }},
            upsert=True
        )
        logger.info(f"Added watermark permission for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding watermark user {user_id}: {e}")
        return False

async def remove_watermark_user(user_id: int) -> bool:
    """Remove watermark permission from a user."""
    try:
        result = await watermark_users.delete_one({'user_id': user_id})
        if result.deleted_count > 0:
            logger.info(f"Removed watermark permission from user {user_id}")
            # Also clear any stored watermark
            user_watermarks.pop(user_id, None)
            return True
        return False
    except Exception as e:
        logger.error(f"Error removing watermark user {user_id}: {e}")
        return False

# Command handlers with multiple prefixes
setwatermark_filter = filters.command(["setwatermark", "sw"]) | filters.command(["setwatermark", "sw"], prefixes="!")
@app.on_message(setwatermark_filter)
async def set_watermark(_, message):
    """Set watermark text for a user."""
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting to set watermark")
        
        # Check if user has watermark permission
        if not (user_id == OWNER_ID or await is_watermark_user(user_id)):
            await message.reply("❌ You don't have permission to use watermark features.")
            return
        
        # Get watermark text
        if len(message.command) < 2:
            await message.reply(
                "❌ Please provide the watermark text.\n\n"
                "Usage: `/setwatermark Your Watermark Text` or `/sw Your Watermark Text`"
            )
            return
        
        watermark_text = " ".join(message.command[1:])
        if len(watermark_text) > 100:  # Reasonable limit for watermark text
            await message.reply("❌ Watermark text too long. Please keep it under 100 characters.")
            return
            
        user_watermarks[user_id] = watermark_text
        logger.info(f"Set watermark for user {user_id}: {watermark_text}")
        await message.reply(
            f"✅ Watermark text set to: `{watermark_text}`\n\n"
            "This will be applied to your future uploads."
        )
    except Exception as e:
        logger.error(f"Error in set_watermark for user {message.from_user.id}: {e}")
        await message.reply("❌ Failed to set watermark. Please try again.")

clearwatermark_filter = filters.command(["clearwatermark", "cw"]) | filters.command(["clearwatermark", "cw"], prefixes="!")
@app.on_message(clearwatermark_filter)
async def clear_watermark(_, message):
    """Clear watermark text for a user."""
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting to clear watermark")
        
        # Check if user has watermark permission
        if not (user_id == OWNER_ID or await is_watermark_user(user_id)):
            await message.reply("❌ You don't have permission to use watermark features.")
            return
        
        if user_id in user_watermarks:
            del user_watermarks[user_id]
            logger.info(f"Cleared watermark for user {user_id}")
            await message.reply("✅ Watermark cleared. Future uploads will not have watermarks.")
        else:
            await message.reply("ℹ️ You don't have any watermark set.")
    except Exception as e:
        logger.error(f"Error in clear_watermark for user {message.from_user.id}: {e}")
        await message.reply("❌ Failed to clear watermark. Please try again.")

addwatermarkuser_filter = filters.command(["addwatermarkuser", "awu"]) | filters.command(["addwatermarkuser", "awu"], prefixes="!")
@app.on_message(addwatermarkuser_filter & filters.user(OWNER_ID))
async def add_watermark_user_cmd(_, message):
    """Add a user to watermark permissions."""
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting to add watermark user")
        
        # Get target user ID
        if len(message.command) != 2:
            await message.reply(
                "❌ Please provide the user ID.\n\n"
                "Usage: `/addwatermarkuser 123456789` or `/awu 123456789`"
            )
            return
        
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID. Please provide a valid numeric ID.")
            return
            
        if await add_watermark_user(target_user_id):
            await message.reply(f"✅ User `{target_user_id}` can now use watermark features.")
        else:
            await message.reply("❌ Failed to add watermark permission.")
    except Exception as e:
        logger.error(f"Error in add_watermark_user_cmd: {e}")
        await message.reply("❌ Failed to add watermark user. Please try again.")

removewatermarkuser_filter = filters.command(["removewatermarkuser", "rwu"]) | filters.command(["removewatermarkuser", "rwu"], prefixes="!")
@app.on_message(removewatermarkuser_filter & filters.user(OWNER_ID))
async def remove_watermark_user_cmd(_, message):
    """Remove a user from watermark permissions."""
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} attempting to remove watermark user")
        
        # Get target user ID
        if len(message.command) != 2:
            await message.reply(
                "❌ Please provide the user ID.\n\n"
                "Usage: `/removewatermarkuser 123456789` or `/rwu 123456789`"
            )
            return
        
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply("❌ Invalid user ID. Please provide a valid numeric ID.")
            return
            
        if await remove_watermark_user(target_user_id):
            await message.reply(f"✅ User `{target_user_id}` can no longer use watermark features.")
        else:
            await message.reply("❌ User not found or failed to remove watermark permission.")
    except Exception as e:
        logger.error(f"Error in remove_watermark_user_cmd: {e}")
        await message.reply("❌ Failed to remove watermark user. Please try again.")

watermarkstatus_filter = filters.command(["watermarkstatus", "ws"]) | filters.command(["watermarkstatus", "ws"], prefixes="!")
@app.on_message(watermarkstatus_filter)
async def watermark_status(_, message):
    """Check watermark status and permissions."""
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} checking watermark status")
        
        has_permission = user_id == OWNER_ID or await is_watermark_user(user_id)
        current_watermark = user_watermarks.get(user_id, None)
        
        status = "📋 **Watermark Status**\n\n"
        status += f"🔑 Permission: {'✅ Yes' if has_permission else '❌ No'}\n"
        
        if has_permission:
            status += f"💬 Current Watermark: {f'`{current_watermark}`' if current_watermark else 'Not set'}\n"
            status += "\nℹ️ Available commands:\n"
            status += "• `/setwatermark <text>` or `/sw <text>` - Set watermark text\n"
            status += "• `/clearwatermark` or `/cw` - Clear watermark text\n"
            status += "• `/watermarkstatus` or `/ws` - Check watermark status\n"
            
            if user_id == OWNER_ID:
                status += "\n👑 Owner commands:\n"
                status += "• `/addwatermarkuser <user_id>` or `/awu <user_id>` - Give watermark permission\n"
                status += "• `/removewatermarkuser <user_id>` or `/rwu <user_id>` - Remove watermark permission"
                
        await message.reply(status)
    except Exception as e:
        logger.error(f"Error in watermark_status for user {message.from_user.id}: {e}")
        await message.reply("❌ Failed to get watermark status. Please try again.")
