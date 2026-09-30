import os

# توکن ربات از BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# آیدی عددی مدیر اصلی ربات (از @userinfobot دریافت کنید)
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))

# مسیر فایل دیتابیس SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "bot.db")

# حالت دیباگ (برای نمایش خطاهای دقیق به ادمین)
DEBUG_MODE = os.environ.get("DEBUG_MODE", "True") == "True"