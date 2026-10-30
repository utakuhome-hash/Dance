"""
ربات بازی — نسخه‌ی شروع (MVP)
برای اجرا: BOT_TOKEN و ADMIN_IDS رو تو config.py یا متغیر محیطی تنظیم کن.
"""

import logging
import time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import database as db
from config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESOURCE_NAMES_FA = {
    "wood": "چوب",
    "stone": "سنگ",
    "food": "غذا",
    "population": "رعیت",
}


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


# ---------- دستورات عمومی بازیکن ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player, _ = db.sync_and_get_player(update.effective_user.id)
    if not player:
        await update.message.reply_text(
            "👋 خوش اومدی!\n"
            "هنوز کاراکترت ثبت نشده. آیدی عددی‌ات رو برای ادمین بفرست تا "
            "کاراکتر و خاندانت رو برات ثبت کنه.\n\n"
            f"آیدی عددی تو: {update.effective_user.id}"
        )
        return

    await update.message.reply_text(
        f"🏰 خوش برگشتی، {player['character_name']}!\n"
        f"خاندان: {player['house']} — {player['castle']}\n\n"
        "دستور /dashboard رو بزن تا وضعیت خاندانت رو ببینی."
    )


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player, upgrade_msg = db.sync_and_get_player(update.effective_user.id)
    if not player:
        await update.message.reply_text("ابتدا باید ادمین ثبت‌نامت کنه. از /start استفاده کن.")
        return

    text = (
        f"🦅 {player['character_name']} — {player['house']} ({player['castle']})\n"
        f"{'👑 رهبر خاندان' if player['is_leader'] else ''}\n\n"
        "📦 منابع انبار:\n"
        f"🪵 چوب: {int(player['wood'])} (سطح {player['wood_lvl']})\n"
        f"🪨 سنگ: {int(player['stone'])} (سطح {player['stone_lvl']})\n"
        f"⛏️ آهن: {int(player['iron'])}\n"
        f"🪙 سکه: {int(player['coin'])}\n"
        f"🌾 غذا: {int(player['food'])} (سطح {player['food_lvl']})\n"
        f"👥 رعیت: {int(player['population'])} (سطح {player['population_lvl']})\n"
    )

    if player["upgrade_resource"]:
        remaining = max(0, int(player["upgrade_complete_at"] - time.time()))
        hrs, rem = divmod(remaining, 3600)
        mins = rem // 60
        text += (
            f"\n🏗️ در حال ارتقا: {RESOURCE_NAMES_FA.get(player['upgrade_resource'])} "
            f"→ سطح {player['upgrade_target_level']} (تا {hrs}س {mins}د دیگر)\n"
        )
    else:
        text += "\nℹ️ برای ارتقای یک منبع: /upgrade wood یا stone یا food یا population\n"

    if upgrade_msg:
        text = f"✅ {upgrade_msg}\n\n" + text

    await update.message.reply_text(text)


async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "استفاده: /upgrade <wood|stone|food|population>\n"
            "مثال: /upgrade wood"
        )
        return

    resource = context.args[0].lower()
    ok, msg = db.start_upgrade(update.effective_user.id, resource)
    prefix = "✅ " if ok else "❌ "
    await update.message.reply_text(prefix + msg)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 دستورات:\n"
        "/start — شروع و دیدن آیدی عددی‌ات\n"
        "/dashboard — دیدن وضعیت خاندانت\n"
        "/upgrade <منبع> — ارتقای یک منبع (wood/stone/food/population)\n"
    )


# ---------- دستورات ادمین ----------

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فقط ادمین: /register <telegram_id> <character_name> <house> <castle> [leader]"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("این دستور فقط برای ادمین بازیه.")
        return

    if len(context.args) < 4:
        await update.message.reply_text(
            "استفاده:\n/register <telegram_id> <character_name> <house> <castle> [leader]\n"
            "مثال:\n/register 123456789 استفون_بارثیون بارثیون استورمزاند leader"
        )
        return

    telegram_id = int(context.args[0])
    character_name = context.args[1].replace("_", " ")
    house = context.args[2]
    castle = context.args[3]
    is_leader = len(context.args) > 4 and context.args[4].lower() == "leader"

    db.register_player(telegram_id, character_name, house, castle, is_leader)
    await update.message.reply_text(
        f"✅ ثبت شد: {character_name} ({house} — {castle})"
        + (" 👑 رهبر خاندان" if is_leader else "")
    )


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dashboard", dashboard))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))

    logger.info("ربات روشن شد...")
    app.run_polling()


if __name__ == "__main__":
    main()
