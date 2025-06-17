# ---------------------------------------------------
# File Name: main.py
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
# More readable 
# ---------------------------------------------------

import time
import random
import string
import asyncio
from pyrogram import filters, Client
from devgagan import app
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import subprocess
from devgagan.modules.shrink import is_user_verified
import os
import logging

logger = logging.getLogger(__name__)

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))



users_loop = {}
interval_set = {}
batch_mode = {}

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        # Reduced sleep time from 15 to 5 seconds
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(5)
    finally:
        pass

# Function to check if the user can proceed
async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):  # Premium or owner users can always proceed
        return True, None

    now = datetime.now()

    # Check if the user is on cooldown
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds(s) before sending another link. Alternatively, purchase premium for instant access.\n\n> Hey 👋 You can suck owners dick to use the bot free for 3 hours without any time limit."
        else:
            del interval_set[user_id]  # Cooldown expired, remove user from interval set

    return True, None

async def set_interval(user_id, interval_minutes=45):
    now = datetime.now()
    # Set the cooldown interval for the user
    interval_set[user_id] = now + timedelta(seconds=interval_minutes)
    

async def shimp_private_fetcher(self, client, message, username, message_id):
    """Handle private message downloads using username"""
    try:
        logger.info(f"Attempting to fetch message from username: {username}, message_id: {message_id}")
        
        # Get the message using username
        try:
            msg = await client.get_messages(username, message_id)
            if not msg:
                logger.error(f"Message not found for username: {username}, message_id: {message_id}")
                await message.reply_text("❌ Could not find the message. It may have been deleted or expired.")
                return
                
            logger.info(f"Message found. Type: {type(msg).__name__}")
            
            # Check if message is view-once
            is_view_once = hasattr(msg, 'view_once') and msg.view_once
            logger.info(f"Message is view-once: {is_view_once}")
            
            # Download and send the content
            if msg.photo:
                logger.info("Processing photo message")
                file = await msg.download()
                await message.reply_photo(file, caption=msg.caption)
                os.remove(file)
            elif msg.video:
                logger.info("Processing video message")
                file = await msg.download()
                await message.reply_video(file, caption=msg.caption)
                os.remove(file)
            elif msg.document:
                logger.info("Processing document message")
                file = await msg.download()
                await message.reply_document(file, caption=msg.caption)
                os.remove(file)
            elif msg.audio:
                logger.info("Processing audio message")
                file = await msg.download()
                await message.reply_audio(file, caption=msg.caption)
                os.remove(file)
            elif msg.voice:
                logger.info("Processing voice message")
                file = await msg.download()
                await message.reply_voice(file, caption=msg.caption)
                os.remove(file)
            elif msg.text:
                logger.info("Processing text message")
                await message.reply_text(msg.text)
            else:
                logger.warning(f"Unsupported message type: {type(msg).__name__}")
                await message.reply_text("❌ Unsupported message type.")
                
        except Exception as e:
            logger.error(f"Error getting message: {str(e)}")
            await message.reply_text("❌ Error accessing the message. Make sure you have access to it.")
            
    except Exception as e:
        logger.error(f"Error handling private message: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        await message.reply_text(f"❌ Error processing private message: {str(e)}\nPlease make sure you have access to the message and try again.")

@app.on_message(
    filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+')
    & filters.private
)
async def single_link(_, message):
    user_id = message.chat.id
    logger.info(f"Received link from user {user_id}: {message.text}")

    # Check subscription and batch mode
    if await subscribe(_, message) == 1 or user_id in batch_mode:
        return

    # Check if user is already in a loop
    if users_loop.get(user_id, False):
        await message.reply(
            "You already have an ongoing process. Please wait for it to finish or cancel it with /cancel."
        )
        return

    # Check freemium limits
    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get Premium", url="https://telegram.dog/shimps_bot")]
        ])
        await message.reply(
            "❌ This feature is only available for premium users.\n\n"
            "🔒 Free users cannot access this feature.\n"
            "💎 Upgrade to premium to unlock this and other exclusive features!",
            reply_markup=buttons
        )
        return

    # Check cooldown
    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed:
        await message.reply(response_message)
        return

    # Add user to the loop
    users_loop[user_id] = True

    link = message.text
    msg = await message.reply("Processing...")
    userbot = await initialize_userbot(user_id)

    try:
        if "/p/" in link:
            # Handle private chat links
            logger.info(f"Processing private chat link: {link}")
            parts = link.split("/p/")[1].split("&")
            logger.info(f"Split parts: {parts}")
            
            if len(parts) == 2:
                try:
                    username = parts[0]  # Now using username directly
                    message_id = int(parts[1])
                    logger.info(f"Parsed username: {username}, message_id: {message_id}")
                    await shimp_private_fetcher(_, userbot, message, username, message_id)
                except ValueError as ve:
                    logger.error(f"Error parsing message ID: {str(ve)}")
                    await msg.edit_text("❌ Invalid message ID format. Please check the link.")
            else:
                logger.error(f"Invalid link format. Expected 2 parts, got {len(parts)}")
                await msg.edit_text("❌ Invalid private chat link format. Use: https://t.me/p/username&messageid")
        elif "/b/" in link:
            # Handle bot description links
            logger.info(f"Processing bot description link: {link}")
            bot_username = link.split("/b/")[1]
            logger.info(f"Bot username: {bot_username}")
            await process_bot_description(_, userbot, message, bot_username)
        elif await is_normal_tg_link(link):
            # Handle normal Telegram links
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            await set_interval(user_id, interval_minutes=45)
        else:
            # Handle special Telegram links
            await process_special_links(userbot, user_id, msg, link)
            
    except FloodWait as fw:
        logger.warning(f"FloodWait error: {fw.x} seconds")
        await msg.edit_text(f'Try again after {fw.x} seconds due to floodwait from Telegram.')
    except Exception as e:
        logger.error(f"Error processing link: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error args: {e.args}")
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        if userbot:
            await userbot.stop()
        try:
            await msg.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")

async def initialize_userbot(user_id): # this ensure the single startup .. even if logged in or not
    """Initialize the userbot session for the given user."""
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro' # added gareebi text
            userbot = Client(
                "userbot",
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=device,
                session_string=data.get("session")
            )
            await userbot.start()
            return userbot
        except Exception:
            return None
    return None


async def is_normal_tg_link(link: str) -> bool:
    """Check if the link is a standard Telegram link."""
    special_identifiers = ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']
    return 't.me/' in link and not any(x in link for x in special_identifiers)
    
async def process_special_links(userbot, user_id, msg, link):
    """Handle special Telegram links."""
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        await msg.edit_text(result)
    elif any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)
    else:
        await msg.edit_text("Invalid link format.")


@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    user_id = message.chat.id
    # Check if a batch process is already running
    if users_loop.get(user_id, False):
        await app.send_message(
            message.chat.id,
            "You already have a batch process running. Please wait for it to complete."
        )
        return

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Free service is currently not available. Upgrade to premium for access.")
        return

    max_batch_size = FREEMIUM_LIMIT if freecheck == 1 else PREMIUM_LIMIT

    # Start link input
    for attempt in range(3):
        start = await app.ask(message.chat.id, "Please send the start link.\n\n> Maximum tries 3")
        start_id = start.text.strip()
        s = start_id.split("/")[-1]
        if s.isdigit():
            cs = int(s)
            break
        await app.send_message(message.chat.id, "Invalid link. Please send again ...")
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Number of messages input
    for attempt in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process?\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size:
                break
            raise ValueError()
        except ValueError:
            await app.send_message(
                message.chat.id, 
                f"Invalid number. Please enter a number between 1 and {max_batch_size}."
            )
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Validate and interval check
    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed:
        await message.reply(response_message)
        return
        
    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/save_restricted_botss")
    keyboard = InlineKeyboardMarkup([[join_button]])
    pin_msg = await app.send_message(
        user_id,
        f"Batch process started ⚡\nProcessing: 0/{cl}\n\n**Powered by Shimperd**",
        reply_markup=keyboard
    )
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True
    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)
        # Handle normal links first
        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                # Process t.me links (normal) without userbot
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered by Shimperd__**",
                        reply_markup=keyboard
                    )
                    normal_links_handled = True
        if normal_links_handled:
            await set_interval(user_id, interval_minutes=300)
            await pin_msg.edit_text(
                f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered by Shimperd__**",
                reply_markup=keyboard
            )
            await app.send_message(message.chat.id, "Batch completed successfully! 🎉")
            return
            
        # Handle special links with userbot
        for i in range(cs, cs + cl):
            if not userbot:
                await app.send_message(message.chat.id, "Login in bot first ...")
                users_loop[user_id] = False
                return
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if any(x in link for x in ['t.me/b/', 't.me/c/']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n**__Powered by Shimperd__**",
                        reply_markup=keyboard
                    )
                    try:
                        await msg.delete()
                    except:
                        pass

        # Show completion message
        await set_interval(user_id, interval_minutes=300)
        await pin_msg.edit_text(
            f"Batch completed successfully for {cl} messages 🎉\n\n**__Powered by Shimperd__**",
            reply_markup=keyboard
        )
        await app.send_message(message.chat.id, "Batch completed successfully! 🎉")

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)
        if userbot:
            await userbot.stop()

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id

    # Check if there is an active batch process for the user
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False  # Set the loop status to False
        await app.send_message(
            message.chat.id, 
            "Batch processing has been stopped successfully. You can start a new batch now if you want."
        )
    elif user_id in users_loop and not users_loop[user_id]:
        await app.send_message(
            message.chat.id, 
            "The batch process was already stopped. No active batch to cancel."
        )
    else:
        await app.send_message(
            message.chat.id, 
            "No active batch processing is running to cancel."
        )

@app.on_message(filters.command("bot") & filters.private)
async def bot_command(_, message):
    """Handle /bot command"""
    user_id = message.chat.id
    
    # Check if user is premium or owner
    if user_id not in OWNER_ID and not await is_user_verified(user_id):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get Premium", url="https://telegram.dog/shimps_bot")]
        ])
        await message.reply_text(
            "❌ This feature is only available for premium users.\n\n"
            "🔒 Free users cannot access this feature.\n"
            "💎 Upgrade to premium to unlock this and other exclusive features!",
            reply_markup=buttons
        )
        return
        
    await message.reply_text(
        "🤖 **Bot Description Download Instructions**\n\n"
        "1. Get the bot's username:\n"
        "   - Open the bot's profile\n"
        "   - Copy the username (without @)\n\n"
        "2. Modify the link format:\n"
        "   - Original: https://t.me/bot_username\n"
        "   - Modified: https://t.me/b/bot_username\n\n"
        "3. Send the modified link to download the content\n\n"
        "⚠️ Important Notes:\n"
        "• The bot must be public\n"
        "• The bot must have a description\n"
        "• Works with all types of media in description"
    )

@app.on_message(filters.command("pm") & filters.private)
async def pm_command(_, message):
    """Handle /pm command"""
    user_id = message.chat.id
    
    # Check if user is premium or owner
    if user_id not in OWNER_ID and not await is_user_verified(user_id):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get Premium", url="https://telegram.dog/shimps_bot")]
        ])
        await message.reply_text(
            "❌ This feature is only available for premium users.\n\n"
            "🔒 Free users cannot access this feature.\n"
            "💎 Upgrade to premium to unlock this and other exclusive features!",
            reply_markup=buttons
        )
        return
        
    await message.reply_text(
        "📱 **Private Chat Download Instructions**\n\n"
        "1. Get the message link from Telegram:\n"
        "   - Open the message\n"
        "   - Click three dots (⋮)\n"
        "   - Select 'Copy Link'\n\n"
        "2. Modify the link format:\n"
        "   - Original: tg://openmessage?user_id=123456789&message_id=123\n"
        "   - Modified: https://t.me/p/username&123\n\n"
        "3. Send the modified link to download the content\n\n"
        "⚠️ Important Notes:\n"
        "• Use the user's username (without @)\n"
        "• The user must not have blocked you\n"
        "• For view-once messages, send the link quickly\n"
        "• Works with all types of media (photos, videos, documents, etc.)"
    )

@app.on_message(
    filters.regex(r'tg://openmessage\?user_id=\d+&message_id=\d+')
    & filters.private
)
async def handle_private_message(_, message):
    user_id = message.chat.id
    
    # Check if user is owner or premium
    if user_id not in OWNER_ID and await chk_user(message, user_id) == 1:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Get Premium", url="https://telegram.dog/shimps_bot")]
        ])
        await message.reply(
            "❌ This feature is only available for premium users.\n\n"
            "🔒 Free users cannot access this feature.\n"
            "💎 Upgrade to premium to unlock this and other exclusive features!",
            reply_markup=buttons
        )
        return

    # Check if user is already in a loop
    if users_loop.get(user_id, False):
        await message.reply(
            "You already have an ongoing process. Please wait for it to finish or cancel it with /cancel."
        )
        return

    # Check subscription
    if await subscribe(_, message) == 1:
        return

    # Add user to the loop
    users_loop[user_id] = True
    msg = await message.reply("Processing...")
    userbot = await initialize_userbot(user_id)

    try:
        if not userbot:
            await msg.edit_text("❌ You need to login first. Use /login command to authenticate.")
            return

        # Parse the link
        link = message.text
        params = dict(param.split('=') for param in link.split('?')[1].split('&'))
        target_user_id = int(params['user_id'])
        message_id = int(params['message_id'])

        # Get the message
        try:
            target_msg = await userbot.get_messages(target_user_id, message_id)
            
            if not target_msg:
                await msg.edit_text("Message not found or has expired.")
                return

            if target_msg.empty:
                await msg.edit_text("Message is empty or has been deleted.")
                return

            if target_msg.service:
                await msg.edit_text("Cannot process service messages.")
                return

            # Handle different message types
            if target_msg.media:
                await msg.edit_text("Downloading media...")
                file = await userbot.download_media(
                    target_msg,
                    progress=progress_bar,
                    progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", msg, time.time())
                )

                if not file:
                    await msg.edit_text("Failed to download media.")
                    return

                # Get caption
                caption = target_msg.caption.markdown if target_msg.caption else None

                # Handle different media types
                if target_msg.photo:
                    await msg.edit_text("Uploading photo...")
                    result = await app.send_photo(user_id, file, caption=caption)
                elif target_msg.video:
                    await msg.edit_text("Uploading video...")
                    result = await app.send_video(user_id, file, caption=caption)
                elif target_msg.document:
                    await msg.edit_text("Uploading document...")
                    result = await app.send_document(user_id, file, caption=caption)
                elif target_msg.audio:
                    await msg.edit_text("Uploading audio...")
                    result = await app.send_audio(user_id, file, caption=caption)
                elif target_msg.voice:
                    await msg.edit_text("Uploading voice message...")
                    result = await app.send_voice(user_id, file)
                else:
                    await msg.edit_text("Unsupported media type.")
                    return

                if result:
                    await result.copy(LOG_GROUP)
                    await msg.delete()
                else:
                    await msg.edit_text("Failed to upload media.")

            elif target_msg.text:
                await msg.edit_text("Sending text message...")
                result = await app.send_message(user_id, target_msg.text.markdown)
                if result:
                    await result.copy(LOG_GROUP)
                    await msg.delete()
                else:
                    await msg.edit_text("Failed to send text message.")

            else:
                await msg.edit_text("No media or text found in the message.")

        except Exception as e:
            await msg.edit_text(f"Error processing message: {str(e)}")

    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")
    finally:
        users_loop[user_id] = False
        if userbot:
            await userbot.stop()
        try:
            await msg.delete()
        except Exception:
            pass
