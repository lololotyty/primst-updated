# ---------------------------------------------------
# File Name: users_db.py
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

from config import MONGO_DB
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli


mongo = MongoCli(MONGO_DB)
db = mongo.users
db = db.users_db

# Collection for watermark permissions
watermark_users = db['watermark_users']

async def get_users():
  user_list = []
  async for user in db.users.find({"user": {"$gt": 0}}):
    user_list.append(user['user'])
  return user_list


async def get_user(user):
  users = await get_users()
  if user in users:
    return True
  else:
    return False

async def add_user(user):
  users = await get_users()
  if user in users:
    return
  else:
    await db.users.insert_one({"user": user})


async def del_user(user):
  users = await get_users()
  if not user in users:
    return
  else:
    await db.users.delete_one({"user": user})

async def add_watermark_user(user_id: int) -> bool:
    """Add a user to watermark permissions."""
    try:
        result = await watermark_users.update_one(
            {'user_id': user_id},
            {'$set': {'user_id': user_id}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding watermark user: {e}")
        return False

async def remove_watermark_user(user_id: int) -> bool:
    """Remove a user from watermark permissions."""
    try:
        result = await watermark_users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing watermark user: {e}")
        return False

async def is_watermark_user(user_id: int) -> bool:
    """Check if a user has watermark permissions."""
    try:
        user = await watermark_users.find_one({'user_id': user_id})
        return bool(user)
    except Exception as e:
        print(f"Error checking watermark user: {e}")
        return False
