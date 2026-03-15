import telebot
import os
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("MAIN_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return {}

def save_bots(data):
    with open("bots.json","w") as f:
        json.dump(data,f)

state = {}

@bot.message_handler(commands=['start'])
def start(msg):

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("➕ Add Bot"),
        KeyboardButton("🤖 My Bots")
    )

    bot.send_message(
        msg.chat.id,
        "Ku dar bot-kaaga verify system.",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text=="➕ Add Bot")
def addbot(msg):

    state[msg.from_user.id] = "token"

    bot.send_message(
        msg.chat.id,
        "Fadlan geli API TOKEN botka"
    )

@bot.message_handler(func=lambda m: state.get(m.from_user.id)=="token")
def gettoken(msg):

    token = msg.text

    try:

        import requests

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe"
        ).json()

        username = r["result"]["username"]

        bots = load_bots()

        bots[token] = {
            "username":username,
            "owner":msg.from_user.id
        }

        save_bots(bots)

        bot.send_message(
            msg.chat.id,
            f"✅ Bot waa la daray\n@{username}"
        )

        state[msg.from_user.id] = None

    except:

        bot.send_message(
            msg.chat.id,
            "❌ Token sax ma aha"
        )

@bot.message_handler(func=lambda m: m.text=="🤖 My Bots")
def mybots(msg):

    bots = load_bots()

    text="Bots-kaaga:\n\n"

    for t,b in bots.items():

        if b["owner"]==msg.from_user.id:

            text+=f"@{b['username']}\n"

    bot.send_message(msg.chat.id,text)

bot.infinity_polling()
