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

from devgagan.core.mongo import db
from config import OWNER_ID

users = db.users
watermark_users = db.watermark_users

async def is_verified_user(user_id: int) -> bool:
    """Check if a user is verified."""
    try:
        user = await users.find_one({'user_id': user_id})
        return bool(user)
    except Exception as e:
        print(f"Error checking user verification: {e}")
        return False

async def get_users() -> list:
    """Get all users."""
    try:
        user_list = await users.find().to_list(length=None)
        return [user['user_id'] for user in user_list]
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

async def add_user(user_id: int) -> bool:
    """Add a new user."""
    try:
        result = await users.update_one(
            {'user_id': user_id},
            {'$set': {'user_id': user_id}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

async def remove_user(user_id: int) -> bool:
    """Remove a user."""
    try:
        result = await users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing user: {e}")
        return False

async def is_watermark_user(user_id: int) -> bool:
    """Check if a user has watermark permission."""
    try:
        # Owner always has watermark permission
        if user_id == OWNER_ID:
            return True
            
        user = await watermark_users.find_one({'user_id': user_id})
        return bool(user)
    except Exception as e:
        print(f"Error checking watermark permission: {e}")
        return False

async def add_watermark_user(user_id: int) -> bool:
    """Grant watermark permission to a user."""
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
    """Remove watermark permission from a user."""
    try:
        # Cannot remove owner's watermark permission
        if user_id == OWNER_ID:
            return False
            
        result = await watermark_users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing watermark user: {e}")
        return False
