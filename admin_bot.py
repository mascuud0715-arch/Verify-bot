import telebot
import os
import json
import requests

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

state = {}

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
        return {}

# start panel
@bot.message_handler(commands=['start'])
def start(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        msg.chat.id,
        "Admin Panel\n\n"
        "/stats\n"
        "/bots\n"
        "/broadcast"
    )

# stats
@bot.message_handler(commands=['stats'])
def stats(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bots = load_bots()
    users = load_users()

    text = f"""
Stats

Bots: {len(bots)}
Users: {len(users)}
"""

    bot.send_message(msg.chat.id,text)

# list bots
@bot.message_handler(commands=['bots'])
def bots_list(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bots = load_bots()

    text="Bots List\n\n"

    for b in bots.values():
        text += f"@{b['username']}\n"

    bot.send_message(msg.chat.id,text)

# broadcast start
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    state[msg.from_user.id] = "broadcast"

    bot.send_message(
        msg.chat.id,
        "Dir fariinta aad rabto in bots dhan lagu diro."
    )

# receive broadcast message
@bot.message_handler(func=lambda m: state.get(m.from_user.id)=="broadcast")
def send_broadcast(msg):

    bots = load_bots()
    users = load_users()

    text = msg.text

    sent = 0

    for u in users:

        for b in bots.values():

            token = b["token"]

            try:

                requests.get(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    params={
                        "chat_id":u,
                        "text":text
                    }
                )

                sent += 1

            except:
                pass

    bot.send_message(
        msg.chat.id,
        f"Broadcast waa la diray\n\nMessages sent: {sent}"
    )

    state[msg.from_user.id] = None

bot.infinity_polling()
