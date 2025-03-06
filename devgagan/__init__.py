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
from pyrogram import Client
from pyrogram.enums import ParseMode 
from config import API_ID, API_HASH, BOT_TOKEN, STRING, MONGO_DB
from telethon.sync import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

botStartTime = time.time()

# Initialize Pyrogram client with proper configuration
app = Client(
    name="PrimstSaverBot",  # Unique session name
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    parse_mode=ParseMode.MARKDOWN,
    in_memory=True,  # Store session in memory
    plugins=dict(root="devgagan/modules")  # Load plugins from modules directory
)

# Initialize user client for additional features
pro = Client(
    name="UserClient",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING,
    in_memory=True
)

# Initialize Telethon client for specific features
sex = TelegramClient('sexrepo', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# MongoDB setup
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]
token = tdb["tokens"]

async def setup_database():
    """Initialize database indexes and collections."""
    try:
        # Create TTL index for tokens
        await token.create_index("created_at", expireAfterSeconds=86400)  # 24 hours
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")

async def restrict_bot():
    """Initialize bot and start accepting commands."""
    try:
        # Start the bot
        await app.start()
        logger.info("Bot started successfully!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot Username: @{me.username}")
        logger.info(f"Bot Name: {me.first_name}")
        
        # Initialize database
        await setup_database()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

# Initialize bot
loop.run_until_complete(restrict_bot())
