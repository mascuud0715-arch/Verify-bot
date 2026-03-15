import telebot
import os
import json

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return {}

def load_users():
    try:
        with open("users.json") as f:
            return json.load(f)
    except:
        return []

@bot.message_handler(commands=['start'])
def start(msg):

    if msg.from_user.id!=ADMIN_ID:
        return

    bot.send_message(
        msg.chat.id,
        "/stats\n/bots"
    )

@bot.message_handler(commands=['stats'])
def stats(msg):

    if msg.from_user.id!=ADMIN_ID:
        return

    bots=load_bots()
    users=load_users()

    bot.send_message(
        msg.chat.id,
        f"Bots: {len(bots)}\nUsers: {len(users)}"
    )

@bot.message_handler(commands=['bots'])
def bots(msg):

    if msg.from_user.id!=ADMIN_ID:
        return

    data=load_bots()

    text="Bots:\n\n"

    for b in data.values():
        text+=f"@{b['username']}\n"

    bot.send_message(msg.chat.id,text)

bot.infinity_polling()
