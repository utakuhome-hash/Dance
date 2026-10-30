"""
دیتابیس ساده‌ی بازی (SQLite) — نسخه‌ی شروع (MVP)
این فایل مسئول ذخیره و محاسبه‌ی منابع هر بازیکنه.

ساده‌سازی نسبت به سند طراحی کامل:
- به‌جای "تعداد نامحدود ساختمون با سطح جدا"، هر منبع (چوب/سنگ/غذا/رعیت) یک
  "سطح توسعه" ۱ تا ۵ داره که سرعت تولیدش رو مشخص می‌کنه. این نسخه‌ی شروعه؛
  بعداً می‌شه سیستم کامل‌تر (تعداد زیاد ساختمون، هرکدوم سطح جدا) رو جایگزین کرد.
"""

import sqlite3
import time

DB_PATH = "game.db"

SECONDS_PER_GAME_YEAR = 86400  # ۱ سال بازی = ۱ روز واقعی

# تولید سالانه در هر سطح (۱ تا ۵) — طبق سند طراحی
PRODUCTION_TABLE = [2, 3, 4, 6, 9]

# هزینه و زمان ارتقای هر سطح (چوب، سنگ، سکه، ساعت)
UPGRADE_COST = {
    1: (80, 35, 50, 3),
    2: (200, 90, 130, 4),
    3: (480, 220, 320, 6),
    4: (1100, 500, 750, 9),
}

RESOURCE_FIELDS = ["wood", "stone", "food", "population"]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            telegram_id INTEGER PRIMARY KEY,
            character_name TEXT NOT NULL,
            house TEXT NOT NULL,
            castle TEXT NOT NULL,
            is_leader INTEGER DEFAULT 0,

            wood REAL DEFAULT 100,
            stone REAL DEFAULT 100,
            iron REAL DEFAULT 20,
            coin REAL DEFAULT 200,
            food REAL DEFAULT 150,
            population REAL DEFAULT 20,

            wood_lvl INTEGER DEFAULT 1,
            stone_lvl INTEGER DEFAULT 1,
            food_lvl INTEGER DEFAULT 1,
            population_lvl INTEGER DEFAULT 1,

            upgrade_resource TEXT,
            upgrade_target_level INTEGER,
            upgrade_complete_at REAL,

            last_update REAL,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()


def register_player(telegram_id: int, character_name: str, house: str, castle: str, is_leader: bool = False):
    """فقط ادمین این تابع رو صدا می‌زنه تا یه پلیر جدید رو به کاراکترش وصل کنه."""
    conn = get_connection()
    now = time.time()
    conn.execute(
        """INSERT OR REPLACE INTO players
           (telegram_id, character_name, house, castle, is_leader, last_update, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (telegram_id, character_name, house, castle, int(is_leader), now, now),
    )
    conn.commit()
    conn.close()


def get_player(telegram_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return row


def _apply_passive_production(conn, player):
    """زمان سپری‌شده از آخرین بار رو حساب می‌کنه و منابع رو بر اساس سطح فعلی اضافه می‌کنه."""
    now = time.time()
    elapsed = max(0, now - player["last_update"])

    updates = {}
    for field in RESOURCE_FIELDS:
        level = player[f"{field}_lvl"]
        yearly = PRODUCTION_TABLE[level - 1]
        rate_per_sec = yearly / SECONDS_PER_GAME_YEAR
        updates[field] = player[field] + rate_per_sec * elapsed

    # اگه ارتقایی در حال انجام بود و زمانش تموم شده، اعمالش کن
    upgrade_applied_msg = None
    if player["upgrade_resource"] and player["upgrade_complete_at"] and now >= player["upgrade_complete_at"]:
        res = player["upgrade_resource"]
        new_level = player["upgrade_target_level"]
        conn.execute(
            f"UPDATE players SET {res}_lvl = ?, upgrade_resource = NULL, "
            f"upgrade_target_level = NULL, upgrade_complete_at = NULL WHERE telegram_id = ?",
            (new_level, player["telegram_id"]),
        )
        upgrade_applied_msg = f"ارتقای {res} به سطح {new_level} تموم شد!"

    conn.execute(
        """UPDATE players SET wood=?, stone=?, food=?, population=?, last_update=?
           WHERE telegram_id=?""",
        (updates["wood"], updates["stone"], updates["food"], updates["population"], now, player["telegram_id"]),
    )
    conn.commit()
    return upgrade_applied_msg


def sync_and_get_player(telegram_id: int):
    """همیشه قبل از نمایش منابع به پلیر، این تابع رو صدا بزن."""
    conn = get_connection()
    player = conn.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if not player:
        conn.close()
        return None, None
    msg = _apply_passive_production(conn, player)
    player = conn.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return player, msg


def start_upgrade(telegram_id: int, resource: str):
    """شروع ارتقای یه منبع. فقط یه ارتقا هم‌زمان مجازه (ساده‌شده‌ی قانون صف ساخت)."""
    if resource not in RESOURCE_FIELDS:
        return False, "این منبع قابل‌ارتقا نیست."

    player, _ = sync_and_get_player(telegram_id)
    if not player:
        return False, "ابتدا باید ثبت‌نام شوی."

    if player["upgrade_resource"]:
        return False, f"یک ارتقا ({player['upgrade_resource']}) در حال انجامه. صبر کن تمام بشه."

    current_level = player[f"{resource}_lvl"]
    if current_level >= 5:
        return False, "این منبع از قبل سطح ۵ (حداکثر) است."

    wood_cost, stone_cost, coin_cost, hours = UPGRADE_COST[current_level]
    if player["wood"] < wood_cost or player["stone"] < stone_cost or player["coin"] < coin_cost:
        return False, (
            f"منابع کافی نیست. نیاز: {wood_cost} چوب، {stone_cost} سنگ، {coin_cost} سکه."
        )

    conn = get_connection()
    now = time.time()
    complete_at = now + hours * 3600
    conn.execute(
        """UPDATE players SET wood=wood-?, stone=stone-?, coin=coin-?,
           upgrade_resource=?, upgrade_target_level=?, upgrade_complete_at=?
           WHERE telegram_id=?""",
        (wood_cost, stone_cost, coin_cost, resource, current_level + 1, complete_at, telegram_id),
    )
    conn.commit()
    conn.close()
    return True, f"ارتقای {resource} به سطح {current_level + 1} شروع شد. تا {hours} ساعت دیگر تمام می‌شود."
