# ---------------------------------------------------
# File Name: get_func.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-02-01
# Version: 2.0.5
# License: MIT License
# Improved logic handles
# ---------------------------------------------------

import asyncio
import time
import gc
import os
import re
from typing import Callable
from devgagan import app
import aiofiles
from devgagan import sex as gf
from telethon.tl.types import DocumentAttributeVideo, Message
from telethon.sessions import StringSession
import pymongo
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid
from pyrogram.enums import MessageMediaType, ParseMode
from devgagan.core.func import *
from pyrogram.errors import RPCError
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH
from devgagan.core.mongo import db as odb
from telethon import TelegramClient, events, Button
from devgagantools import fast_upload
import math

# Try to import devgagantools, fallback if not available
try:
    from devgagantools import fast_upload
    FAST_UPLOAD_AVAILABLE = True
except ImportError:
    logger.warning("devgagantools not available, Telethon uploads will be limited")
    FAST_UPLOAD_AVAILABLE = False
    fast_upload = None

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

# MongoDB database name and collection name
DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"

VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', '3gp', 'ts', 'm4v', 'f4v', 'vob']
DOCUMENT_EXTENSIONS = ['pdf', 'docs']

mongo_app = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_app[DB_NAME]
collection = db[COLLECTION_NAME]

if STRING:
    from devgagan import pro
    print("App imported by shimperd.")
else:
    pro = None
    print("STRING is not available. 'app' is set to None.")
    
async def fetch_upload_method(user_id):
    """Fetch the user's preferred upload method."""
    user_data = collection.find_one({"user_id": user_id})
    return user_data.get("upload_method", "Pyrogram") if user_data else "Pyrogram"

async def format_caption_to_html(caption: str) -> str:
    caption = re.sub(r"^> (.*)", r"<blockquote>\1</blockquote>", caption, flags=re.MULTILINE)
    caption = re.sub(r"```(.*?)```", r"<pre>\1</pre>", caption, flags=re.DOTALL)
    caption = re.sub(r"`(.*?)`", r"<code>\1</code>", caption)
    caption = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", caption)
    caption = re.sub(r"\*(.*?)\*", r"<b>\1</b>", caption)
    caption = re.sub(r"__(.*?)__", r"<i>\1</i>", caption)
    caption = re.sub(r"_(.*?)_", r"<i>\1</i>", caption)
    caption = re.sub(r"~~(.*?)~~", r"<s>\1</s>", caption)
    caption = re.sub(r"\|\|(.*?)\|\|", r"<details>\1</details>", caption)
    caption = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', caption)
    return caption.strip() if caption else None
    


async def upload_media(sender, target_chat_id, file, caption, edit, topic_id):
    try:
        upload_method = await fetch_upload_method(sender)  # Fetch the upload method (Pyrogram or Telethon)
        metadata = video_metadata(file)
        width, height, duration = metadata['width'], metadata['height'], metadata['duration']
        thumb_path = None
        
        try:
            # Get user's saved thumbnail or generate one
            thumb_path = thumbnail(sender)
            if not thumb_path and file.split('.')[-1].lower() in {'mp4', 'mkv', 'avi', 'mov'}:
                thumb_path = await screenshot(file, duration, sender)
                if not thumb_path:
                    print(f"Failed to generate thumbnail for {file}")
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            thumb_path = None

        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        document_formats = {'pdf', 'docx', 'txt', 'epub'}
        image_formats = {'jpg', 'png', 'jpeg'}

        # Pyrogram upload with optimized performance
        if upload_method == "Pyrogram":
            try:
                if file.split('.')[-1].lower() in video_formats:
                    dm = await app.send_video(
                        chat_id=target_chat_id,
                        video=file,
                        caption=caption,
                        height=height,
                        width=width,
                        duration=duration,
                        thumb=thumb_path,
                        reply_to_message_id=topic_id,
                        parse_mode=ParseMode.MARKDOWN,
                        progress=progress_bar,
                        progress_args=("╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────", edit, time.time())
                    )
                    await dm.copy(LOG_GROUP)
                    
                elif file.split('.')[-1].lower() in image_formats:
                    dm = await app.send_photo(
                        chat_id=target_chat_id,
                        photo=file,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        progress=progress_bar,
                        reply_to_message_id=topic_id,
                        progress_args=("╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────", edit, time.time())
                    )
                    await dm.copy(LOG_GROUP)
                else:
                    dm = await app.send_document(
                        chat_id=target_chat_id,
                        document=file,
                        caption=caption,
                        thumb=thumb_path,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        parse_mode=ParseMode.MARKDOWN,
                        progress_args=("╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────", edit, time.time())
                    )
                    await asyncio.sleep(1)  # Reduced sleep time
                    await dm.copy(LOG_GROUP)
                    
            except Exception as e:
                await app.send_message(LOG_GROUP, f"**Upload Failed:** {str(e)}")
                print(f"Error during Pyrogram upload: {e}")
                raise

        # Telethon upload with optimized performance
        elif upload_method == "Telethon":
            try:
                if not FAST_UPLOAD_AVAILABLE:
                    await edit.edit_text("Telethon upload not available (devgagantools missing)")
                    return
                    
                await edit.delete()
                progress_message = await gf.send_message(sender, "**__Uploading...__**")
                caption = await format_caption_to_html(caption)
                
                # Use asyncio.create_task for better performance
                upload_task = asyncio.create_task(
                    fast_upload(
                        gf, file,
                        reply=progress_message,
                        name=None,
                        progress_bar_function=lambda done, total: progress_callback(done, total, sender)
                    )
                )
                
                uploaded = await upload_task
                await progress_message.delete()

                attributes = [
                    DocumentAttributeVideo(
                        duration=duration,
                        w=width,
                        h=height,
                        supports_streaming=True
                    )
                ] if file.split('.')[-1].lower() in video_formats else []

                # Send to target chat
                await gf.send_file(
                    target_chat_id,
                    uploaded,
                    caption=caption,
                    attributes=attributes,
                    reply_to=topic_id,
                    thumb=thumb_path
                )
                
                # Send to log group
                await gf.send_file(
                    LOG_GROUP,
                    uploaded,
                    caption=caption,
                    attributes=attributes,
                    thumb=thumb_path
                )
                
            except Exception as e:
                await app.send_message(LOG_GROUP, f"**Telethon Upload Failed:** {str(e)}")
                print(f"Error during Telethon upload: {e}")
                raise

    except Exception as e:
        await app.send_message(LOG_GROUP, f"**Upload Failed:** {str(e)}")
        print(f"Error during media upload: {e}")
        raise

    finally:
        # Only remove auto-generated thumbnails after successful upload, and not user-set ones
        try:
            if thumb_path and os.path.exists(thumb_path) and thumb_path != f'{sender}.jpg':
                await asyncio.sleep(1)  # Reduced delay
                os.remove(thumb_path)
        except Exception as e:
            print(f"Error removing thumbnail: {e}")
        
        # Force garbage collection
        gc.collect()


async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    try:
        # Add timeout to prevent hanging
        timeout = 3000  # 50 minutes timeout
        
        # Parse the message link
        if "t.me/p/" in msg_link:
            # Handle private user links
            try:
                username, msg_id = await extract_private_user_info(msg_link)
                chat = await resolve_username(userbot, username)
                if not chat:
                    await app.edit_message_text(sender, edit_id, "Could not resolve username")
                    return
            except Exception as e:
                print(f"Error processing private user link: {e}")
                await app.edit_message_text(sender, edit_id, f"Error processing private link: {str(e)}")
                return
        else:
            # Handle normal Telegram links
            try:
                chat, msg_id = await parse_telegram_link(msg_link, i)
                if not chat:
                    await app.edit_message_text(sender, edit_id, "Could not parse link")
                    return
            except Exception as e:
                print(f"Error processing public link: {e}")
                await app.edit_message_text(sender, edit_id, f"Error processing link: {str(e)}")
                return
            
        # Fetch the target message with timeout
        try:
            msg = await asyncio.wait_for(
                userbot.get_messages(chat, msg_id),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            await app.edit_message_text(sender, edit_id, "Timeout: Message fetch took too long")
            return
        except Exception as e:
            await app.edit_message_text(sender, edit_id, f"Error fetching message: {str(e)}")
            return
            
        if not msg or msg.service or msg.empty:
            await app.edit_message_text(sender, edit_id, "Message not found or is a service message")
            return

        target_chat_id = user_chat_ids.get(message.chat.id, message.chat.id)
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different message types efficiently
        if msg.media == MessageMediaType.WEB_PAGE_PREVIEW:
            await clone_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.text:
            await clone_text_message(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        if msg.sticker:
            await handle_sticker(app, msg, target_chat_id, topic_id, edit_id, LOG_GROUP)
            return

        # Handle file media (photo, document, video)
        file_size = get_message_file_size(msg)
        free_check = await chk_user(message.chat.id, sender)
        size_limit = 2 * 1024 * 1024 * 1024  # 2GB size limit

        file_name = await get_media_filename(msg)
        edit = await app.edit_message_text(sender, edit_id, "**Downloading...**")

        # Download media with timeout and better error handling
        try:
            file = await asyncio.wait_for(
                userbot.download_media(
                    msg,
                    file_name=file_name,
                    progress=progress_bar,
                    progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", edit, time.time())
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            await edit.edit_text("Download timeout: File is too large or connection is slow")
            return
        except Exception as e:
            await edit.edit_text(f"Download failed: {str(e)}")
            return
        
        if not file:
            await edit.edit_text("Failed to download media")
            return
            
        caption = await get_final_caption(msg, sender)

        # Rename file
        try:
            file = await rename_file(file, sender)
        except Exception as e:
            print(f"Error renaming file: {e}")
            # Continue with original filename

        # Handle specific media types
        if msg.audio:
            result = await app.send_audio(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete()
            return
        
        if msg.voice:
            result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete()
            return

        if msg.photo:
            result = await app.send_photo(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete()
            return

        # Upload media with size checking
        if file_size > size_limit and (free_check == 1 or pro is None):
            await edit.delete()
            await split_and_upload_file(app, sender, target_chat_id, file, caption, topic_id)
            return       
        elif file_size > size_limit:
            await handle_large_file(file, sender, edit, caption)
        else:
            await upload_media(sender, target_chat_id, file, caption, edit, topic_id)

    except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
        await app.edit_message_text(sender, edit_id, "Have you joined the channel?")
    except Exception as e:
        print(f"Error in get_msg: {e}")
        await app.edit_message_text(sender, edit_id, f"An error occurred: {str(e)}")
    finally:
        # Clean up resources
        try:
            if 'file' in locals() and file and os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Error cleaning up file: {e}")
        
        try:
            if 'edit' in locals() and edit:
                await edit.delete()
        except Exception as e:
            print(f"Error deleting edit message: {e}")
        
        # Force garbage collection
        gc.collect()

async def clone_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    await devgaganin.copy(log_group)
    await edit.delete()

async def clone_text_message(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning text message...")
    devgaganin = await app.send_message(target_chat_id, msg.text.markdown, reply_to_message_id=topic_id)
    await devgaganin.copy(log_group)
    await edit.delete()


async def handle_sticker(app, msg, target_chat_id, topic_id, edit_id, log_group):
    edit = await app.edit_message_text(target_chat_id, edit_id, "Handling sticker...")
    result = await app.send_sticker(target_chat_id, msg.sticker.file_id, reply_to_message_id=topic_id)
    await result.copy(log_group)
    await edit.delete()


async def get_media_filename(msg):
    if msg.document:
        return msg.document.file_name
    if msg.video:
        return msg.video.file_name if msg.video.file_name else "temp.mp4"
    if msg.photo:
        return "temp.jpg"
    return "unknown_file"

def get_message_file_size(msg):
    if msg.document:
        return msg.document.file_size
    if msg.photo:
        return msg.photo.file_size
    if msg.video:
        return msg.video.file_size
    return 1

async def get_final_caption(msg, sender):
    # Handle caption based on the upload method
    if msg.caption:
        original_caption = msg.caption.markdown
    else:
        original_caption = ""
    
    custom_caption = get_user_caption_preference(sender)
    final_caption = f"{original_caption}\n\n{custom_caption}" if custom_caption else original_caption
    replacements = load_replacement_words(sender)
    for word, replace_word in replacements.items():
        final_caption = final_caption.replace(word, replace_word)
        
    return final_caption if final_caption else None


async def download_user_stories(userbot, chat_id, msg_id, edit, sender):
    try:
        # Fetch the story using the provided chat ID and message ID
        story = await userbot.get_stories(chat_id, msg_id)
        if not story:
            await edit.edit("No story available for this user.")
            return  
        if not story.media:
            await edit.edit("The story doesn't contain any media.")
            return
        await edit.edit("Downloading Story...")
        file_path = await userbot.download_media(story)
        print(f"Story downloaded: {file_path}")
        # Send the downloaded story based on its type
        if story.media:
            await edit.edit("Uploading Story...")
            if story.media == MessageMediaType.VIDEO:
                await app.send_video(sender, file_path)
            elif story.media == MessageMediaType.DOCUMENT:
                await app.send_document(sender, file_path)
            elif story.media == MessageMediaType.PHOTO:
                await app.send_photo(sender, file_path)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)  
        await edit.edit("Story processed successfully.")
    except RPCError as e:
        print(f"Failed to fetch story: {e}")
        await edit.edit(f"Error: {e}")
        
async def copy_message_with_chat_id(app, userbot, sender, chat_id, message_id, edit):
    target_chat_id = user_chat_ids.get(sender, sender)
    file = None
    result = None
    size_limit = 2 * 1024 * 1024 * 1024  # 2 GB size limit

    try:
        # Check if userbot is available
        if not userbot:
            await edit.edit("❌ You need to login first. Use /login command to authenticate.")
            return

        # First try to get message directly
        try:
            msg = await app.get_messages(chat_id, message_id)
        except Exception as e:
            # If direct message fetch fails, try resolving username
            await edit.edit("Resolving username...")
            success, response = await resolve_username(userbot, chat_id)
            if not success:
                await edit.edit(f"Error: {response}")
                return
            chat_id = response
            try:
                msg = await userbot.get_messages(chat_id, message_id)
            except Exception as e:
                await edit.edit(f"Failed to get message: {str(e)}")
                return

        if not msg or msg.service or msg.empty:
            await edit.edit("Message not found or is empty")
            return

        custom_caption = get_user_caption_preference(sender)
        final_caption = format_caption(msg.caption or '', sender, custom_caption)

        # Parse target_chat_id and topic_id
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different media types
        if msg.media:
            result = await send_media_message(app, target_chat_id, msg, final_caption, topic_id)
            if result:
                return
        elif msg.text:
            result = await app.copy_message(target_chat_id, chat_id, message_id, reply_to_message_id=topic_id)
            if result:
                return

        # If we reach here, we need to download and re-upload
        await edit.edit("Downloading media...")
        
        file = await userbot.download_media(
            msg,
            progress=progress_bar,
            progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", edit, time.time())
        )
        
        if not file:
            await edit.edit("Failed to download media")
            return
            
        file = await rename_file(file, sender)

        if msg.photo:
            result = await app.send_photo(target_chat_id, file, caption=final_caption, reply_to_message_id=topic_id)
        elif msg.video or msg.document:
            file_size = get_message_file_size(msg)
            freecheck = await chk_user(chat_id, sender)
            if file_size > size_limit and (freecheck == 1 or pro is None):
                await edit.delete()
                await split_and_upload_file(app, sender, target_chat_id, file, final_caption, topic_id)
                return       
            elif file_size > size_limit:
                await handle_large_file(file, sender, edit, final_caption)
                return
            await upload_media(sender, target_chat_id, file, final_caption, edit, topic_id)
        elif msg.audio:
            result = await app.send_audio(target_chat_id, file, caption=final_caption, reply_to_message_id=topic_id)
        elif msg.voice:
            result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
        elif msg.sticker:
            result = await app.send_sticker(target_chat_id, msg.sticker.file_id, reply_to_message_id=topic_id)
        else:
            await edit.edit("Unsupported media type")

    except Exception as e:
        print(f"Error : {e}")
        await edit.edit(f"Error occurred: {str(e)}")

    finally:
        if file and os.path.exists(file):
            os.remove(file)


async def send_media_message(app, target_chat_id, msg, caption, topic_id):
    try:
        if msg.video:
            if msg.video.file_id:
                return await app.send_video(
                    target_chat_id, 
                    msg.video.file_id, 
                    caption=caption, 
                    reply_to_message_id=topic_id,
                    width=msg.video.width,
                    height=msg.video.height,
                    duration=msg.video.duration
                )
        if msg.document:
            if msg.document.file_id:
                return await app.send_document(
                    target_chat_id, 
                    msg.document.file_id, 
                    caption=caption, 
                    reply_to_message_id=topic_id
                )
        if msg.photo:
            if msg.photo.file_id:
                return await app.send_photo(
                    target_chat_id, 
                    msg.photo.file_id, 
                    caption=caption, 
                    reply_to_message_id=topic_id
                )
    except Exception as e:
        print(f"Error while sending media: {e}")
        # If sending media by file_id fails, fallback to copy_message
        try:
            return await app.copy_message(
                target_chat_id, 
                msg.chat.id, 
                msg.id, 
                reply_to_message_id=topic_id
            )
        except Exception as copy_error:
            print(f"Error during copy_message fallback: {copy_error}")
    
    return None

    
# ------------------------ Button Mode Editz FOR SETTINGS ----------------------------

# Define a dictionary to store user chat IDs
user_chat_ids = {}

def load_user_data(user_id, key, default_value=None):
    try:
        user_data = collection.find_one({"_id": user_id})
        return user_data.get(key, default_value) if user_data else default_value
    except Exception as e:
        print(f"Error loading {key}: {e}")
        return default_value

def load_saved_channel_ids():
    saved_channel_ids = set()
    try:
        # Retrieve channel IDs from MongoDB collection
        for channel_doc in collection.find({"channel_id": {"$exists": True}}):
            saved_channel_ids.add(channel_doc["channel_id"])
    except Exception as e:
        print(f"Error loading saved channel IDs: {e}")
    return saved_channel_ids

def save_user_data(user_id, key, value):
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {key: value}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving {key}: {e}")


# Delete and replacement word functions
load_delete_words = lambda user_id: set(load_user_data(user_id, "delete_words", []))
save_delete_words = lambda user_id, words: save_user_data(user_id, "delete_words", list(words))

load_replacement_words = lambda user_id: load_user_data(user_id, "replacement_words", {})
save_replacement_words = lambda user_id, replacements: save_user_data(user_id, "replacement_words", replacements)

# User session functions
def load_user_session(user_id):
    return load_user_data(user_id, "session")

# Upload preference functions
set_dupload = lambda user_id, value: save_user_data(user_id, "dupload", value)
get_dupload = lambda user_id: load_user_data(user_id, "dupload", False)

# User preferences storage
user_rename_preferences = {}
user_caption_preferences = {}

# Rename and caption preference functions
async def set_rename_command(user_id, custom_rename_tag):
    user_rename_preferences[str(user_id)] = custom_rename_tag

get_user_rename_preference = lambda user_id: user_rename_preferences.get(str(user_id), 'Shimperd')

async def set_caption_command(user_id, custom_caption):
    user_caption_preferences[str(user_id)] = custom_caption

get_user_caption_preference = lambda user_id: user_caption_preferences.get(str(user_id), 'Shimperd')

# Initialize the dictionary to store user sessions

sessions = {}
m = None
SET_PIC = "settings.jpg"
MESS = "Customize by your end and Configure your settings ..."

@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    user_id = event.sender_id
    await send_settings_message(event.chat_id, user_id)

async def send_settings_message(chat_id, user_id):
    
    # Define the rest of the buttons
    buttons = [
        [Button.inline("Set Chat ID", b'setchat'), Button.inline("Set Rename Tag", b'setrename')],
        [Button.inline("Caption", b'setcaption'), Button.inline("Replace Words", b'setreplacement')],
        [Button.inline("Remove Words", b'delete'), Button.inline("Reset", b'reset')],
        [Button.inline("Session Login", b'addsession'), Button.inline("Logout", b'logout')],
        [Button.inline("Set Thumbnail", b'setthumb'), Button.inline("Remove Thumbnail", b'remthumb')],
        [Button.inline("PDF Wtmrk", b'pdfwt'), Button.inline("Video Wtmrk", b'watermark')],
        [Button.inline("Upload Method", b'uploadmethod')],  # Include the dynamic Fast DL button
        [Button.url("Report Errors", "https://telegram.dog/shimps_bot")]
    ]

    await gf.send_file(
        chat_id,
        file=SET_PIC,
        caption=MESS,
        buttons=buttons
    )


pending_photos = {}

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id
    
    if event.data == b'setchat':
        await event.respond("Send me the ID of that chat:")
        sessions[user_id] = 'setchat'

    elif event.data == b'setrename':
        await event.respond("Send me the rename tag:")
        sessions[user_id] = 'setrename'
    
    elif event.data == b'setcaption':
        await event.respond("Send me the caption:")
        sessions[user_id] = 'setcaption'

    elif event.data == b'setreplacement':
        await event.respond("Send me the replacement words in the format: 'WORD(s)' 'REPLACEWORD'")
        sessions[user_id] = 'setreplacement'

    elif event.data == b'addsession':
        await event.respond("Send Pyrogram V2 session")
        sessions[user_id] = 'addsession' # (If you want to enable session based login just uncomment this and modify response message accordingly)

    elif event.data == b'delete':
        await event.respond("Send words seperated by space to delete them from caption/filename ...")
        sessions[user_id] = 'deleteword'
        
    elif event.data == b'logout':
        await odb.remove_session(user_id)
        user_data = await odb.get_data(user_id)
        if user_data and user_data.get("session") is None:
            await event.respond("Logged out and deleted session successfully.")
        else:
            await event.respond("You are not logged in.")
        
    elif event.data == b'setthumb':
        pending_photos[user_id] = True
        await event.respond('Please send the photo you want to set as the thumbnail.')
    
    elif event.data == b'pdfwt':
        await event.respond("Watermark is Pro+ Plan.. contact @shimps_bot")
        return

    elif event.data == b'uploadmethod':
        # Retrieve the user's current upload method (default to Pyrogram)
        user_data = collection.find_one({'user_id': user_id})
        current_method = user_data.get('upload_method', 'Pyrogram') if user_data else 'Pyrogram'
        pyrogram_check = " ✅" if current_method == "Pyrogram" else ""
        telethon_check = " ✅" if current_method == "Telethon" else ""

        # Display the buttons for selecting the upload method
        buttons = [
            [Button.inline(f"Pyrogram v2{pyrogram_check}", b'pyrogram')],
            [Button.inline(f"SpyLib v1 ⚡{telethon_check}", b'telethon')]
        ]
        await event.edit("Choose your preferred upload method:\n\n__**Note:** **shimp Lib ⚡**, built on Telethon(base), by shimperd still in beta.__", buttons=buttons)

    elif event.data == b'pyrogram':
        save_user_upload_method(user_id, "Pyrogram")
        await event.edit("Upload method set to **Pyrogram** ✅")

    elif event.data == b'telethon':
        save_user_upload_method(user_id, "Telethon")
        await event.edit("Upload method set to **Shimp Lib ⚡\n\nThanks for choosing this library as it will help me to analyze the error raise issues on github.** ✅")        
        
    elif event.data == b'reset':
        try:
            user_id_str = str(user_id)
            
            collection.update_one(
                {"_id": user_id},
                {"$unset": {
                    "delete_words": "",
                    "replacement_words": "",
                    "watermark_text": "",
                    "duration_limit": ""
                }}
            )
            
            collection.update_one(
                {"user_id": user_id},
                {"$unset": {
                    "delete_words": "",
                    "replacement_words": "",
                    "watermark_text": "",
                    "duration_limit": ""
                }}
            )            
            user_chat_ids.pop(user_id, None)
            user_rename_preferences.pop(user_id_str, None)
            user_caption_preferences.pop(user_id_str, None)
            thumbnail_path = f"{user_id}.jpg"
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            await event.respond("✅ Reset successfully, to logout click /logout")
        except Exception as e:
            await event.respond(f"Error clearing delete list: {e}")
    
    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('Thumbnail removed successfully!')
        except FileNotFoundError:
            await event.respond("No thumbnail found to remove.")
    

@gf.on(events.NewMessage(func=lambda e: e.sender_id in pending_photos))
async def save_thumbnail(event):
    user_id = event.sender_id  # Use event.sender_id as user_id

    if event.photo:
        temp_path = await event.download_media()
        if os.path.exists(f'{user_id}.jpg'):
            os.remove(f'{user_id}.jpg')
        os.rename(temp_path, f'./{user_id}.jpg')
        await event.respond('Thumbnail saved successfully!')

    else:
        await event.respond('Please send a photo... Retry')

    # Remove user from pending photos dictionary in both cases
    pending_photos.pop(user_id, None)

def save_user_upload_method(user_id, method):
    # Save or update the user's preferred upload method
    collection.update_one(
        {'user_id': user_id},  # Query
        {'$set': {'upload_method': method}},  # Update
        upsert=True  # Create a new document if one doesn't exist
    )

@gf.on(events.NewMessage)
async def handle_user_input(event):
    user_id = event.sender_id
    if user_id in sessions:
        session_type = sessions[user_id]

        if session_type == 'setchat':
            try:
                chat_id = event.text
                user_chat_ids[user_id] = chat_id
                await event.respond("Chat ID set successfully!")
            except ValueError:
                await event.respond("Invalid chat ID!")
                
        elif session_type == 'setrename':
            custom_rename_tag = event.text
            await set_rename_command(user_id, custom_rename_tag)
            await event.respond(f"Custom rename tag set to: {custom_rename_tag}")
        
        elif session_type == 'setcaption':
            custom_caption = event.text
            await set_caption_command(user_id, custom_caption)
            await event.respond(f"Custom caption set to: {custom_caption}")

        elif session_type == 'setreplacement':
            match = re.match(r"'(.+)' '(.+)'", event.text)
            if not match:
                await event.respond("Usage: 'WORD(s)' 'REPLACEWORD'")
            else:
                word, replace_word = match.groups()
                delete_words = load_delete_words(user_id)
                if word in delete_words:
                    await event.respond(f"The word '{word}' is in the delete set and cannot be replaced.")
                else:
                    replacements = load_replacement_words(user_id)
                    replacements[word] = replace_word
                    save_replacement_words(user_id, replacements)
                    await event.respond(f"Replacement saved: '{word}' will be replaced with '{replace_word}'")

        elif session_type == 'addsession':
            session_string = event.text
            await odb.set_session(user_id, session_string)
            await event.respond("✅ Session string added successfully!")
                
        elif session_type == 'deleteword':
            words_to_delete = event.message.text.split()
            delete_words = load_delete_words(user_id)
            delete_words.update(words_to_delete)
            save_delete_words(user_id, delete_words)
            await event.respond(f"Words added to delete list: {', '.join(words_to_delete)}")
               
            
        del sessions[user_id]
    
# Command to store channel IDs
@gf.on(events.NewMessage(incoming=True, pattern='/lock'))
async def lock_command_handler(event):
    if event.sender_id not in OWNER_ID:
        return await event.respond("You are not authorized to use this command.")
    
    # Extract the channel ID from the command
    try:
        channel_id = int(event.text.split(' ')[1])
    except (ValueError, IndexError):
        return await event.respond("Invalid /lock command. Use /lock CHANNEL_ID.")
    
    # Save the channel ID to the MongoDB database
    try:
        # Insert the channel ID into the collection
        collection.insert_one({"channel_id": channel_id})
        await event.respond(f"Channel ID {channel_id} locked successfully.")
    except Exception as e:
        await event.respond(f"Error occurred while locking channel ID: {str(e)}")


async def handle_large_file(file, sender, edit, caption):
    if pro is None:
        await edit.edit('**__ ❌ 4GB trigger not found__**')
        os.remove(file)
        gc.collect()
        return
    
    dm = None
    
    print("4GB connector found.")
    await edit.edit('**__ ✅ 4GB trigger connected...__**\n\n')
    
    target_chat_id = user_chat_ids.get(sender, sender)
    file_extension = str(file).split('.')[-1].lower()
    metadata = video_metadata(file)
    duration = metadata['duration']
    width = metadata['width']
    height = metadata['height']
    
    thumb_path = await screenshot(file, duration, sender)
    try:
        if file_extension in VIDEO_EXTENSIONS:
            dm = await pro.send_video(
                LOG_GROUP,
                video=file,
                caption=caption,
                thumb=thumb_path,
                height=height,
                width=width,
                duration=duration,
                progress=progress_bar,
                progress_args=(
                    "╭─────────────────────╮\n│       **__4GB Uploader__ ⚡**\n├─────────────────────",
                    edit,
                    time.time()
                )
            )
        else:
            # Send as document
            dm = await pro.send_document(
                LOG_GROUP,
                document=file,
                caption=caption,
                thumb=thumb_path,
                progress=progress_bar,
                progress_args=(
                    "╭─────────────────────╮\n│      **__4GB Uploader ⚡__**\n├─────────────────────",
                    edit,
                    time.time()
                )
            )

        from_chat = dm.chat.id
        msg_id = dm.id
        freecheck = 0
        if freecheck == 1:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("💎 Get Premium to Forward", url="https://telegram.dog/shimps_bot")]
                ]
            )
            await app.copy_message(
                target_chat_id,
                from_chat,
                msg_id,
                protect_content=True,
                reply_markup=reply_markup
            )
        else:
            # Simple copy without protect_content or reply_markup
            await app.copy_message(
                target_chat_id,
                from_chat,
                msg_id
            )
            
    except Exception as e:
        print(f"Error while sending file: {e}")

    finally:
        await edit.delete()
        os.remove(file)
        gc.collect()
        return

async def rename_file(file, sender):
    try:
        delete_words = load_delete_words(sender)
        custom_rename_tag = get_user_rename_preference(sender)
        replacements = load_replacement_words(sender)
        
        print(f"Original file: {file}")
        print(f"Delete words: {delete_words}")
        print(f"Custom rename tag: {custom_rename_tag}")
        print(f"Replacements: {replacements}")
        
        # Get the directory and filename separately
        directory = os.path.dirname(str(file))
        filename = os.path.basename(str(file))
        
        # Remove _app_downloads prefix from both directory and filename
        directory = directory.replace("_app_downloads", "")
        filename = filename.replace("_app_downloads", "")
        
        # Reconstruct the file path without _app_downloads
        file = os.path.join(directory, filename) if directory else filename
        
        last_dot_index = str(file).rfind('.')
        
        if last_dot_index != -1 and last_dot_index != 0:
            ggn_ext = str(file)[last_dot_index + 1:]
            
            if ggn_ext.isalpha() and len(ggn_ext) <= 9:
                if ggn_ext.lower() in VIDEO_EXTENSIONS:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = 'mp4'
                else:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = ggn_ext
            else:
                original_file_name = str(file)[:last_dot_index]
                file_extension = 'mp4'
        else:
            original_file_name = str(file)
            file_extension = 'mp4'
            
        print(f"Original filename: {original_file_name}")
        print(f"File extension: {file_extension}")
        
        # Apply delete words
        for word in delete_words:
            original_file_name = original_file_name.replace(word, "")
            print(f"After deleting '{word}': {original_file_name}")

        # Apply replacements
        for word, replace_word in replacements.items():
            original_file_name = original_file_name.replace(word, replace_word)
            print(f"After replacing '{word}' with '{replace_word}': {original_file_name}")

        # Sanitize the filename
        original_file_name = await sanitize(original_file_name)
        print(f"After sanitizing: {original_file_name}")
        
        # One final check to remove any remaining _app_downloads prefix
        original_file_name = original_file_name.replace("_app_downloads", "")
        
        new_file_name = f"{original_file_name} {custom_rename_tag}.{file_extension}"
        print(f"Final new filename: {new_file_name}")
        
        # Get the original file path to rename
        original_file_path = str(file)
        if directory:
            new_file_path = os.path.join(directory, new_file_name)
        else:
            new_file_path = new_file_name
        
        # Ensure no _app_downloads in the final path
        new_file_path = new_file_path.replace("_app_downloads", "")
            
        await asyncio.to_thread(os.rename, original_file_path, new_file_path)
        print(f"File renamed successfully to: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"Error in rename_file: {e}")
        return file  # Return original file if rename fails


async def sanitize(file_name: str) -> str:
    # First remove _app_downloads prefix if it exists
    file_name = file_name.replace("_app_downloads", "")
    # Then sanitize invalid characters
    sanitized_name = re.sub(r'[\\/:"*?<>|]', '_', file_name)
    # Strip leading/trailing whitespaces and remove _app_downloads again
    sanitized_name = sanitized_name.strip().replace("_app_downloads", "")
    # Remove any leading underscores
    sanitized_name = sanitized_name.lstrip('_')
    return sanitized_name
    
async def is_file_size_exceeding(file_path, size_limit):
    try:
        return os.path.getsize(file_path) > size_limit
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    except Exception as e:
        print(f"Error while checking file size: {e}")
        return False


user_progress = {}

def progress_callback(done, total, user_id):
    # Check if this user already has progress tracking
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    
    # Retrieve the user's tracking data
    user_data = user_progress[user_id]
    
    # Calculate the percentage of progress
    percent = (done / total) * 100
    
    # Format the progress bar
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    # Convert done and total to MB for easier reading
    done_mb = done / (1024 * 1024)  # Convert bytes to MB
    total_mb = total / (1024 * 1024)
    
    # Calculate the upload speed (in bytes per second)
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time  # Speed in bytes per second
        speed_mbps = (speed_bps * 8) / (1024 * 1024)  # Speed in Mbps
    else:
        speed_mbps = 0
    
    # Estimated time remaining (in seconds)
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    
    # Convert remaining time to minutes
    remaining_time_min = remaining_time / 60
    
    # Format the final output as needed
    final = (
        f"╭──────────────────╮\n"
        f"│     **__Shimp Lib ⚡ Uploader__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__ETA:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Powered by Shimperd__**"
    )
    
    # Update tracking variables for the user
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    
    return final


def dl_progress_callback(done, total, user_id):
    # Check if this user already has progress tracking
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    
    # Retrieve the user's tracking data
    user_data = user_progress[user_id]
    
    # Calculate the percentage of progress
    percent = (done / total) * 100
    
    # Format the progress bar
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    # Convert done and total to MB for easier reading
    done_mb = done / (1024 * 1024)  # Convert bytes to MB
    total_mb = total / (1024 * 1024)
    
    # Calculate the upload speed (in bytes per second)
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time  # Speed in bytes per second
        speed_mbps = (speed_bps * 8) / (1024 * 1024)  # Speed in Mbps
    else:
        speed_mbps = 0
    
    # Estimated time remaining (in seconds)
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    
    # Convert remaining time to minutes
    remaining_time_min = remaining_time / 60
    
    # Format the final output as needed
    final = (
        f"╭──────────────────╮\n"
        f"│     **__Shimp Lib ⚡ Downloader__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__ETA:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Powered by Shimperd__**"
    )
    
    # Update tracking variables for the user
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    
    return final

# split function .... ?( to handle gareeb bot coder jo string n lga paaye)

def split_progress_callback(current, total, part_number, total_parts):
    """Progress callback function specifically for file splitting operations."""
    percent = (current / total) * 100
    
    # Format the progress bar
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    # Format the final output
    final = (
        f"╭──────────────────╮\n"
        f"│     **__File Splitting Progress__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Overall:__** Part {part_number}/{total_parts}\n"
        f"│ **__Current Part:__** {percent:.2f}%\n"
        f"│ **__Done:__** {current / (1024 * 1024):.2f} MB / {total / (1024 * 1024):.2f} MB\n"
        f"╰──────────────────╯\n\n"
        f"**__Please wait while the file is being prepared__**"
    )
    
    return final

async def split_and_upload_file(app, sender, target_chat_id, file_path, caption, topic_id):
    if not os.path.exists(file_path):
        await app.send_message(sender, "❌ File not found!")
        return

    file_size = os.path.getsize(file_path)
    # Set part size to 1.9 GB to ensure it stays under Telegram's 2GB limit
    PART_SIZE = int(1.9 * 1024 * 1024 * 1024)  # 1.9 GB in bytes, converted to integer
    BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer for reading/writing to reduce memory usage
    total_parts = math.ceil(file_size / PART_SIZE)
    
    # Send initial notification message with detailed info
    start = await app.send_message(
        sender, 
        f"⚙️ **File Processing Started**\n\n"
        f"• **File Size:** {file_size / (1024 * 1024 * 1024):.2f} GB\n"
        f"• **Parts:** {total_parts} (max 1.9GB each)\n"
        f"• **Status:** Preparing to split file..."
    )
    
    part_number = 0
    try:
        file_handle = await aiofiles.open(file_path, mode="rb")
        try:
            bytes_read_total = 0
            while bytes_read_total < file_size:
                # Show splitting progress
                if part_number > 0:
                    await start.edit_text(
                        f"⚙️ **File Processing**\n\n"
                        f"• **File Size:** {file_size / (1024 * 1024 * 1024):.2f} GB\n"
                        f"• **Parts:** {total_parts} (max 1.9GB each)\n"
                        f"• **Status:** Splitting in progress...\n"
                        f"• **Progress:** {part_number}/{total_parts} parts processed"
                    )
                    # Force garbage collection after each part to reduce memory usage
                    gc.collect()
                
                # Create part filename
                base_name, file_ext = os.path.splitext(file_path)
                part_file = f"{base_name}.part{str(part_number + 1).zfill(3)}{file_ext}"

                # Prepare progress message
                progress_update = await app.send_message(sender, f"📦 Preparing part {part_number + 1}/{total_parts}...")
                
                # Stream data in smaller chunks to part file
                bytes_written = 0
                part_file_handle = await aiofiles.open(part_file, mode="wb")
                try:
                    while bytes_written < PART_SIZE:
                        # Read a small buffer to avoid memory issues
                        chunk = await file_handle.read(min(BUFFER_SIZE, PART_SIZE - bytes_written))
                        if not chunk:
                            break
                            
                        # Update progress occasionally 
                        if bytes_written % (100 * 1024 * 1024) == 0:  # Every 100MB
                            percent = (bytes_written / PART_SIZE) * 100
                            await progress_update.edit_text(
                                f"📦 Preparing part {part_number + 1}/{total_parts}...\n"
                                f"Progress: {percent:.1f}% ({bytes_written / (1024 * 1024):.1f}MB)"
                            )
                            
                        await part_file_handle.write(chunk)
                        bytes_written += len(chunk)
                        bytes_read_total += len(chunk)
                        
                        # Break if we've reached the end of the file
                        if len(chunk) < BUFFER_SIZE:
                            break
                finally:
                    await part_file_handle.close()
                    
                # Delete progress message to clean up chat
                await progress_update.delete()

                # Skip empty parts (should only happen for the last part if it's empty)
                if bytes_written == 0:
                    break

                # Uploading part
                edit = await app.send_message(
                    target_chat_id, 
                    f"⬆️ **Uploading Part {part_number + 1}/{total_parts}**\n"
                    f"Progress: Starting upload..."
                )
                
                part_caption = f"{caption}\n\n**Part {part_number + 1}/{total_parts}**"
                
                try:
                    # Make sure all progress arguments are properly typed
                    await app.send_document(
                        chat_id=target_chat_id,
                        document=part_file,
                        caption=part_caption,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        progress_args=(
                            f"╭─────────────────────╮\n│ **__Part {part_number + 1}/{total_parts} Upload__**\n├─────────────────────", 
                            edit, 
                            int(time.time())
                        )
                    )
                except Exception as e:
                    error_msg = f"Error uploading part {part_number + 1}: {str(e)}"
                    await app.send_message(sender, error_msg)
                    raise Exception(error_msg)
                finally:
                    # Clean up resources immediately after each part
                    if os.path.exists(part_file):
                        os.remove(part_file)
                    await edit.delete()
                    # Force garbage collection after each part
                    gc.collect()

                part_number += 1
        finally:
            await file_handle.close()
            
        # All parts uploaded successfully
        await start.edit_text(
            f"✅ **File Upload Complete**\n\n"
            f"• **File Size:** {file_size / (1024 * 1024 * 1024):.2f} GB\n"
            f"• **Parts:** {total_parts}\n"
            f"• **Status:** All parts uploaded successfully!"
        )
        
    except Exception as e:
        await app.send_message(sender, f"❌ Error during file split/upload: {str(e)}")
        if os.path.exists(file_path):
            await start.edit_text(
                f"🚫 **Process Failed**\n\n"
                f"• **Error:** {str(e)}\n"
                f"• **Resolution:** Please try again or contact support"
            )
    finally:
        # Ensure cleanup happens in all cases
        try:
            # Clean up the original file
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # Keep the success message for a bit longer then delete
            await asyncio.sleep(5)
            await start.delete()
            
            # Force another garbage collection
            gc.collect()
        except Exception as cleanup_error:
            print(f"Cleanup error: {str(cleanup_error)}")

async def resolve_username(userbot, username):
    try:
        # Remove @ if present
        username = username.replace('@', '')
        
        # Check if it's a channel/group ID
        if username.startswith('-100'):
            return True, int(username)
            
        # Try to resolve the username
        try:
            entity = await userbot.get_entity(username)
            return True, entity.id
        except ValueError:
            return False, "Invalid username or channel ID"
        except Exception as e:
            return False, f"Error resolving username: {str(e)}"
            
    except Exception as e:
        return False, f"Error in username resolution: {str(e)}"

async def process_and_upload_link(userbot, user_id, edit_id, link, i, message):
    try:
        # Check if userbot is available for special links
        if any(x in link for x in ['t.me/b/', 't.me/c/', '/s/', 'tg://openmessage']) and not userbot:
            await app.edit_message_text(
                message.chat.id, edit_id,
                "❌ You need to login first to access this content. Use /login command to authenticate."
            )
            return

        # Process the link
        await get_msg(userbot, message.chat.id, edit_id, link, i, message)
    except Exception as e:
        print(f"Error in process_and_upload_link: {e}")
        await app.edit_message_text(
            message.chat.id, edit_id,
            f"Error processing link: {str(e)}"
        )

async def parse_telegram_link(msg_link, i=0):
    """Parse Telegram link and return chat and message ID."""
    try:
        # Sanitize the message link
        msg_link = msg_link.split("?single")[0]
        
        # Extract chat and message ID for valid Telegram links
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            parts = msg_link.split("/")
            if 't.me/b/' in msg_link:
                chat = parts[-2]
                msg_id = int(parts[-1]) + i
            else:
                chat = int('-100' + parts[parts.index('c') + 1])
                msg_id = int(parts[-1]) + i
            return chat, msg_id
        elif '/s/' in msg_link:
            # Handle story links
            parts = msg_link.split("/")
            chat = parts[3]
            
            if chat.isdigit():   # this is for channel stories
                chat = f"-100{chat}"
            
            msg_id = int(parts[-1])
            return chat, msg_id
        else:
            # Handle public links
            chat = msg_link.split("t.me/")[1].split("/")[0]
            msg_id = int(msg_link.split("/")[-1])
            return chat, msg_id
    except Exception as e:
        print(f"Error parsing Telegram link: {e}")
        return None, None
