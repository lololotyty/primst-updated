from .. import app
from ..core.mongo.users_db import add_watermark_user, remove_watermark_user, is_watermark_user
from pyrogram import filters
from config import OWNER_ID

# Store user watermark text preferences
user_watermarks = {}

@app.on_message(filters.command("setwatermark") & filters.private)
async def set_watermark(_, message):
    """Set watermark text for a user."""
    user_id = message.from_user.id
    
    # Check if user has watermark permission
    if not (user_id in OWNER_ID or await is_watermark_user(user_id)):
        await message.reply("❌ You don't have permission to use watermark features.")
        return
    
    # Get watermark text
    if len(message.command) < 2:
        await message.reply("Please provide the watermark text.\nUsage: `/setwatermark Your Watermark Text`")
        return
    
    watermark_text = " ".join(message.command[1:])
    user_watermarks[user_id] = watermark_text
    await message.reply(f"✅ Watermark text set to: `{watermark_text}`\n\nThis will be applied to your future uploads.")

@app.on_message(filters.command("clearwatermark") & filters.private)
async def clear_watermark(_, message):
    """Clear watermark text for a user."""
    user_id = message.from_user.id
    
    # Check if user has watermark permission
    if not (user_id in OWNER_ID or await is_watermark_user(user_id)):
        await message.reply("❌ You don't have permission to use watermark features.")
        return
    
    if user_id in user_watermarks:
        del user_watermarks[user_id]
        await message.reply("✅ Watermark cleared. Future uploads will not have watermarks.")
    else:
        await message.reply("You don't have any watermark set.")

@app.on_message(filters.command("addwatermarkuser") & filters.private)
async def add_watermark_user_cmd(_, message):
    """Add a user to watermark permissions."""
    user_id = message.from_user.id
    
    # Only owner can add watermark users
    if user_id not in OWNER_ID:
        await message.reply("❌ Only the bot owner can add watermark users.")
        return
    
    # Get target user ID
    if len(message.command) != 2:
        await message.reply("Please provide the user ID.\nUsage: `/addwatermarkuser 123456789`")
        return
    
    try:
        target_user_id = int(message.command[1])
        if await add_watermark_user(target_user_id):
            await message.reply(f"✅ User {target_user_id} can now use watermark features.")
        else:
            await message.reply("❌ Failed to add watermark permission.")
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a valid numeric ID.")

@app.on_message(filters.command("removewatermarkuser") & filters.private)
async def remove_watermark_user_cmd(_, message):
    """Remove a user from watermark permissions."""
    user_id = message.from_user.id
    
    # Only owner can remove watermark users
    if user_id not in OWNER_ID:
        await message.reply("❌ Only the bot owner can remove watermark users.")
        return
    
    # Get target user ID
    if len(message.command) != 2:
        await message.reply("Please provide the user ID.\nUsage: `/removewatermarkuser 123456789`")
        return
    
    try:
        target_user_id = int(message.command[1])
        if await remove_watermark_user(target_user_id):
            await message.reply(f"✅ User {target_user_id} can no longer use watermark features.")
        else:
            await message.reply("❌ User not found or failed to remove watermark permission.")
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a valid numeric ID.")

