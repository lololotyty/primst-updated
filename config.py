# devgagan
# Note if you are trying to deploy on vps then directly fill values in ("")

from os import getenv

API_ID = int(getenv("API_ID", "22430866"))
API_HASH = getenv("API_HASH", "20a0f0284c49fe38bb3676c297fbf947")
BOT_TOKEN = getenv("BOT_TOKEN", "")
OWNER_ID = list(map(int, getenv("OWNER_ID", "8028959557").split()))
MONGO_DB = getenv("MONGO_DB", "")
LOG_GROUP = getenv("LOG_GROUP", "-1002226652008")
CHANNEL_ID = int(getenv("CHANNEL_ID", "-1002216382990"))
FREEMIUM_LIMIT = int(getenv("FREEMIUM_LIMIT", "0"))
PREMIUM_LIMIT = int(getenv("PREMIUM_LIMIT", "1000"))
WEBSITE_URL = getenv("WEBSITE_URL", "upshr")
AD_API = getenv("AD_API", "52b4a2cf4687d8f2b7bc2943f618e78cb")
STRING = getenv("STRING", None)
YT_COOKIES = getenv("YT_COOKIES", None)
INSTA_COOKIES = getenv("INSTA_COOKIES", None)
DEFAULT_SESSION = getenv("DEFAUL_SESSION", None)  # added old method of invite link joining
