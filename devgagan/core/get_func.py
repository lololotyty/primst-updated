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

from pyrogram import Client
from pyrogram.enums import ParseMode
from devgagan import app, pro, sex
from devgagan.core.mongo import db as odb
from telethon import TelegramClient, events, Button
from devgagantools import fast_upload
import shutil
import math
import time
import os
import asyncio
import gc
import re
import pymongo
from typing import Callable
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH

# MongoDB database name and collection name
DB_NAME = "smart_users"
collection = odb[DB_NAME]

VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', '3gp', 'ts', 'm4v', 'f4v', 'vob']
DOCUMENT_EXTENSIONS = ['pdf', 'docs']

mongo_app = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_app[DB_NAME]

if STRING:
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
        start_time = time.time()
        upload_method = await fetch_upload_method(sender)
        metadata = video_metadata(file)
        width, height, duration = metadata['width'], metadata['height'], metadata['duration']
        
        # Get custom thumbnail and ensure it exists for each upload
        thumb_path = await get_custom_thumbnail(sender)
        if thumb_path:
            new_thumb_path = f"{thumb_path}_{os.path.basename(file)}"
            shutil.copy2(thumb_path, new_thumb_path)
            thumb_path = new_thumb_path
        elif file.split('.')[-1].lower() in {'mp4', 'mkv', 'avi', 'mov'}:
            thumb_path = await screenshot(file, duration, sender)

        # Apply watermark if set
        watermark_text = await get_user_watermark(sender)
        if watermark_text:
            file = await apply_watermark(file, watermark_text, sender)

        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        document_formats = {'pdf', 'docx', 'txt', 'epub'}
        image_formats = {'jpg', 'png', 'jpeg'}
        
        file_ext = file.split('.')[-1].lower()
        
        if not os.path.exists(file):
            await edit.edit("❌ File not found. Download may have failed.")
            return

        try:
            if upload_method == "telethon":
                progress_message = await app2.send_message(sender, "**Uploading...**")
                try:
                    if file_ext in video_formats:
                        await app2.send_file(
                            target_chat_id,
                            file=file,
                            thumb=thumb_path,
                            caption=caption,
                            force_document=False,
                            reply_to=topic_id,
                            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                progress_bar(d, t, progress_message, start_time)
                            )
                        )
                    else:
                        await app2.send_file(
                            target_chat_id,
                            file=file,
                            thumb=thumb_path if file_ext not in image_formats else None,
                            caption=caption,
                            force_document=True,
                            reply_to=topic_id,
                            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                                progress_bar(d, t, progress_message, start_time)
                            )
                        )
                finally:
                    await progress_message.delete()
            else:
                if file_ext in video_formats:
                    await app.send_video(
                        target_chat_id,
                        video=file,
                        thumb=thumb_path,
                        caption=caption,
                        duration=duration,
                        width=width,
                        height=height,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        progress_args=(edit, start_time)
                    )
                elif file_ext in image_formats:
                    await app.send_photo(
                        target_chat_id,
                        photo=file,
                        caption=caption,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        progress_args=(edit, start_time)
                    )
                else:
                    await app.send_document(
                        target_chat_id,
                        document=file,
                        thumb=thumb_path,
                        caption=caption,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        progress_args=(edit, start_time)
                    )
        except Exception as upload_error:
            error_msg = f"Upload Error: {str(upload_error)}"
            await app.send_message(sender, error_msg)
            await app.send_message(LOG_GROUP, error_msg)
            raise upload_error

    except Exception as e:
        error_msg = f"Media Processing Error: {str(e)}"
        await app.send_message(sender, error_msg)
        await app.send_message(LOG_GROUP, error_msg)
        raise e
    finally:
        # Cleanup temporary files
        try:
            if thumb_path and thumb_path.endswith(os.path.basename(file)):
                os.remove(thumb_path)
            if watermark_text and file.endswith('_watermarked.' + file_ext):
                os.remove(file)
        except Exception as cleanup_error:
            print(f"Cleanup Error: {str(cleanup_error)}")

async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    try:
        # Sanitize the message link
        msg_link = msg_link.split("?single")[0]
        chat, msg_id = None, None
        saved_channel_ids = load_saved_channel_ids()
        size_limit = 2 * 1024 * 1024 * 1024  # 1.99 GB size limit
        file = ''
        edit = ''
        # Extract chat and message ID for valid Telegram links
        if 't.me/c/' in msg_link or 't.me/b/' in msg_link:
            parts = msg_link.split("/")
            if 't.me/b/' in msg_link:
                chat = parts[-2]
                msg_id = int(parts[-1]) + i # fixed bot problem 
            else:
                chat = int('-100' + parts[parts.index('c') + 1])
                msg_id = int(parts[-1]) + i

            if chat in saved_channel_ids:
                await app.edit_message_text(
                    message.chat.id, edit_id,
                    "Sorry! This channel is protected by **__Shimperd__**."
                )
                return
            
        elif '/s/' in msg_link: # fixed story typo
            edit = await app.edit_message_text(sender, edit_id, "Story Link Dictected...")
            if userbot is None:
                await edit.edit("Login in bot save stories...")     
                return
            parts = msg_link.split("/")
            chat = parts[3]
            
            if chat.isdigit():   # this is for channel stories
                chat = f"-100{chat}"
            
            msg_id = int(parts[-1])
            await download_user_stories(userbot, chat, msg_id, edit, sender)
            await edit.delete(2)
            return
        
        else:
            edit = await app.edit_message_text(sender, edit_id, "Public link detected...")
            chat = msg_link.split("t.me/")[1].split("/")[0]
            msg_id = int(msg_link.split("/")[-1])
            await copy_message_with_chat_id(app, userbot, sender, chat, msg_id, edit)
            await edit.delete(2)
            return
            
        # Fetch the target message
        msg = await userbot.get_messages(chat, msg_id)
        if not msg or msg.service or msg.empty:
            return

        target_chat_id = user_chat_ids.get(message.chat.id, message.chat.id)
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different message types
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

        # if file_size and file_size > size_limit and pro is None:
        #     await app.edit_message_text(sender, edit_id, "**❌ 4GB Uploader not found**")
        #     return

        file_name = await get_media_filename(msg)
        edit = await app.edit_message_text(sender, edit_id, "**Downloading...**")

        # Download media
        file = await userbot.download_media(
            msg,
            file_name=file_name,
            progress=progress_bar,
            progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", edit, time.time())
        )
        
        caption = await get_final_caption(msg, sender)

        # Rename file
        file = await rename_file(file, sender)
        if msg.audio:
            result = await app.send_audio(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(2)
            return
        
        if msg.voice:
            result = await app.send_voice(target_chat_id, file, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(2)
            return

        if msg.photo:
            result = await app.send_photo(target_chat_id, file, caption=caption, reply_to_message_id=topic_id)
            await result.copy(LOG_GROUP)
            await edit.delete(2)
            return

        # Upload media
        # await edit.edit("**Checking file...**")
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
        # await app.edit_message_text(sender, edit_id, f"Failed to save: `{msg_link}`\n\nError: {str(e)}")
        print(f"Error: {e}")
    finally:
        # Clean up
        if file and os.path.exists(file):
            os.remove(file)
        if edit:
            await edit.delete(2)
        
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
        msg = await app.get_messages(chat_id, message_id)
        custom_caption = get_user_caption_preference(sender)
        final_caption = format_caption(msg.caption or '', sender, custom_caption)

        # Parse target_chat_id and topic_id
        topic_id = None
        if '/' in str(target_chat_id):
            target_chat_id, topic_id = map(int, target_chat_id.split('/', 1))

        # Handle different media types
        if msg.media:
            result = await send_media_message(app, target_chat_id, msg, final_caption, topic_id)
            return
        elif msg.text:
            result = await app.copy_message(target_chat_id, chat_id, message_id, reply_to_message_id=topic_id)
            return

        # Fallback if result is None
        if result is None:
            await edit.edit("Trying if it is a group...")
            chat_id = (await userbot.get_chat(f"@{chat_id}")).id
            msg = await userbot.get_messages(chat_id, message_id)

            if not msg or msg.service or msg.empty:
                return

            final_caption = format_caption(msg.caption.markdown if msg.caption else "", sender, custom_caption)
            file = await userbot.download_media(
                msg,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **__Downloading__...**\n├─────────────────────", edit, time.time())
            )
            file = await rename_file(file, sender)

            if msg.photo:
                result = await app.send_photo(target_chat_id, file, caption=final_caption, reply_to_message_id=topic_id)
            elif msg.video or msg.document:
                freecheck = await chk_user(chat_id, sender)
                if file_size > size_limit and (freecheck == 1 or pro is None):
                    await edit.delete()
                    await split_and_upload_file(app, sender, target_chat_id, file, caption, topic_id)
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
                await edit.edit("Unsupported media type.")

    except Exception as e:
        print(f"Error : {e}")
        pass
        #error_message = f"Error occurred while processing message: {str(e)}"
        # await app.send_message(sender, error_message)
        # await app.send_message(sender, f" Baka Make Bot admin in your Channel - {target_chat_id} and restart the process after /cancel")

    finally:
        if file and os.path.exists(file):
            os.remove(file)


async def send_media_message(app, target_chat_id, msg, caption, topic_id):
    try:
        if msg.video:
            return await app.send_video(target_chat_id, msg.video.file_id, caption=caption, reply_to_message_id=topic_id)
        if msg.document:
            return await app.send_document(target_chat_id, msg.document.file_id, caption=caption, reply_to_message_id=topic_id)
        if msg.photo:
            return await app.send_photo(target_chat_id, msg.photo.file_id, caption=caption, reply_to_message_id=topic_id)
    except Exception as e:
        print(f"Error while sending media: {e}")
    
    # Fallback to copy_message in case of any exceptions
    return await app.copy_message(target_chat_id, msg.chat.id, msg.id, reply_to_message_id=topic_id)
    

def format_caption(original_caption, sender, custom_caption):
    delete_words = load_delete_words(sender)
    replacements = load_replacement_words(sender)

    # Remove and replace words in the caption
    for word in delete_words:
        original_caption = original_caption.replace(word, '  ')
    for word, replace_word in replacements.items():
        original_caption = original_caption.replace(word, replace_word)

    # Append custom caption if available
    return f"{original_caption}\n\n__**{custom_caption}**__" if custom_caption else original_caption

    
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
        # Check if user is premium
        if await is_user_verified(user_id):
            await event.respond("Send me the watermark text for PDF files:")
            sessions[user_id] = 'pdfwatermark'
        else:
            await event.respond("PDF Watermark feature is only available for Premium users. Contact @shimps_bot to upgrade.")
        return

    elif event.data == b'watermark':
        # Check if user is premium
        if await is_user_verified(user_id):
            await event.respond("Send me the watermark text you want to apply to your videos/PDFs:")
            sessions[user_id] = 'watermark'
        else:
            await event.respond("Watermark feature is only available for Premium users. Contact @shimps_bot to upgrade.")
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
               
            
        elif session_type == 'watermark':
            watermark_text = event.text
            await set_watermark(user_id, watermark_text)
            await event.respond(f"Video watermark text set to: {watermark_text}")
            
        elif session_type == 'pdfwatermark':
            watermark_text = event.text
            await set_watermark(user_id, watermark_text)
            await event.respond(f"PDF watermark text set to: {watermark_text}")
            
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

async def apply_watermark(file_path, watermark_text, sender):
    """Apply watermark to video or PDF files"""
    try:
        file_ext = file_path.split('.')[-1].lower()
        
        if file_ext in ['mp4', 'mkv', 'avi', 'mov']:
            # Video watermark using ffmpeg
            watermark_position = "5:5"  # Top-left corner
            font_size = "24"
            font_color = "white"
            
            cmd = [
                'ffmpeg', '-i', file_path,
                '-vf', f"drawtext=text='{watermark_text}':x={watermark_position.split(':')[0]}:y={watermark_position.split(':')[1]}:fontsize={font_size}:fontcolor={font_color}:box=1:boxcolor=black@0.5",
                '-codec:a', 'copy',
                f'{file_path}_watermarked.{file_ext}'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if os.path.exists(file_path):
                os.remove(file_path)
            return f'{file_path}_watermarked.{file_ext}'
            
        elif file_ext == 'pdf':
            # PDF watermark using PyPDF2
            from PyPDF2 import PdfFileWriter, PdfFileReader
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Create watermark
            c = canvas.Canvas('watermark.pdf', pagesize=letter)
            c.setFont("Helvetica", 60)
            c.setFillColorRGB(0.5, 0.5, 0.5)  # Gray color
            c.saveState()
            c.translate(300, 400)
            c.rotate(45)
            c.drawString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            
            # Apply watermark to PDF
            with open(file_path, 'rb') as file:
                reader = PdfFileReader(file)
                writer = PdfFileWriter()
                
                watermark = PdfFileReader('watermark.pdf')
                for i in range(reader.getNumPages()):
                    page = reader.getPage(i)
                    page.mergePage(watermark.getPage(0))
                    writer.addPage(page)
                
                with open(f'{file_path}_watermarked.{file_ext}', 'wb') as output_file:
                    writer.write(output_file)
            
            # Cleanup
            os.remove('watermark.pdf')
            if os.path.exists(file_path):
                os.remove(file_path)
            return f'{file_path}_watermarked.{file_ext}'
            
        return file_path
    except Exception as e:
        print(f"Error applying watermark: {e}")
        return file_path

async def get_user_watermark(user_id):
    """Get user's watermark settings"""
    user_data = collection.find_one({"user_id": user_id})
    return user_data.get("watermark_text") if user_data else None

async def set_watermark(user_id, watermark_text):
    """Save user's watermark settings"""
    collection.update_one(
        {"user_id": user_id},
        {"$set": {"watermark_text": watermark_text}},
        upsert=True
    )

async def rename_file(file, sender):
    delete_words = load_delete_words(sender)
    custom_rename_tag = get_user_rename_preference(sender)
    replacements = load_replacement_words(sender)
    
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
        
    for word in delete_words:
        original_file_name = original_file_name.replace(word, "")

    for word, replace_word in replacements.items():
        original_file_name = original_file_name.replace(word, replace_word)

    new_file_name = f"{original_file_name} {custom_rename_tag}.{file_extension}"
    await asyncio.to_thread(os.rename, file, new_file_name)
    return new_file_name


async def sanitize(file_name: str) -> str:
    sanitized_name = re.sub(r'[\\/:"*?<>|]', '_', file_name)
    # Strip leading/trailing whitespaces
    return sanitized_name.strip()
    
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

async def progress_bar(current, total, up_msg, start):
    """Show progress bar for upload/download"""
    try:
        if not up_msg or not total:
            return
            
        now = time.time()
        diff = now - start
        
        # Only update every 2 seconds to avoid flood
        if diff < 2:
            return
            
        speed = current / diff if diff > 0 else 0
        percentage = (current * 100) / total
        
        progress = "".join("●" for _ in range(math.floor(percentage / 10)))
        progress += "".join("○" for _ in range(10 - math.floor(percentage / 10)))
        
        text = f"""**Progress:** {round(percentage, 2)}%
[{progress}]
**Speed:** {humanbytes(speed)}/s
**Done:** {humanbytes(current)} of {humanbytes(total)}
**Time Left:** {TimeFormatter(int((total - current) / speed)) if speed > 0 else '0s'}"""

        try:
            await up_msg.edit(text)
        except Exception:
            pass
            
    except Exception as e:
        print(f"Progress Bar Error: {str(e)}")

# split function .... ?( to handle gareeb bot coder jo string n lga paaye)

async def split_and_upload_file(app, sender, target_chat_id, file_path, caption, topic_id):
    if not os.path.exists(file_path):
        await app.send_message(sender, "❌ File not found!")
        return

    file_size = os.path.getsize(file_path)
    start = await app.send_message(sender, f"ℹ️ File size: {file_size / (1024 * 1024):.2f} MB")
    PART_SIZE =  1.9 * 1024 * 1024 * 1024

    part_number = 0
    async with aiofiles.open(file_path, mode="rb") as f:
        while True:
            chunk = await f.read(PART_SIZE)
            if not chunk:
                break

            # Create part filename
            base_name, file_ext = os.path.splitext(file_path)
            part_file = f"{base_name}.part{str(part_number).zfill(3)}{file_ext}"

            # Write part to file
            async with aiofiles.open(part_file, mode="wb") as part_f:
                await part_f.write(chunk)

            # Uploading part
            edit = await app.send_message(target_chat_id, f"⬆️ Uploading part {part_number + 1}...")
            part_caption = f"{caption} \n\n**Part : {part_number + 1}**"
            await app.send_document(target_chat_id, document=part_file, caption=part_caption, reply_to_message_id=topic_id,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────", edit, time.time())
            )
            await edit.delete()
            os.remove(part_file)  # Cleanup after upload

            part_number += 1

    await start.delete()
    os.remove(file_path)

async def process_media(message_ids, target_chat, edit, topic_id=None):
    """Process multiple media messages"""
    try:
        total = len(message_ids)
        for i, msg_id in enumerate(message_ids, 1):
            try:
                await edit.edit(f"**Processing media {i}/{total}...**")
                message = await app.get_messages(message.chat.id, msg_id)
                
                # Download media
                file_path = await download_media(message, edit)
                if not file_path:
                    continue
                
                # Get caption
                caption = get_caption(message)
                
                # Upload media
                await upload_media(message.from_user.id, target_chat, file_path, caption, edit, topic_id)
                
                # Cleanup downloaded file
                try:
                    os.remove(file_path)
                except:
                    pass
                    
            except Exception as msg_error:
                error_msg = f"Error processing message {msg_id}: {str(msg_error)}"
                await app.send_message(message.from_user.id, error_msg)
                await app.send_message(LOG_GROUP, error_msg)
                continue
                
        await edit.edit("✅ Batch processing completed!")
        
    except Exception as e:
        error_msg = f"Batch Processing Error: {str(e)}"
        await app.send_message(message.from_user.id, error_msg)
        await app.send_message(LOG_GROUP, error_msg)

async def batch_link(_, message):
    """Process batch of links for downloading and uploading"""
    try:
        # Initialize status message
        status = await message.reply_text("🔄 Processing batch request...")
        
        # Extract links
        if not (message.reply_to_message and message.reply_to_message.text):
            await status.edit("❌ Please reply to a message containing links")
            return
            
        links = [link.strip() for link in message.reply_to_message.text.split('\n') if link.strip()]
        if not links:
            await status.edit("❌ No valid links found in the message")
            return
            
        # Process each link
        total_links = len(links)
        processed = 0
        failed = 0
        
        for i, link in enumerate(links, 1):
            try:
                status_text = f"""🔄 Processing link {i}/{total_links}
✓ Completed: {processed}
❌ Failed: {failed}
⏳ Current: Getting message..."""
                await status.edit(status_text)
                
                # Get message from link
                msg = await get_msg(app2, message.from_user.id, status.id, link, i, message)
                if not msg:
                    failed += 1
                    continue
                
                # Update status for download
                await status.edit(status_text.replace("Getting message...", "Downloading..."))
                
                # Download media
                file_path = await download_media(msg, status)
                if not file_path:
                    failed += 1
                    continue
                
                # Update status for upload
                await status.edit(status_text.replace("Downloading...", "Uploading..."))
                
                # Get caption and upload
                caption = get_caption(msg)
                await upload_media(message.from_user.id, message.chat.id, file_path, caption, status, None)
                processed += 1
                
                # Cleanup downloaded file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as cleanup_error:
                    print(f"Cleanup error for {file_path}: {str(cleanup_error)}")
                
                # Small delay between files to prevent flood
                await asyncio.sleep(2)
                
            except Exception as e:
                failed += 1
                error_msg = f"Error processing link {i}: {str(e)}"
                await app.send_message(message.from_user.id, error_msg)
                await app.send_message(LOG_GROUP, error_msg)
                continue
        
        # Final status
        completion_msg = f"""✅ Batch processing completed!
✓ Successfully processed: {processed}/{total_links}
❌ Failed: {failed}

Note: Check above messages for any specific errors."""
        await status.edit(completion_msg)
        
    except Exception as e:
        error_msg = f"Batch Processing Error: {str(e)}"
        await message.reply_text(f"❌ {error_msg}")
        await app.send_message(LOG_GROUP, error_msg)

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

def TimeFormatter(seconds: int) -> str:
    """Format seconds into human readable time"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")
        
    return " ".join(time_parts) if time_parts else "0s"

def thumbnail(sender):
    """Get thumbnail path for a user"""
    thumb_path = f'thumb/{sender}.jpg'
    return thumb_path if os.path.exists(thumb_path) else None

async def get_custom_thumbnail(sender):
    """Get custom thumbnail for the user, with fallback to auto-generated thumbnail"""
    thumb_path = thumbnail(sender)
    if thumb_path:
        # Create a copy of thumbnail for each upload to prevent deletion issues
        new_thumb_path = f"{thumb_path}_{os.path.basename(thumb_path)}"
        shutil.copy2(thumb_path, new_thumb_path)
        thumb_path = new_thumb_path
    return thumb_path

def get_file_name(message):
    """Get appropriate file name from message"""
    try:
        if message.document:
            return message.document.file_name
        if message.video:
            return message.video.file_name if message.video.file_name else f"video_{int(time.time())}.mp4"
        if message.audio:
            return message.audio.file_name or f"audio_{int(time.time())}.mp3"
        if message.voice:
            return f"voice_{int(time.time())}.ogg"
        if message.photo:
            return f"photo_{int(time.time())}.jpg"
        if message.animation:
            return message.animation.file_name or f"animation_{int(time.time())}.mp4"
        if message.sticker:
            return f"sticker_{int(time.time())}.webp"
        if message.video_note:
            return f"video_note_{int(time.time())}.mp4"
        return f"file_{int(time.time())}"
    except Exception:
        return f"file_{int(time.time())}"

async def download_media(message, edit):
    """Download media with progress tracking and error handling"""
    try:
        if not message or not hasattr(message, 'media'):
            await edit.edit("❌ No media found in message")
            return None

        start_time = time.time()
        file_name = get_file_name(message)
        
        # Create downloads directory if it doesn't exist
        os.makedirs('downloads', exist_ok=True)
        file_path = os.path.join('downloads', file_name)
        
        # Show download progress
        progress_text = await edit.edit("⬇️ **Downloading media...**")
        
        try:
            downloaded_file = await message.download(
                file_name=file_path,
                progress=progress_bar,
                progress_args=(progress_text, start_time)
            )
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                await edit.edit("❌ Download failed")
                return None
                
            return downloaded_file
            
        except Exception as download_error:
            error_msg = f"Download Error: {str(download_error)}"
            await edit.edit(f"❌ {error_msg}")
            await app.send_message(LOG_GROUP, error_msg)
            return None
            
    except Exception as e:
        error_msg = f"Media Download Error: {str(e)}"
        await edit.edit(f"❌ {error_msg}")
        await app.send_message(LOG_GROUP, error_msg)
        return None
