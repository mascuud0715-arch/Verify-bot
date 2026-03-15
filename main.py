import telebot
import json
import os
import time
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# TOKEN FROM RAILWAY
# =========================
TOKEN = os.getenv("MAIN_BOT_TOKEN")

if TOKEN is None:
    print("MAIN_BOT_TOKEN not found")
    exit()

bot = telebot.TeleBot(TOKEN)

# =========================
# LOAD DATABASE
# =========================
FILE = "bots.json"

try:
    with open(FILE) as f:
        bots = json.load(f)
except:
    bots = {}

# =========================
# SAVE DATABASE
# =========================
def save():
    with open(FILE, "w") as f:
        json.dump(bots, f, indent=2)

# =========================
# USER STATE
# =========================
user_state = {}

# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=["start"])
def start(message):

    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton("➕ Add Bot", callback_data="add"),
        InlineKeyboardButton("🤖 My Bots", callback_data="mybots")
    )

    text = "Ku dar botkaaga si uu u isticmaalo Verify System."

    bot.send_message(message.chat.id, text, reply_markup=kb)

# =========================
# ADD BOT BUTTON
# =========================
@bot.callback_query_handler(func=lambda call: call.data == "add")
def add_bot(call):

    user_state[call.from_user.id] = "token"

    bot.send_message(
        call.message.chat.id,
        "Fadlan geli BOT API TOKEN"
    )

# =========================
# SAVE TOKEN
# =========================
@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == "token")
def save_token(message):

    token = message.text.strip()

    bot.send_message(message.chat.id, "Token-ka waa la hubinayaa...")

    try:

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15
        ).json()

        if not r["ok"]:
            bot.send_message(message.chat.id, "Token sax ma aha.")
            return

        username = r["result"]["username"]
        bot_id = str(r["result"]["id"])

        bots[bot_id] = {
            "token": token,
            "username": username,
            "owner": message.from_user.id
        }

        save()

        user_state[message.from_user.id] = None

        bot.send_message(
            message.chat.id,
            f"Bot waa la daray: @{username}"
        )

    except:

        bot.send_message(
            message.chat.id,
            "Error ayaa dhacay marka token-ka la hubinayay."
        )

# =========================
# MY BOTS
# =========================
@bot.callback_query_handler(func=lambda call: call.data == "mybots")
def my_bots(call):

    text = "Bots-kaaga:\n\n"

    found = False

    for bot_id, data in bots.items():

        if data["owner"] == call.from_user.id:

            text += f"@{data['username']}\n"
            found = True

    if not found:
        text = "Wax bot ah wali ma gelin."

    bot.send_message(call.message.chat.id, text)

# =========================
# SAFE POLLING
# =========================
while True:
    try:
        print("Bot running...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
