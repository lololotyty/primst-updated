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
from pyrogram import Client, ConnectionMode
from pyrogram.enums import ParseMode 
from config import API_ID, API_HASH, BOT_TOKEN, STRING, MONGO_DB
from telethon.sync import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient
import time

loop = asyncio.get_event_loop()

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)

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
    retry_delay=1,
    no_updates=True,
    ipv6=False,  # Disable IPv6 to speed up connections
    connection_mode=ConnectionMode.TCP_FULL,  # Use TCP FULL mode for stability
    device_model="Telegram Bot",  # Simple device model
    system_version="1.0",
    app_version="1.0",
    lang_code="en"
)

pro = Client(
    "ggbot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING,
    workers=50,
    sleep_threshold=5,
    max_concurrent_transmissions=20,
    retry_delay=1,
    no_updates=True,
    ipv6=False,
    connection_mode=ConnectionMode.TCP_FULL,
    device_model="Telegram Bot",
    system_version="1.0",
    app_version="1.0",
    lang_code="en"
)

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
    raise_last_call_error=False,
    device_model="Telegram Bot",
    system_version="1.0",
    app_version="1.0",
    lang_code="en"
)

# MongoDB setup
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]  # Your database
token = tdb["tokens"]  # Your tokens collection

async def create_ttl_index():
    """Ensure the TTL index exists for the `tokens` collection."""
    await token.create_index("expires_at", expireAfterSeconds=0)

# Run the TTL index creation when the bot starts
async def setup_database():
    await create_ttl_index()
    print("MongoDB TTL index created.")

async def start_clients():
    global BOT_ID, BOT_NAME, BOT_USERNAME
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
    
    print("All clients started successfully!")

# Run startup sequence
try:
    loop.run_until_complete(start_clients())
except Exception as e:
    print(f"Error during startup: {e}")
    sys.exit(1)

# Export all necessary clients and variables
__all__ = [
    'app', 'pro', 'telethon_client', 'userrbot',
    'BOT_ID', 'BOT_NAME', 'BOT_USERNAME',
    'tclient', 'tdb', 'token'
]
