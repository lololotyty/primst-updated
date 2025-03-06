# ---------------------------------------------------
# File Name: db.py
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

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_DB)
db = client.primst_saver  # Use a dedicated database name

# Initialize collections
users = db.users  # Collection for storing users
watermark_users = db.watermark_users  # Collection for watermark permissions
premium_users = db.premium_users  # Collection for premium users
sessions = db.sessions  # Collection for user sessions
tokens = db.tokens  # Collection for user tokens
files = db.files  # Collection for files
broadcast_list = db.broadcast_list  # Collection for broadcast list

async def init_collections():
    """Initialize all required collections if they don't exist."""
    try:
        # Create collections if they don't exist
        if "users" not in await db.list_collection_names():
            await db.create_collection("users")
            
        if "files" not in await db.list_collection_names():
            await db.create_collection("files")
            
        if "tokens" not in await db.list_collection_names():
            await db.create_collection("tokens")
            
        if "watermark_users" not in await db.list_collection_names():
            await db.create_collection("watermark_users")
            
        if "premium_users" not in await db.list_collection_names():
            await db.create_collection("premium_users")
            
        if "sessions" not in await db.list_collection_names():
            await db.create_collection("sessions")
            
        if "broadcast_list" not in await db.list_collection_names():
            await db.create_collection("broadcast_list")
            
    except Exception as e:
        print(f"Error initializing collections: {e}")
        raise

# Export collections for use in other modules
__all__ = ['client', 'db', 'users', 'watermark_users', 'premium_users', 'sessions', 'tokens', 'files', 'broadcast_list']

async def get_data(user_id):
    x = await users.find_one({"_id": user_id})
    return x

async def set_thumbnail(user_id, thumb):
    data = await get_data(user_id)
    if data and data.get("_id"):
        await users.update_one({"_id": user_id}, {"$set": {"thumb": thumb}})
    else:
        await users.insert_one({"_id": user_id, "thumb": thumb})

async def set_caption(user_id, caption):
    data = await get_data(user_id)
    if data and data.get("_id"):
        await users.update_one({"_id": user_id}, {"$set": {"caption": caption}})
    else:
        await users.insert_one({"_id": user_id, "caption": caption})

async def replace_caption(user_id, replace_txt, to_replace):
    data = await get_data(user_id)
    if data and data.get("_id"):
        await users.update_one({"_id": user_id}, {"$set": {"replace_txt": replace_txt, "to_replace": to_replace}})
    else:
        await users.insert_one({"_id": user_id, "replace_txt": replace_txt, "to_replace": to_replace})

async def set_session(user_id, session):
    data = await get_data(user_id)
    if data and data.get("_id"):
        await users.update_one({"_id": user_id}, {"$set": {"session": session}})
    else:
        await users.insert_one({"_id": user_id, "session": session})

async def clean_words(user_id, new_clean_words):
    data = await get_data(user_id)
    if data and data.get("_id"):
        existing_words = data.get("clean_words", [])
         
        if existing_words is None:
            existing_words = []
        updated_words = list(set(existing_words + new_clean_words))
        await users.update_one({"_id": user_id}, {"$set": {"clean_words": updated_words}})
    else:
        await users.insert_one({"_id": user_id, "clean_words": new_clean_words})

async def remove_clean_words(user_id, words_to_remove):
    data = await get_data(user_id)
    if data and data.get("_id"):
        existing_words = data.get("clean_words", [])
        updated_words = [word for word in existing_words if word not in words_to_remove]
        await users.update_one({"_id": user_id}, {"$set": {"clean_words": updated_words}})
    else:
        await users.insert_one({"_id": user_id, "clean_words": []})

async def set_channel(user_id, chat_id):
    data = await get_data(user_id)
    if data and data.get("_id"):
        await users.update_one({"_id": user_id}, {"$set": {"chat_id": chat_id}})
    else:
        await users.insert_one({"_id": user_id, "chat_id": chat_id})

async def all_words_remove(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"clean_words": None}})

async def remove_thumbnail(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"thumb": None}})

async def remove_caption(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"caption": None}})

async def remove_replace(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"replace_txt": None, "to_replace": None}})

async def remove_session(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"session": None}})

async def remove_channel(user_id):
    await users.update_one({"_id": user_id}, {"$set": {"chat_id": None}})

async def delete_session(user_id):
    """Delete the session associated with the given user_id from the database."""
    await users.update_one({"_id": user_id}, {"$unset": {"session": ""}})
