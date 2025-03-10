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
from devgagan import app, pro, userrbot, telethon_client
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
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import asyncio
from io import BytesIO
import yt_dlp

# Optimized chunk size for better performance
CHUNK_SIZE = 524288  # 512KB
MAX_CONCURRENT_DOWNLOADS = 4
MAX_RETRIES = 3

async def download_chunk(session, url, start, end, file, semaphore):
    headers = {'Range': f'bytes={start}-{end}'}
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            async with semaphore:
                async with session.get(url, headers=headers) as response:
                    if response.status == 206:
                        chunk = await response.read()
                        async with aiofiles.open(file, 'rb+') as f:
                            await f.seek(start)
                            await f.write(chunk)
                        return True
        except Exception as e:
            print(f"Chunk download error: {e}")
            retries += 1
            await asyncio.sleep(1)
    return False

async def parallel_download(url, file_path, file_size):
    chunk_size = CHUNK_SIZE
    chunks = range(0, file_size, chunk_size)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    
    async with aiohttp.ClientSession() as session:
        # Pre-allocate file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.truncate(file_size)
        
        # Download chunks in parallel
        tasks = []
        for start in chunks:
            end = min(start + chunk_size - 1, file_size - 1)
            task = download_chunk(session, url, start, end, file_path, semaphore)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return all(results)

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

async def optimized_upload_media(sender, target_chat_id, file, caption, edit, topic_id):
    try:
        upload_method = await fetch_upload_method(sender)
        metadata = video_metadata(file)
        width, height, duration = metadata['width'], metadata['height'], metadata['duration']
        
        # Get or generate thumbnail
        thumb_path = thumbnail(sender)
        if not thumb_path and file.split('.')[-1].lower() in {'mp4', 'mkv', 'avi', 'mov'}:
            thumb_path = await screenshot(file, duration, sender)

        # Determine file type
        file_ext = file.split('.')[-1].lower()
        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        document_formats = {'pdf', 'docx', 'txt', 'epub'}
        image_formats = {'jpg', 'png', 'jpeg'}

        # Optimize file for upload
        optimized_file = await optimize_media(file, file_ext)
        
        if upload_method == "Pyrogram":
            client = get_appropriate_client()
            
            # Use memory buffer for small files
            if os.path.getsize(optimized_file) < 10 * 1024 * 1024:  # 10MB
                async with aiofiles.open(optimized_file, 'rb') as f:
                    file_data = await f.read()
                file_buffer = BytesIO(file_data)
                file_buffer.name = os.path.basename(optimized_file)
                upload_file = file_buffer
            else:
                upload_file = optimized_file

            if file_ext in video_formats:
                dm = await client.send_video(
                    chat_id=target_chat_id,
                    video=upload_file,
                    caption=caption,
                    height=height,
                    width=width,
                    duration=duration,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=(
                        "╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────",
                        edit,
                        time.time()
                    )
                )
            elif file_ext in image_formats:
                dm = await client.send_photo(
                    chat_id=target_chat_id,
                    photo=upload_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    reply_to_message_id=topic_id,
                    progress_args=(
                        "╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────",
                        edit,
                        time.time()
                    )
                )
            else:
                dm = await client.send_document(
                    chat_id=target_chat_id,
                    document=upload_file,
                    caption=caption,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    progress=progress_bar,
                    parse_mode=ParseMode.MARKDOWN,
                    progress_args=(
                        "╭─────────────────────╮\n│      **__Pyro Uploader__**\n├─────────────────────",
                        edit,
                        time.time()
                    )
                )
            await dm.copy(LOG_GROUP)

        elif upload_method == "Telethon":
            await edit.delete()
            progress_message = await telethon_client.send_message(sender, "**__Uploading...__**")
            
            # Use fast_upload with optimized settings
            uploaded = await fast_upload(
                telethon_client,
                optimized_file,
                reply=progress_message,
                name=os.path.basename(optimized_file),
                progress_bar_function=lambda done, total: progress_callback(done, total, sender),
                part_size_kb=512,  # 512KB chunks
                parallel_upload=True
            )

            attributes = [
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ] if file_ext in video_formats else []

            await telethon_client.send_file(
                target_chat_id,
                uploaded,
                caption=caption,
                attributes=attributes,
                reply_to=topic_id,
                thumb=thumb_path,
                part_size_kb=512,
                upload_speed=2
            )

    except Exception as e:
        await app.send_message(LOG_GROUP, f"**Upload Failed:** {str(e)}")
        print(f"Error during media upload: {e}")
        if edit and not edit.empty:
            try:
                await edit.edit(f"**Upload failed:** {str(e)}")
            except:
                pass
    finally:
        if 'optimized_file' in locals() and optimized_file != file:
            os.remove(optimized_file)
        if thumb_path and os.path.exists(thumb_path) and thumb_path != f'{sender}.jpg':
            os.remove(thumb_path)

async def optimize_media(file_path, file_ext):
    """Optimize media file for faster upload"""
    video_formats = {'mp4', 'mkv', 'avi', 'mov'}
    image_formats = {'jpg', 'png', 'jpeg'}
    
    if file_ext in video_formats:
        # Optimize video
        output_path = f"{file_path}_optimized.{file_ext}"
        cmd = [
            'ffmpeg', '-i', file_path,
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if os.path.exists(output_path) and os.path.getsize(output_path) < os.path.getsize(file_path):
                return output_path
        except Exception as e:
            print(f"Video optimization failed: {e}")
    
    elif file_ext in image_formats:
        # Optimize image
        from PIL import Image
        output_path = f"{file_path}_optimized.{file_ext}"
        
        try:
            with Image.open(file_path) as img:
                img.save(output_path, quality=85, optimize=True)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) < os.path.getsize(file_path):
                return output_path
        except Exception as e:
            print(f"Image optimization failed: {e}")
    
    return file_path

import os
import re
import time
import asyncio
import logging
from io import BytesIO
import yt_dlp
from pyrogram.types import Message
from devgagan import app
from .utils import humanbytes, format_time

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def process_video(url, user_id, edit_id, message):
    """Process and download YouTube videos with optimized settings"""
    try:
        # Send initial status
        await message.edit("Fetching video information...")
        
        # Ensure downloads directory exists
        video_dir = os.path.join(DOWNLOADS_DIR, str(user_id))
        os.makedirs(video_dir, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Prefer MP4
            'outtmpl': os.path.join(video_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'concurrent_fragment_downloads': 8,  # Parallel downloads
            'file_access_retries': 5,
            'fragment_retries': 5,
            'retries': 5,
            'buffersize': 1024*1024,  # 1MB buffer
            'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
                download_progress_hook(d, message),
                asyncio.get_event_loop()
            )],
            'external_downloader': 'aria2c',  # Use aria2c for faster downloads
            'external_downloader_args': [
                '--max-connection-per-server=8',
                '--min-split-size=1M',
                '--max-concurrent-downloads=8',
                '--continue=true'  # Resume partial downloads
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Get video info
                info = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: ydl.extract_info(url, download=False)
                )
                
                if not info:
                    await message.edit("Could not fetch video information!")
                    return
                    
                # Check file size
                filesize = info.get('filesize', 0) or info.get('filesize_approx', 0)
                if filesize > 2 * 1024 * 1024 * 1024:  # 2GB limit
                    await message.edit("Video is too large (>2GB)! Cannot process.")
                    return
                    
                # Update status with video info
                await message.edit(
                    f"Downloading: {info['title']}\n"
                    f"Duration: {format_duration(info.get('duration', 0))}\n"
                    f"Size: {humanbytes(filesize)}"
                )
                
                # Download video
                file_path = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: ydl.download([url])
                )
                
                # Find the downloaded file
                video_file = None
                for file in os.listdir(video_dir):
                    if file.endswith(('.mp4', '.mkv', '.webm')):
                        video_file = os.path.join(video_dir, file)
                        break
                
                if not video_file or not os.path.exists(video_file):
                    await message.edit("Download failed or file not found!")
                    return
                
                # Upload to Telegram
                await message.edit("Uploading to Telegram...")
                caption = (
                    f"**Title:** {info['title']}\n"
                    f"**Duration:** {format_duration(info.get('duration', 0))}\n"
                    f"**Requested by:** {message.from_user.mention}"
                )
                
                await optimized_upload_media(
                    message.chat.id,
                    message.chat.id,
                    video_file,
                    caption,
                    message,
                    None
                )
                
            except Exception as e:
                await message.edit(f"Error while processing: {str(e)}")
                return
            finally:
                # Cleanup
                try:
                    if video_file and os.path.exists(video_file):
                        os.remove(video_file)
                    if os.path.exists(video_dir):
                        os.rmdir(video_dir)
                except OSError:
                    pass
                    
    except Exception as e:
        await message.edit(f"Error processing video: {str(e)}")
        
async def download_progress_hook(d, message):
    """Progress hook for yt-dlp downloads"""
    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                percentage = downloaded * 100 / total
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                # Only update every 5% to reduce message edits
                if int(percentage) % 5 == 0:
                    progress = (
                        f"**Downloading: {percentage:.1f}%**\n"
                        f"**Speed:** {humanbytes(speed)}/s\n"
                        f"**ETA:** {format_time(eta)}\n"
                        f"**Size:** {humanbytes(downloaded)}/{humanbytes(total)}"
                    )
                    
                    await message.edit(progress)
                
        except Exception as e:
            logging.error(f"Progress hook error: {e}")

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    if not seconds:
        return "00:00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    try:
        client = userbot if userbot else get_appropriate_client()
        
        # Extract chat and message IDs efficiently
        match = re.match(r"https?://t\.me/([^/]+)/(\d+)", msg_link)
        if not match:
            await message.edit("Invalid message link format!")
            return
        
        chat_username, msg_id = match.groups()
        msg_id = int(msg_id)
        
        # Get message with optimized settings
        msg = await client.get_messages(
            chat_username,
            msg_id,
            reply_to_message_ids=False,  # Skip fetching reply messages
            replies=0  # Don't fetch replies
        )
        
        if not msg:
            await message.edit("Message not found!")
            return

        # Process media with optimized settings
        if msg.media:
            file = await process_media(msg, sender, edit_id)
            if not file:
                return
            
            # Get file size efficiently
            try:
                file_size = os.path.getsize(file)
            except OSError:
                await message.edit("Error accessing file!")
                return
            
            # Check size limits
            size_limit = 2 * 1024 * 1024 * 1024  # 2GB
            if file_size > size_limit:
                await handle_large_file(file, sender, message, msg.caption)
                return
            
            # Upload with optimized settings
            await optimized_upload_media(
                sender,
                message.chat.id,
                file,
                msg.caption,
                message,
                None
            )
            
            # Clean up
            try:
                os.remove(file)
            except OSError:
                pass
        else:
            # Forward non-media messages directly
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=msg.chat.id,
                message_id=msg.id
            )

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if "wait" in str(e).lower():
            # Extract wait time and provide better message
            wait_time = re.search(r"\d+", str(e))
            if wait_time:
                error_msg = f"Rate limited! Please wait {wait_time.group()} seconds."
        await message.edit(error_msg)

async def process_media(msg, sender, edit_id):
    """Process media messages with optimized settings"""
    try:
        # Create download directory if not exists
        download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = get_file_extension(msg)
        filename = f"{sender}_{int(time.time())}.{file_ext}"
        file_path = os.path.join(download_dir, filename)
        
        # Download with optimized settings
        start_time = time.time()
        file = await msg.download(
            file_path,
            block=False,  # Non-blocking download
            progress=progress_callback,
            progress_args=(sender, edit_id, start_time)
        )
        
        return file
    except Exception as e:
        print(f"Media processing error: {e}")
        return None

def get_file_extension(msg):
    """Get appropriate file extension based on message type"""
    if msg.video:
        return "mp4"
    elif msg.audio:
        return "mp3"
    elif msg.voice:
        return "ogg"
    elif msg.photo:
        return "jpg"
    elif msg.document:
        mime_type = msg.document.mime_type
        if mime_type:
            return mime_type.split('/')[-1]
    return "unknown"

async def progress_callback(current, total, sender, edit_id, start_time):
    """Optimized progress callback with less frequent updates"""
    try:
        if total:
            percentage = current * 100 / total
            
            # Update progress less frequently to reduce overhead
            if percentage % 5 == 0:  # Update every 5%
                speed = current / (time.time() - start_time)
                eta = (total - current) / speed if speed > 0 else 0
                
                progress = (
                    f"**Downloading... {percentage:.1f}%**\n"
                    f"**Speed:** {humanbytes(speed)}/s\n"
                    f"**ETA:** {format_time(eta)}\n"
                    f"**Size:** {humanbytes(current)}/{humanbytes(total)}"
                )
                
                await app.edit_message_text(
                    chat_id=sender,
                    message_id=edit_id,
                    text=progress
                )
    except Exception as e:
        print(f"Progress callback error: {e}")

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

@telethon_client.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    user_id = event.sender_id
    chat_id = event.chat_id
    await send_settings_message(chat_id, user_id)

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

    await telethon_client.send_file(
        chat_id,
        file=SET_PIC,
        caption=MESS,
        buttons=buttons
    )


pending_photos = {}

@telethon_client.on(events.CallbackQuery)
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
    

@telethon_client.on(events.NewMessage(func=lambda e: e.sender_id in pending_photos))
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

@telethon_client.on(events.NewMessage)
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
@telethon_client.on(events.NewMessage(incoming=True, pattern='/lock'))
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

def get_appropriate_client():
    if userrbot:
        return userrbot
    elif pro:
        return pro
    return app
