# ---------------------------------------------------
# File Name: __init__.py
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

import asyncio
import logging
import sys
from pyrogram import Client
from pyrogram.enums import ParseMode 
from config import API_ID, API_HASH, BOT_TOKEN, STRING, MONGO_DB
from telethon.sync import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient
import time

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

botStartTime = time.time()

# Initialize Pyrogram clients with optimized settings
app = Client(
    ":RestrictBot:",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,  # Reduced from 200 to prevent overload
    parse_mode=ParseMode.MARKDOWN,
    sleep_threshold=5,  # Reduced from 10
    max_concurrent_transmissions=20,  # Reduced from 50
    in_memory=True,  # Optimize for performance
    no_updates=True,  # Disable updates for better startup
    ipv6=False,  # Disable IPv6 to speed up connections
    system_version="1.0",
    app_version="1.0",
    device_model="Bot"
)

pro = Client(
    "ggbot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING,
    workers=50,
    sleep_threshold=5,
    max_concurrent_transmissions=20,
    in_memory=True,
    no_updates=True,
    ipv6=False,
    system_version="1.0",
    app_version="1.0",
    device_model="Bot"
)

# Initialize userbot client
userrbot = None
if STRING:
    userrbot = pro

# Initialize Telethon client with optimized settings
telethon_client = TelegramClient(
    'telethon_bot', 
    API_ID, 
    API_HASH,
    connection_retries=3,
    retry_delay=1,
    auto_reconnect=True,
    sequential_updates=True,
    flood_sleep_threshold=5,
    device_model="Bot",
    system_version="1.0",
    app_version="1.0"
)

# MongoDB setup
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient.bot
token = tdb.token

async def setup_database():
    """Setup MongoDB with TTL index"""
    await token.create_index("time", expireAfterSeconds=24*60*60)
    print("MongoDB TTL index created.")

async def start_clients():
    """Start all clients concurrently"""
    global BOT_ID, BOT_NAME, BOT_USERNAME
    
    try:
        # Setup database first
        await setup_database()
        
        # Start all clients concurrently
        await asyncio.gather(
            app.start(),
            pro.start() if STRING else asyncio.sleep(0),
            telethon_client.start(bot_token=BOT_TOKEN)
        )
        
        # Get bot info
        getme = await app.get_me()
        BOT_ID = getme.id
        BOT_USERNAME = getme.username
        BOT_NAME = f"{getme.first_name} {getme.last_name}" if getme.last_name else getme.first_name
        
        logger.info("All clients started successfully!")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        sys.exit(1)

# Run startup sequence
try:
    loop.run_until_complete(start_clients())
except Exception as e:
    logger.error(f"Error during startup: {e}")
    sys.exit(1)

# Export all necessary clients and variables
__all__ = [
    'app', 'pro', 'telethon_client', 'userrbot',
    'BOT_ID', 'BOT_NAME', 'BOT_USERNAME',
    'tclient', 'tdb', 'token'
]
