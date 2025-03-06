# ---------------------------------------------------
# File Name: plans.py
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

from datetime import datetime, timedelta
import pytz
import datetime, time
from devgagan import app
import asyncio
from config import OWNER_ID
from devgagan.core.func import get_seconds
from devgagan.core.mongo.db import premium_users
from pyrogram import filters 



@app.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium_handler(client, message):
    """Handle adding premium users."""
    try:
        user_id = message.from_user.id
        
        # Check command format
        if len(message.command) != 3:
            await message.reply(
                "❌ Invalid format.\n\n"
                "Usage: `/addpremium <user_id> <days>`\n"
                "Example: `/addpremium 123456789 30`"
            )
            return
            
        try:
            target_user = int(message.command[1])
            days = int(message.command[2])
        except ValueError:
            await message.reply("❌ User ID and days must be numbers.")
            return
            
        # Calculate expiry date
        expiry_date = datetime.utcnow() + timedelta(days=days)
        
        # Add premium user
        try:
            await premium_users.update_one(
                {'user_id': target_user},
                {'$set': {
                    'user_id': target_user,
                    'expiry_date': expiry_date,
                    'added_on': datetime.utcnow(),
                    'added_by': user_id
                }},
                upsert=True
            )
            
            await message.reply(
                f"✅ Successfully added premium user!\n\n"
                f"👤 User ID: `{target_user}`\n"
                f"📅 Duration: `{days} days`\n"
                f"⏰ Expires: `{expiry_date.strftime('%Y-%m-%d %H:%M UTC')}`"
            )
            
        except Exception as e:
            print(f"Database error adding premium user: {e}")
            await message.reply("❌ Failed to add premium user. Please try again later.")
            
    except Exception as e:
        print(f"Error in add premium handler: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


@app.on_message(filters.command("delpremium") & filters.user(OWNER_ID))
async def remove_premium_handler(client, message):
    """Handle removing premium users."""
    try:
        user_id = message.from_user.id
        
        # Check command format
        if len(message.command) != 2:
            await message.reply(
                "❌ Invalid format.\n\n"
                "Usage: `/delpremium <user_id>`\n"
                "Example: `/delpremium 123456789`"
            )
            return
            
        try:
            target_user = int(message.command[1])
        except ValueError:
            await message.reply("❌ User ID must be a number.")
            return
            
        # Remove premium user
        try:
            result = await premium_users.delete_one({'user_id': target_user})
            
            if result.deleted_count > 0:
                await message.reply(f"✅ Successfully removed premium access for user `{target_user}`.")
            else:
                await message.reply(f"❌ User `{target_user}` is not a premium user.")
                
        except Exception as e:
            print(f"Database error removing premium user: {e}")
            await message.reply("❌ Failed to remove premium user. Please try again later.")
            
    except Exception as e:
        print(f"Error in remove premium handler: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


@app.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def list_premium_handler(client, message):
    """Handle listing premium users."""
    try:
        user_id = message.from_user.id
            
        # Get all premium users
        try:
            premium_list = await premium_users.find().to_list(length=None)
            
            if not premium_list:
                await message.reply("📝 No premium users found.")
                return
                
            # Format user list
            current_time = datetime.utcnow()
            user_text = "📋 **Premium Users List**\n\n"
            
            for user in premium_list:
                expiry = user.get('expiry_date')
                remaining = expiry - current_time if expiry else timedelta()
                days_left = remaining.days
                
                user_text += (
                    f"👤 User ID: `{user['user_id']}`\n"
                    f"⏰ Expires: `{expiry.strftime('%Y-%m-%d %H:%M UTC')}`\n"
                    f"📅 Days Left: `{days_left}`\n"
                    "➖➖➖➖➖➖➖➖➖➖\n"
                )
                
            await message.reply(user_text)
            
        except Exception as e:
            print(f"Database error listing premium users: {e}")
            await message.reply("❌ Failed to fetch premium users. Please try again later.")
            
    except Exception as e:
        print(f"Error in list premium handler: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


@app.on_message(filters.command("myplan"))
async def myplan(client, message):
    user_id = message.from_user.id
    user = message.from_user.mention
    data = await premium_users.find_one({'user_id': user_id})
    if data and data.get("expiry_date"):
        expiry = data.get("expiry_date")
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
        expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
        
        current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        time_left = expiry_ist - current_time
            
        
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
            
        
        time_left_str = f"{days} ᴅᴀʏꜱ, {hours} ʜᴏᴜʀꜱ, {minutes} ᴍɪɴᴜᴛᴇꜱ"
        await message.reply_text(f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n👤 ᴜꜱᴇʀ : {user}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")   
    else:
        await message.reply_text(f"ʜᴇʏ {user},\n\nʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀɴʏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs contact @shimps_bot")
        


@app.on_message(filters.command("check") & filters.user(OWNER_ID))
async def get_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        data = await premium_users.find_one({'user_id': user_id})
        if data and data.get("expiry_date"):
            expiry = data.get("expiry_date") 
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
            
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            
            
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
            await message.reply_text(f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")
        else:
            await message.reply_text("ɴᴏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ᴏꜰ ᴛʜᴇ ᴡᴀꜱ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀꜱᴇ !")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /check user_id")


@app.on_message(filters.command("transfer"))
async def transfer_premium(client, message):
    if len(message.command) == 2:
        new_user_id = int(message.command[1])  # The user ID to whom premium is transferred
        sender_user_id = message.from_user.id  # The current premium user issuing the command
        sender_user = await client.get_users(sender_user_id)
        new_user = await client.get_users(new_user_id)
        
        # Fetch sender's premium plan details
        data = await premium_users.find_one({'user_id': sender_user_id})
        
        if data and data.get("_id"):  # Verify sender is already a premium user
            expiry = data.get("expiry_date")  
            
            # Remove premium for the sender
            await premium_users.delete_one({'user_id': sender_user_id})
            
            # Add premium for the new user with the same expiry date
            await premium_users.update_one(
                {'user_id': new_user_id},
                {'$set': {
                    'user_id': new_user_id,
                    'expiry_date': expiry,
                    'added_on': datetime.utcnow(),
                    'added_by': sender_user_id
                }},
                upsert=True
            )
            
            # Convert expiry date to IST format for display
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
                "%d-%m-%Y\n⏱️ **Expiry Time:** %I:%M:%S %p"
            )
            time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            current_time = time_zone.strftime("%d-%m-%Y\n⏱️ **Transfer Time:** %I:%M:%S %p")
            
            # Confirmation message to the sender
            await message.reply_text(
                f"✅ **Premium Plan Transferred Successfully!**\n\n"
                f"👤 **From:** {sender_user.mention}\n"
                f"👤 **To:** {new_user.mention}\n"
                f"⏳ **Expiry Date:** {expiry_str_in_ist}\n\n"
                f"__Powered by Shimperd__ 🚀"
            )
            
            # Notification to the new user
            await client.send_message(
                chat_id=new_user_id,
                text=(
                    f"👋 **Hey {new_user.mention},**\n\n"
                    f"🎉 **Your Premium Plan has been Transferred!**\n"
                    f"🛡️ **Transferred From:** {sender_user.mention}\n\n"
                    f"⏳ **Expiry Date:** {expiry_str_in_ist}\n"
                    f"📅 **Transferred On:** {current_time}\n\n"
                    f"__Enjoy the Service!__ ✨"
                )
            )
        else:
            await message.reply_text("⚠️ **You are not a Premium user!**\n\nOnly Premium users can transfer their plans.")
    else:
        await message.reply_text("⚠️ **Usage:** /transfer user_id\n\nReplace `user_id` with the new user's ID.")


async def premium_remover():
    all_users = await premium_users.find().to_list(length=None)
    removed_users = []
    not_removed_users = []

    for user in all_users:
        try:
            user_id = user['user_id']
            chk_time = user.get('expiry_date')

            if chk_time and chk_time <= datetime.utcnow():
                name = await app.get_users(user_id)
                await premium_users.delete_one({'user_id': user_id})
                await app.send_message(user_id, text=f"Hello {name.first_name}, your premium subscription has expired.")
                print(f"{name.first_name}, your premium subscription has expired.")
                removed_users.append(f"{name.first_name} ({user_id})")
            else:
                name = await app.get_users(user_id)
                current_time = datetime.utcnow()
                time_left = chk_time - current_time

                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days > 0:
                    remaining_time = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
                elif hours > 0:
                    remaining_time = f"{hours} hours, {minutes} minutes, {seconds} seconds"
                elif minutes > 0:
                    remaining_time = f"{minutes} minutes, {seconds} seconds"
                else:
                    remaining_time = f"{seconds} seconds"

                print(f"{name.first_name} : Remaining Time : {remaining_time}")
                not_removed_users.append(f"{name.first_name} ({user_id})")
        except:
            await premium_users.delete_one({'user_id': user_id})
            print(f"Unknown users captured : {user_id} removed")
            removed_users.append(f"Unknown ({user_id})")

    return removed_users, not_removed_users


@app.on_message(filters.command("freez") & filters.user(OWNER_ID))
async def refresh_users(_, message):
    removed_users, not_removed_users = await premium_remover()
    # Create a summary message
    removed_text = "\n".join(removed_users) if removed_users else "No users removed."
    not_removed_text = "\n".join(not_removed_users) if not_removed_users else "No users remaining with premium."
    summary = (
        f"**Here is Summary...**\n\n"
        f"> **Removed Users:**\n{removed_text}\n\n"
        f"> **Not Removed Users:**\n{not_removed_text}"
    )
    await message.reply(summary)
