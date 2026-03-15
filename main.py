import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("MAIN_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

try:
    with open("bots.json") as f:
        bots = json.load(f)
except:
    bots = {}

user_state = {}

def save():
    with open("bots.json","w") as f:
        json.dump(bots,f)

@bot.message_handler(commands=['start'])
def start(msg):

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Add Bot", callback_data="addbot"))

    bot.send_message(
        msg.chat.id,
        "Ku dar botkaaga si verify system loo geliyo",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data=="addbot")
def addbot(call):

    user_state[call.from_user.id] = "api"

    bot.send_message(
        call.message.chat.id,
        "Fadlan geli API TOKEN botka"
    )

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id)=="api")
def save_api(msg):

    token = msg.text

    try:
        newbot = telebot.TeleBot(token)
        me = newbot.get_me()

        bots[token] = me.username
        save()

        user_state[msg.from_user.id] = None

        bot.send_message(
            msg.chat.id,
            f"✅ Bot waa la daray\n\n@{me.username}"
        )

    except:

        bot.send_message(
            msg.chat.id,
            "❌ API token ma saxna"
        )

bot.infinity_polling()
