"""
تنظیمات ربات.
بهتره BOT_TOKEN رو به‌جای نوشتن مستقیم اینجا، از متغیر محیطی (Environment Variable)
تو هاستی که استفاده می‌کنی (مثل Railway) بخونی — امن‌تره.
"""

import os

# توکن ربات رو از @BotFather تو تلگرام بگیر
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9258376003:AAE5cFS-b05yc4WDiUR0G68X3iOqGiALhww")

# آیدی عددی تلگرام خودت (و هر ادمین دیگه‌ای) رو اینجا بذار
# برای گرفتن آیدی عددی‌ات، به ربات @userinfobot پیام بده
ADMIN_IDS = [
    123456789,  # <-- این رو با آیدی عددی خودت عوض کن
]
