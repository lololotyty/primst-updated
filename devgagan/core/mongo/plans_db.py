# ---------------------------------------------------
# File Name: plans_db.py
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

import datetime
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_DB
from datetime import datetime, timedelta
from devgagan.core.mongo.db import premium_users

mongo = MongoCli(MONGO_DB)
db = mongo.premium
db = db.premium_db

async def get_premium_users() -> list:
    """Get all premium users."""
    try:
        user_list = await premium_users.find().to_list(length=None)
        return [user['user_id'] for user in user_list]
    except Exception as e:
        print(f"Error getting premium users: {e}")
        return []

async def update_premium_users(user_id: int, expiry_date: datetime) -> bool:
    """Update or add a premium user with expiry date."""
    try:
        result = await premium_users.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'expiry_date': expiry_date,
                'added_on': datetime.utcnow()
            }},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error updating premium user: {e}")
        return False

async def remove_premium_users(user_id: int) -> bool:
    """Remove a premium user."""
    try:
        result = await premium_users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing premium user: {e}")
        return False

async def check_and_remove_expired_users():
    """Check and remove expired premium users."""
    try:
        current_time = datetime.utcnow()
        # Find all expired users
        expired_users = await premium_users.find({
            'expiry_date': {'$lt': current_time}
        }).to_list(length=None)
        
        # Remove expired users
        if expired_users:
            await premium_users.delete_many({
                'user_id': {'$in': [user['user_id'] for user in expired_users]}
            })
            print(f"Removed {len(expired_users)} expired premium users")
    except Exception as e:
        print(f"Error checking expired users: {e}")

async def is_premium_user(user_id: int) -> bool:
    """Check if a user is premium and not expired."""
    try:
        user = await premium_users.find_one({
            'user_id': user_id,
            'expiry_date': {'$gt': datetime.utcnow()}
        })
        return bool(user)
    except Exception as e:
        print(f"Error checking premium status: {e}")
        return False
