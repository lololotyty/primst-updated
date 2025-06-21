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
from telethon.errors import FloodWaitError
import sys

# Set up logging
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

botStartTime = time.time()

# Initialize Pyrogram client with optimized settings
try:
    app = Client(
        ":RestrictBot:",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workers=100,  # Increased from 50 to 100 for better performance
        parse_mode=ParseMode.MARKDOWN,
        max_concurrent_transmissions=10  # Limit concurrent uploads
    )
    logger.info("Pyrogram client initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize Pyrogram client: {e}")
    sys.exit(1)

# Initialize Telethon client with FloodWait error handling
async def initialize_telethon():
    max_retries = 5
    retry_count = 0
    wait_base = 30  # Initial wait period in seconds
    
    while retry_count < max_retries:
        try:
            client = TelegramClient('sexrepo', API_ID, API_HASH)
            await client.start(bot_token=BOT_TOKEN)
            logger.info("Successfully initialized Telethon client")
            return client
        except FloodWaitError as e:
            wait_time = e.seconds
            retry_count += 1
            logger.warning(f"FloodWaitError: Need to wait {wait_time} seconds. Retry {retry_count}/{max_retries}")
            
            # If this is the last retry, notify about the issue
            if retry_count >= max_retries:
                logger.error(f"Max retries reached for Telethon initialization. Last error: {e}")
                # Continue with a longer wait rather than giving up
                logger.info(f"Trying one last time with extended wait...")
                
            # Wait the required time plus a small buffer
            await asyncio.sleep(wait_time + 5)
        except Exception as e:
            logger.error(f"Error initializing Telethon client: {e}")
            # Add a delay before retrying
            retry_count += 1
            wait_time = wait_base * (2 ** retry_count)  # Exponential backoff
            logger.info(f"Retrying in {wait_time} seconds... ({retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
    
    # If all retries failed, try one last time with a different session name
    try:
        logger.info("Trying with a new session as last resort...")
        client = TelegramClient(f'sexrepo_backup_{int(time.time())}', API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        logger.info("Successfully initialized Telethon client with backup session")
        return client
    except Exception as e:
        logger.critical(f"Failed to initialize Telethon client after all retries: {e}")
        raise

# Run in the event loop to handle async initialization
try:
    sex = loop.run_until_complete(initialize_telethon())
except Exception as e:
    logger.critical(f"Fatal error initializing the Telethon client: {e}")
    # Fallback - continue without Telethon but log the issue
    sex = None 
    logger.warning("Continuing without Telethon client - some functionality will be limited")

# Handle session for premium users (if STRING is provided)
pro = None  # Default value
try:
    if STRING:
        pro = Client(
            "gaganPro", 
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=STRING,
            in_memory=True
        )
except Exception as e:
    logger.error(f"Error initializing pro client: {e}")
    pro = None

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

# You can call this in your main bot file before starting the bot

async def restrict_bot():
    global BOT_ID, BOT_NAME, BOT_USERNAME
    await setup_database()
    await app.start()
    getme = await app.get_me()
    BOT_ID = getme.id
    BOT_USERNAME = getme.username
    if getme.last_name:
        BOT_NAME = getme.first_name + " " + getme.last_name
    else:
        BOT_NAME = getme.first_name
    if STRING:
        await pro.start()

loop.run_until_complete(restrict_bot())
