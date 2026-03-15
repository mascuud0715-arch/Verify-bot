import telebot
import json
import os
import requests
from telebot.types import ReplyKeyboardMarkup

TOKEN = os.getenv("MAIN_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

user_state = {}

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []

def save_bots(data):
    with open("bots.json","w") as f:
        json.dump(data,f)

@bot.message_handler(commands=["start"])
def start(message):

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Add Bot","My Bots")

    bot.send_message(
        message.chat.id,
        "🤖 Welcome to Verify System\n\nChoose an option:",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text == "Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "waiting_token"

    bot.send_message(
        message.chat.id,
        "📩 Send your Bot API Token"
    )

@bot.message_handler(func=lambda m: m.text == "My Bots")
def my_bots(message):

    bots = load_bots()

    text = "🤖 Your Bots:\n\n"

    for b in bots:
        if b["owner"] == message.from_user.id:

            username = get_bot_username(b["token"])
            text += f"{username}\n"

    if not found:
        text = "❌ You don't have bots added."

    bot.send_message(message.chat.id,text)

@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def receive_token(message):

    token = message.text.strip()

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        r = requests.get(url).json()

        if not r["ok"]:
            bot.send_message(message.chat.id,"❌ Invalid Bot Token")
            return

    except:
        bot.send_message(message.chat.id,"❌ Token Check Failed")
        return

    bots = load_bots()

    bots.append({
        "owner": message.from_user.id,
        "token": token
    })

    save_bots(bots)

    del user_state[message.from_user.id]

    bot.send_message(
        message.chat.id,
        "✅ Bot Added Successfully"
    )

print("Main Bot Running...")

bot.infinity_polling()
