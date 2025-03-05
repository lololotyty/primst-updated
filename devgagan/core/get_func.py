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
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode, MessageMediaType
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid
from pyrogram.errors import RPCError
from devgagan.core.func import *
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH
from devgagan.core.mongo import db as odb
from telethon import TelegramClient, events, Button
from devgagantools import fast_upload
import shutil

# MongoDB database name and collection name
DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"
WATERMARK_SETTINGS = "watermark_settings"

# Initialize MongoDB connection
mongo_app = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_app[DB_NAME]
collection = db[COLLECTION_NAME]
watermark_db = mongo_app[DB_NAME]
watermark_collection = watermark_db[WATERMARK_SETTINGS]

# Constants
VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', '3gp', 'ts', 'm4v', 'f4v', 'vob']
DOCUMENT_EXTENSIONS = ['pdf', 'docs']
SET_PIC = "settings.jpg"
MESS = "Customize by your end and Configure your settings ..."

# Initialize global variables
user_chat_ids = {}
user_rename_preferences = {}
user_caption_preferences = {}
sessions = {}
pending_photos = {}
user_progress = {}

if STRING:
    from devgagan import pro
    print("App imported by shimperd.")
else:
    pro = None
    print("STRING is not available. 'app' is set to None.")

# Watermark Functions
async def add_watermark_user(user_id):
    """Add a user to the authorized watermark users list"""
    try:
        watermark_collection.update_one(
            {"_id": "authorized_users"},
            {"$addToSet": {"users": user_id}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding watermark user: {e}")
        return False

async def remove_watermark_user(user_id):
    """Remove user from watermark authorized users"""
    try:
        result = watermark_collection.update_one(
            {"_id": "authorized_users"},
            {"$pull": {"users": user_id}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error removing watermark user: {e}")
        return False

async def get_authorized_watermark_users():
    """Get list of authorized watermark users"""
    try:
        doc = watermark_collection.find_one({"_id": "authorized_users"})
        return doc.get("users", []) if doc else []
    except Exception as e:
        print(f"Error getting authorized users: {e}")
        return []

async def is_authorized_for_watermark(user_id):
    """Check if user is authorized to modify watermark settings"""
    try:
        doc = watermark_collection.find_one({"_id": "authorized_users"})
        return user_id in (doc.get("users", []) if doc else [])
    except Exception as e:
        print(f"Error checking authorization: {e}")
        return False

async def get_watermark_settings():
    """Get watermark settings from database"""
    settings = watermark_collection.find_one({"_id": "settings"})
    if not settings:
        # Default settings
        settings = {
            "_id": "settings",
            "enabled": True,
            "text": "",  # Empty default text
            "position": "bottom-right",
            "font_size": 36,
            "opacity": 0.7
        }
        watermark_collection.insert_one(settings)
    return settings

async def save_watermark_settings(settings):
    """Save watermark settings to database"""
    try:
        result = watermark_collection.update_one(
            {"_id": "settings"},
            {"$set": settings},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error saving watermark settings: {e}")
        return False

async def is_user_authorized(user_id):
    """Check if user is authorized to use watermark"""
    return user_id in OWNER_ID or await is_authorized_for_watermark(user_id)

async def apply_watermark(input_path, output_path, settings=None):
    """Apply watermark to file based on type"""
    if not settings:
        settings = await get_watermark_settings()
    
    if not settings.get("enabled", True) or not settings.get("text"):
        # If watermark is disabled or text is empty, just copy the file
        shutil.copy2(input_path, output_path)
        return True

    file_ext = os.path.splitext(input_path)[1].lower()
    
    try:
        if file_ext in ['.jpg', '.jpeg', '.png']:
            return await apply_image_watermark(input_path, output_path, settings)
        elif file_ext == '.pdf':
            return await apply_pdf_watermark(input_path, output_path, settings)
        elif file_ext in ['.mp4', '.avi', '.mov']:
            return await apply_video_watermark(input_path, output_path, settings)
        else:
            # Unsupported file type, just copy
            shutil.copy2(input_path, output_path)
            return True
    except Exception as e:
        print(f"Error applying watermark: {e}")
        # On error, copy original file
        shutil.copy2(input_path, output_path)
        return False

async def apply_image_watermark(input_path, output_path, settings):
    """Apply watermark to image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import math

        # Open image
        with Image.open(input_path) as img:
            # Convert to RGBA
            img = img.convert('RGBA')
            
            # Create text layer
            txt = Image.new('RGBA', img.size, (255,255,255,0))
            draw = ImageDraw.Draw(txt)

            # Load font
            font_size = settings.get('font_size', 36)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            text = settings.get('text', '')
            position = settings.get('position', 'bottom-right')
            opacity = int(255 * settings.get('opacity', 0.7))

            # Get text size
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Calculate position
            padding = 10
            if position == 'top-left':
                pos = (padding, padding)
            elif position == 'top-right':
                pos = (img.width - text_width - padding, padding)
            elif position == 'bottom-left':
                pos = (padding, img.height - text_height - padding)
            elif position == 'center':
                pos = ((img.width - text_width) // 2, (img.height - text_height) // 2)
            else:  # bottom-right
                pos = (img.width - text_width - padding, img.height - text_height - padding)

            # Draw text
            draw.text(pos, text, fill=(255,255,255,opacity), font=font)

            # Combine layers
            watermarked = Image.alpha_composite(img, txt)
            watermarked = watermarked.convert('RGB')
            
            # Save
            watermarked.save(output_path, quality=95)
            return True
    except Exception as e:
        print(f"Error applying image watermark: {e}")
        return False

async def apply_pdf_watermark(input_path, output_path, settings):
    """Apply watermark to PDF"""
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io

        # Create watermark
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        
        text = settings.get('text', '')
        position = settings.get('position', 'bottom-right')
        font_size = settings.get('font_size', 36)
        opacity = settings.get('opacity', 0.7)

        # Position mapping
        positions = {
            'top-left': (50, letter[1] - 50),
            'top-right': (letter[0] - 50, letter[1] - 50),
            'bottom-left': (50, 50),
            'bottom-right': (letter[0] - 50, 50),
            'center': (letter[0]/2, letter[1]/2)
        }
        
        x, y = positions.get(position, positions['bottom-right'])
        
        c.setFont("Helvetica", font_size)
        c.setFillAlpha(opacity)
        c.drawString(x, y, text)
        c.save()

        # Move to beginning of StringIO buffer
        packet.seek(0)
        watermark = PdfReader(packet)
        
        # Read original PDF
        original = PdfReader(input_path)
        output = PdfWriter()

        # Add watermark to each page
        for page in original.pages:
            page.merge_page(watermark.pages[0])
            output.add_page(page)

        # Write output
        with open(output_path, 'wb') as out_file:
            output.write(out_file)
            
        return True
    except Exception as e:
        print(f"Error applying PDF watermark: {e}")
        return False

async def apply_video_watermark(input_path, output_path, settings):
    """Apply watermark to video"""
    try:
        import cv2
        import numpy as np
        
        # Open video
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Prepare text properties
        text = settings.get('text', '')
        position = settings.get('position', 'bottom-right')
        font_size = settings.get('font_size', 36) / 36  # Scale down for CV2
        opacity = settings.get('opacity', 0.7)
        
        # Get text size
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, font_size, 2)[0]
        
        # Calculate position
        padding = 10
        if position == 'top-left':
            pos = (padding, text_size[1] + padding)
        elif position == 'top-right':
            pos = (width - text_size[0] - padding, text_size[1] + padding)
        elif position == 'bottom-left':
            pos = (padding, height - padding)
        elif position == 'center':
            pos = ((width - text_size[0]) // 2, (height + text_size[1]) // 2)
        else:  # bottom-right
            pos = (width - text_size[0] - padding, height - padding)

        # Process frames
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Add watermark
            overlay = frame.copy()
            cv2.putText(overlay, text, pos, font, font_size, (255,255,255), 2)
            
            # Apply opacity
            cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
            
            # Write frame
            out.write(frame)

        # Release everything
        cap.release()
        out.release()
        
        return True
    except Exception as e:
        print(f"Error applying video watermark: {e}")
        return False

@Client.on_message(filters.command("watermark"))
async def watermark_command(client, message):
    """Handle watermark command"""
    user_id = message.from_user.id
    
    # Check if user is authorized
    if not await is_user_authorized(user_id):
        await message.reply("❌ You are not authorized to use watermark settings.")
        return

    args = message.text.split()[1:]  # Remove the command itself
    if len(args) == 0:
        settings = await get_watermark_settings()
        status = "✅ Enabled" if settings.get("enabled") else "❌ Disabled"
        position = settings.get("position", "bottom-right")
        font_size = settings.get("font_size", 36)
        opacity = settings.get("opacity", 0.7)
        text = settings.get("text", "").strip()
        
        current_settings = (
            f"📝 **Current Watermark Settings**\n\n"
            f"• Status: {status}\n"
            f"• Text: `{text}`\n"
            f"• Position: `{position}`\n"
            f"• Font Size: `{font_size}`\n"
            f"• Opacity: `{opacity}`\n\n"
            f"**Available Commands:**\n"
            f"• `/watermark enable` - Enable watermark\n"
            f"• `/watermark disable` - Disable watermark\n"
            f"• `/watermark text <text>` - Set watermark text\n"
            f"• `/watermark position <top-left/top-right/bottom-left/bottom-right/center>`\n"
            f"• `/watermark size <12-72>` - Set font size\n"
            f"• `/watermark opacity <0.1-1.0>` - Set opacity\n"
        )
        
        if user_id in OWNER_ID:
            current_settings += (
                f"\n**Owner Commands:**\n"
                f"• `/watermark adduser <user_id>` - Add authorized user\n"
                f"• `/watermark removeuser <user_id>` - Remove authorized user\n"
                f"• `/watermark listusers` - List authorized users"
            )
        
        await message.reply(current_settings)
        return

    command = args[0].lower()
    settings = await get_watermark_settings()

    if command == "enable":
        settings["enabled"] = True
        await save_watermark_settings(settings)
        await message.reply("✅ Watermark enabled")
    elif command == "disable":
        settings["enabled"] = False
        await save_watermark_settings(settings)
        await message.reply("❌ Watermark disabled")
    elif command == "text" and len(args) > 1:
        text = " ".join(args[1:]).strip()
        if text:  # Only update if text is not empty
            settings["text"] = text
            await save_watermark_settings(settings)
            await message.reply(f"✅ Watermark text updated to: `{text}`")
        else:
            await message.reply("❌ Please provide some text for the watermark")
    elif command == "position" and len(args) > 1:
        pos = args[1].lower()
        if pos in ["top-left", "top-right", "bottom-left", "bottom-right", "center"]:
            settings["position"] = pos
            await save_watermark_settings(settings)
            await message.reply(f"✅ Watermark position set to: `{pos}`")
        else:
            await message.reply("❌ Invalid position. Use: top-left, top-right, bottom-left, bottom-right, or center")
    elif command == "size" and len(args) > 1:
        try:
            size = int(args[1])
            if 12 <= size <= 72:
                settings["font_size"] = size
                await save_watermark_settings(settings)
                await message.reply(f"✅ Font size set to: `{size}`")
            else:
                await message.reply("❌ Font size must be between 12 and 72")
        except ValueError:
            await message.reply("❌ Invalid font size")
    elif command == "opacity" and len(args) > 1:
        try:
            opacity = float(args[1])
            if 0.1 <= opacity <= 1.0:
                settings["opacity"] = opacity
                await save_watermark_settings(settings)
                await message.reply(f"✅ Opacity set to: `{opacity}`")
            else:
                await message.reply("❌ Opacity must be between 0.1 and 1.0")
        except ValueError:
            await message.reply("❌ Invalid opacity value")
    elif command == "adduser" and len(args) > 1 and user_id in OWNER_ID:
        try:
            target_user_id = int(args[1])
            if await add_watermark_user(target_user_id):
                await message.reply(f"✅ User `{target_user_id}` authorized to use watermark feature")
            else:
                await message.reply("❌ Failed to authorize user")
        except ValueError:
            await message.reply("❌ Invalid user ID format")
    elif command == "removeuser" and len(args) > 1 and user_id in OWNER_ID:
        try:
            target_user_id = int(args[1])
            if await remove_watermark_user(target_user_id):
                await message.reply(f"✅ User `{target_user_id}` removed from authorized users")
            else:
                await message.reply("❌ Failed to remove user")
        except ValueError:
            await message.reply("❌ Invalid user ID format")
    elif command == "listusers" and user_id in OWNER_ID:
        users = await get_authorized_watermark_users()
        if users:
            user_list = "\n".join([f"• `{uid}`" for uid in users])
            await message.reply(f"**Authorized Watermark Users:**\n{user_list}")
        else:
            await message.reply("No users are authorized to use watermark")
    else:
        await message.reply("❌ Invalid command. Use /watermark to see available options")

# File upload and download functions
async def upload_media(sender, target_chat_id, file, caption, edit, topic_id):
    try:
        upload_method = await fetch_upload_method(sender)
        metadata = video_metadata(file)
        width, height, duration = metadata['width'], metadata['height'], metadata['duration']
        
        # Get thumbnail path and ensure it exists
        thumb_path = thumbnail(sender)
        if not thumb_path:
            if file.split('.')[-1].lower() in VIDEO_EXTENSIONS:
                thumb_path = await screenshot(file, duration, sender)

        # Apply watermark if enabled
        original_file = file
        output_path = f"{file}_watermarked"
        await apply_watermark(file, output_path)
        file = output_path
        
        video_formats = {'mp4', 'mkv', 'avi', 'mov'}
        document_formats = {'pdf', 'docx', 'txt', 'epub'}
        image_formats = {'jpg', 'png', 'jpeg'}

        # Pyrogram upload
        if upload_method == "Pyrogram":
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
                await asyncio.sleep(2)
                await dm.copy(LOG_GROUP)

        # Telethon upload
        elif upload_method == "Telethon":
            await edit.delete()
            progress_message = await gf.send_message(sender, "**__Uploading...__**")
            caption = await format_caption_to_html(caption)
            uploaded = await fast_upload(
                gf, file,
                reply=progress_message,
                name=None,
                progress_bar_function=lambda done, total: progress_callback(done, total, sender)
            )
            await progress_message.delete()

            attributes = [
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ] if file.split('.')[-1].lower() in video_formats else []

            # Send to target chat and log group
            for chat_id in [target_chat_id, LOG_GROUP]:
                await gf.send_file(
                    chat_id,
                    uploaded,
                    caption=caption,
                    attributes=attributes,
                    reply_to=topic_id,
                    thumb=thumb_path
                )

    except Exception as e:
        await app.send_message(LOG_GROUP, f"**Upload Failed:** {str(e)}")
        print(f"Error during media upload: {e}")

    finally:
        # Cleanup temporary files
        try:
            # Only remove screenshot thumbnails, not user-set thumbnails
            if thumb_path and thumb_path.startswith('temp_'):
                os.remove(thumb_path)
            
            # Remove watermarked file if it was created
            if file != original_file and os.path.exists(file):
                os.remove(file)
        except:
            pass
        gc.collect()

async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    """Handle message processing and forwarding"""
    try:
        # Sanitize the message link
        msg_link = msg_link.split("?single")[0]
        chat, msg_id = None, None
        saved_channel_ids = load_saved_channel_ids()
        size_limit = 2 * 1024 * 1024 * 1024  # 2GB size limit
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
            edit = await app.edit_message_text(sender, edit_id, "Story Link Detected...")
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
        print(f"Error: {e}")
    finally:
        # Clean up
        if file and os.path.exists(file):
            os.remove(file)
        if edit:
            await edit.delete(2)

# Helper functions
def thumbnail(sender):
    """Get thumbnail path for a sender"""
    thumb_path = f'{sender}.jpg'
    try:
        if os.path.exists(thumb_path):
            return thumb_path
    except:
        pass
    return None

async def fetch_upload_method(user_id):
    """Fetch the user's preferred upload method."""
    user_data = collection.find_one({"user_id": user_id})
    return user_data.get("upload_method", "Pyrogram") if user_data else "Pyrogram"

async def format_caption_to_html(caption: str) -> str:
    """Convert markdown-style formatting to HTML"""
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

# Progress tracking functions
def progress_callback(done, total, user_id):
    """Track upload progress"""
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    
    user_data = user_progress[user_id]
    percent = (done / total) * 100
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    
    done_mb = done / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time
        speed_mbps = (speed_bps * 8) / (1024 * 1024)
    else:
        speed_mbps = 0
    
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    
    remaining_time_min = remaining_time / 60
    
    final = (
        f"╭──────────────────╮\n"
        f"│     **__Shimp Lib Uploader__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__ETA:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Powered by Shimperd__**"
    )
    
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    
    return final

# Settings management functions
def save_user_upload_method(user_id, method):
    """Save user's preferred upload method"""
    try:
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"upload_method": method}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving upload method: {e}")
        return False

# Event handlers
@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    """Handle settings command"""
    user_id = event.sender_id
    await send_settings_message(event.chat_id, user_id)

async def send_settings_message(chat_id, user_id):
    """Send settings menu"""
    buttons = [
        [Button.inline("Set Chat ID", b'setchat'), Button.inline("Set Rename Tag", b'setrename')],
        [Button.inline("Caption", b'setcaption'), Button.inline("Replace Words", b'setreplacement')],
        [Button.inline("Remove Words", b'delete'), Button.inline("Reset", b'reset')],
        [Button.inline("Session Login", b'addsession'), Button.inline("Logout", b'logout')],
        [Button.inline("Set Thumbnail", b'setthumb'), Button.inline("Remove Thumbnail", b'remthumb')],
        [Button.inline("PDF Wtmrk", b'pdfwt'), Button.inline("Video Wtmrk", b'watermark')],
        [Button.inline("Upload Method", b'uploadmethod')],
        [Button.url("Report Errors", "https://telegram.dog/shimps_bot")]
    ]

    await gf.send_file(
        chat_id,
        file=SET_PIC,
        caption=MESS,
        buttons=buttons
    )

# Initialize required collections and settings
if not watermark_collection.find_one({"_id": "settings"}):
    watermark_collection.insert_one({
        "_id": "settings",
        "enabled": True,
        "text": "",
        "position": "bottom-right",
        "font_size": 36,
        "opacity": 0.7
    })

if not watermark_collection.find_one({"_id": "authorized_users"}):
    watermark_collection.insert_one({
        "_id": "authorized_users",
        "users": []
    })
