import telebot
import json
import os
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("MAIN_BOT_TOKEN")
VERIFY_BOT = "@Verifyd_bot"

bot = telebot.TeleBot(TOKEN)

try:
    bots = json.load(open("bots.json"))
except:
    bots = {}

user_state = {}

def save():
    json.dump(bots, open("bots.json","w"))

# START
@bot.message_handler(commands=['start'])
def start(msg):

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Add Bot", callback_data="add"),
        InlineKeyboardButton("🤖 My Bots", callback_data="mybots")
    )

    bot.send_message(
        msg.chat.id,
        "Ku dar botkaaga verify system.",
        reply_markup=kb
    )

# ADD BOT
@bot.callback_query_handler(func=lambda c: c.data=="add")
def add_bot(call):

    user_state[call.from_user.id] = "token"

    bot.send_message(
        call.message.chat.id,
        "Fadlan geli BOT API TOKEN"
    )

# SAVE TOKEN
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id)=="token")
def save_token(msg):

    token = msg.text

    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()

        if not r["ok"]:
            bot.send_message(msg.chat.id,"❌ Token sax ma aha")
            return

        username = r["result"]["username"]

        bots[token] = {
            "owner": msg.from_user.id,
            "username": username
        }

        save()

        user_state[msg.from_user.id] = None

        bot.send_message(
            msg.chat.id,
            f"✅ Bot waa la daray\n\n@{username}\n\nUser walba wuxuu heli doonaa verify."
        )

    except:
        bot.send_message(msg.chat.id,"❌ Error")

# MY BOTS
@bot.callback_query_handler(func=lambda c: c.data=="mybots")
def mybots(call):

    text = "🤖 Bots-kaaga:\n\n"

    found = False

    for token,data in bots.items():

        if data["owner"] == call.from_user.id:

            text += f"@{data['username']}\n"
            found = True

    if not found:
        text = "Wax bot ah ma gelin."

    bot.send_message(call.message.chat.id,text)

bot.infinity_polling()
