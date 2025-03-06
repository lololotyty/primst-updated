# ---------------------------------------------------
# File Name: __main__.py
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
import importlib
import gc
from pyrogram import idle
from devgagan.modules import ALL_MODULES
from devgagan.core.mongo.plans_db import check_and_remove_expired_users
from devgagan.core.mongo.db import init_collections
from aiojobs import create_scheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get event loop
loop = asyncio.get_event_loop()

# Function to schedule expiry checks
async def schedule_expiry_check():
    """Schedule periodic checks for expired premium users."""
    try:
        scheduler = await create_scheduler()
        while True:
            await scheduler.spawn(check_and_remove_expired_users())
            await asyncio.sleep(3600)  # Check every hour
            gc.collect()
    except Exception as e:
        logger.error(f"Error in expiry check scheduler: {e}")

async def load_modules():
    """Load all bot modules."""
    try:
        for module_name in ALL_MODULES:
            try:
                importlib.import_module(f"devgagan.modules.{module_name}")
                logger.info(f"Loaded module: {module_name}")
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")
    except Exception as e:
        logger.error(f"Error loading modules: {e}")
        raise

async def devggn_boot():
    """Initialize and start the bot."""
    try:
        # Initialize database collections
        logger.info("Initializing database collections...")
        await init_collections()
        
        # Load all modules
        logger.info("Loading bot modules...")
        await load_modules()
        
        # Start premium expiry checker
        logger.info("Starting premium expiry checker...")
        asyncio.create_task(schedule_expiry_check())
        
        logger.info("""
---------------------------------------------------
📂 Bot Deployed successfully ...
📝 Description: A Pyrogram bot for downloading files from Telegram channels or groups 
                and uploading them back to Telegram.
👨‍💻 Author: Gagan
🌐 GitHub: https://telegram.dog/shimps_bot
📬 Telegram: https://telegram.dog/shimps_bot
▶️ YouTube: https://telegram.dog/shimps_bot
🗓️ Created: 2025-01-11
🔄 Last Modified: 2025-01-11
🛠️ Version: 2.0.5
📜 License: MIT License
---------------------------------------------------
""")
        # Wait for bot to be idle
        await idle()
        
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        raise

if __name__ == "__main__":
    try:
        loop.run_until_complete(devggn_boot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        loop.close()
