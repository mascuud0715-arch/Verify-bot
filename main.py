import telebot
import json
import os
import time
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# ENV TOKEN (Railway)
# =========================
TOKEN = os.getenv("MAIN_BOT_TOKEN")

if not TOKEN:
    raise Exception("MAIN_BOT_TOKEN not found in Railway Variables")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# LOAD DATABASE
# =========================
BOTS_FILE = "bots.json"

try:
    with open(BOTS_FILE) as f:
        bots = json.load(f)
except:
    bots = {}

# =========================
# SAVE FUNCTION
# =========================
def save_bots():
    with open(BOTS_FILE, "w") as f:
        json.dump(bots, f, indent=2)

# =========================
# USER STATE
# =========================
user_state = {}

# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=["start"])
def start(msg):

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Add Bot", callback_data="add_bot"),
        InlineKeyboardButton("🤖 My Bots", callback_data="my_bots")
    )

    text = """
<b>Verify System Bot</b>

Ku dar botkaaga si uu u isticmaalo
<b>Verification System</b>

Dooro mid:
"""

    bot.send_message(msg.chat.id, text, reply_markup=kb)

# =========================
# ADD BOT BUTTON
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "add_bot")
def add_bot(call):

    user_state[call.from_user.id] = "waiting_token"

    bot.send_message(
        call.message.chat.id,
        "Fadlan geli <b>BOT API TOKEN</b>\n\nTusaale:\n<code>123456:ABCDEF...</code>"
    )

# =========================
# SAVE TOKEN
# =========================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "waiting_token")
def save_token(msg):

    token = msg.text.strip()

    bot.send_message(msg.chat.id, "🔎 Token-ka waa la hubinayaa...")

    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15
        ).json()

        if not r["ok"]:
            bot.send_message(msg.chat.id, "❌ Token sax ma aha.")
            return

        username = r["result"]["username"]
        bot_id = str(r["result"]["id"])

        bots[bot_id] = {
            "token": token,
            "username": username,
            "owner": msg.from_user.id
        }

        save_bots()

        user_state[msg.from_user.id] = None

        bot.send_message(
            msg.chat.id,
            f"""
✅ <b>Bot waa la daray</b>

🤖 Bot: @{username}

Hadda waxaad isticmaali kartaa
<b>Verification System</b>.
"""
        )

    except Exception as e:

        bot.send_message(
            msg.chat.id,
            "❌ Error ayaa dhacay marka token-ka la hubinayay."
        )

# =========================
# MY BOTS BUTTON
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "my_bots")
def my_bots(call):

    text = "<b>🤖 Bots-kaaga</b>\n\n"

    found = False

    for bot_id, data in bots.items():

        if data["owner"] == call.from_user.id:

            text += f"• @{data['username']}\n"
            found = True

    if not found:
        text = "Wax bot ah wali ma
