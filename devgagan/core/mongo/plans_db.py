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

from datetime import datetime
from devgagan.core.mongo.db import premium_users

async def check_and_remove_expired_users():
    """Check and remove expired premium users."""
    try:
        # Find all expired premium users
        current_time = datetime.utcnow()
        expired_users = await premium_users.find({
            'expiry_date': {'$lte': current_time}
        }).to_list(length=None)
        
        # Remove expired users
        if expired_users:
            for user in expired_users:
                await premium_users.delete_one({'user_id': user['user_id']})
                
        return expired_users
        
    except Exception as e:
        print(f"Error checking expired users: {e}")
        return []

async def get_premium_users():
    """Get all premium users."""
    try:
        users = await premium_users.find().to_list(length=None)
        return [user['user_id'] for user in users]
    except Exception as e:
        print(f"Error getting premium users: {e}")
        return []

async def check_premium(user_id: int):
    """Check if a user has premium access."""
    try:
        return await premium_users.find_one({'user_id': user_id})
    except Exception as e:
        print(f"Error checking premium status: {e}")
        return None
