# devgagan
# Note if you are trying to deploy on vps then directly fill values in ("")

from os import getenv

API_ID = int(getenv("API_ID", "25120174"))
API_HASH = getenv("API_HASH", "89a10ea368b634194752731a7c405e30")
BOT_TOKEN = getenv("BOT_TOKEN", "7749356378:AAHuJL0WdadFOEVN84U1Db8iJgob6x0AeM0")
OWNER_ID = list(map(int, getenv("OWNER_ID", "6820248376").split()))
MONGO_DB = getenv("MONGO_DB", "mongodb+srv://venom:cnqHd4qPjRAPdakY@venom.zkis3.mongodb.net/")
LOG_GROUP = getenv("LOG_GROUP", "-1002226652008")
CHANNEL_ID = int(getenv("CHANNEL_ID", "-1002216382990"))
FREEMIUM_LIMIT = int(getenv("FREEMIUM_LIMIT", "0"))
PREMIUM_LIMIT = int(getenv("PREMIUM_LIMIT", "500"))
WEBSITE_URL = getenv("WEBSITE_URL", "up")
AD_API = getenv("AD_API", "52b4a2cf4687d81e7d3f8f2b7bce78cb")
STRING = getenv("STRING", None)
YT_COOKIES = getenv("YT_COOKIES", None)
INSTA_COOKIES = getenv("INSTA_COOKIES", None)
