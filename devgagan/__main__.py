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
from aiojobs import create_scheduler
import sys
import os
import logging
import time
from utils import performance_optimizer, monitor_performance

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[ %(levelname)s/%(asctime)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ----------------------------Bot-Start---------------------------- #

loop = asyncio.get_event_loop()

# Memory management - run garbage collection periodically
async def monitor_memory_usage():
    while True:
        try:
            # Use the performance optimizer for better memory management
            await performance_optimizer.optimize_memory()
            
            # Sleep for a period
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logger.error(f"Error in memory monitoring: {e}")
            await asyncio.sleep(600)  # Wait longer if error occurs

# Function to schedule expiry checks
async def schedule_expiry_check():
    scheduler = await create_scheduler()
    while True:
        try:
            await scheduler.spawn(check_and_remove_expired_users())
        except Exception as e:
            logger.error(f"Error in expiry check: {e}")
        
        # Run garbage collection after user expiry checks
        gc.collect()
        await asyncio.sleep(3600)  # Check every hour

async def load_modules():
    """Load all modules with error handling for each module"""
    successful_modules = 0
    failed_modules = 0
    
    for module_name in ALL_MODULES:
        try:
            importlib.import_module("devgagan.modules." + module_name)
            successful_modules += 1
            logger.info(f"Loaded module: {module_name}")
        except Exception as e:
            failed_modules += 1
            logger.error(f"Failed to load module {module_name}: {e}")
    
    if failed_modules > 0:
        logger.warning(f"Not all modules loaded successfully. {successful_modules} loaded, {failed_modules} failed.")
    else:
        logger.info(f"All {successful_modules} modules loaded successfully!")

async def devggn_boot():
    try:
        # Start performance monitoring tasks
        asyncio.create_task(monitor_memory_usage())
        asyncio.create_task(performance_optimizer.periodic_cleanup())
        asyncio.create_task(monitor_performance())
        
        # Load the modules with error handling
        await load_modules()
        
        # Display bot startup message
        print("""
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
⚡ Performance Optimized
---------------------------------------------------
""")

        # Start background tasks
        asyncio.create_task(schedule_expiry_check())
        logger.info("Auto removal scheduler started...")
        
        # Run garbage collection before idle
        gc.collect()
        
        # Start the bot
        await idle()
        logger.info("Bot stopped...")
    except Exception as e:
        logger.critical(f"Fatal error during bot startup: {e}")
        # Exit with error status
        sys.exit(1)

if __name__ == "__main__":
    try:
        loop.run_until_complete(devggn_boot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        sys.exit(1)

# ------------------------------------------------------------------ #
