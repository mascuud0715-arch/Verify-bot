import telebot
import json
import requests
import os
from telebot.types import ReplyKeyboardMarkup

TOKEN = os.getenv("MAIN_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

user_state = {}

# ---------------- LOAD FILES ----------------

def load_bots():

    try:
        with open("bots.json") as f:
            return json.load(f)

    except:
        return []

def save_bots(data):

    with open("bots.json","w") as f:
        json.dump(data,f,indent=4)


def load_users():

    try:
        with open("users.json") as f:
            return json.load(f)

    except:
        return []

def save_users(data):

    with open("users.json","w") as f:
        json.dump(data,f,indent=4)

# ---------------- SAVE USER ----------------

def save_user(uid):

    users = load_users()

    if uid not in users:

        users.append(uid)

        save_users(users)

# ---------------- GET BOT USERNAME ----------------

def get_bot_username(token):

    try:

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe"
        ).json()

        if r["ok"]:

            return "@" + r["result"]["username"]

        else:
            return None

    except:

        return None


# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):

    uid = message.from_user.id

    save_user(uid)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("➕ Add Bot")
    kb.add("🤖 My Bots")

    bot.send_message(
        message.chat.id,
        "🤖 Welcome To Verify System\n\nChoose option:",
        reply_markup=kb
    )


# ---------------- ADD BOT ----------------

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "token"

    bot.send_message(
        message.chat.id,
        "📩 Send your Bot Token"
    )


# ---------------- MY BOTS ----------------

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    uid = message.from_user.id

    bots = load_bots()

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        if b["owner"] == uid:

            text += f"{b['username']}\n"

            found = True

    if not found:

        text = "❌ You don't have bots added."

    bot.send_message(
        message.chat.id,
        text
    )


# ---------------- RECEIVE TOKEN ----------------

@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def receive_token(message):

    uid = message.from_user.id

    token = message.text.strip()

    username = get_bot_username(token)

    if not username:

        bot.send_message(
            message.chat.id,
            "❌ Invalid Bot Token"
        )

        return


    bots = load_bots()

    for b in bots:

        if b["token"] == token:

            bot.send_message(
                message.chat.id,
                "⚠️ Bot already added"
            )

            return


    bots.append({

        "owner": uid,
        "token": token,
        "username": username

    })


    save_bots(bots)

    del user_state[uid]

    bot.send_message(

        message.chat.id,

        f"✅ Bot Added Successfully\n\n{username}"

    )


# ---------------- RUN ----------------

print("Main Bot Running...")

bot.infinity_polling(skip_pending=True)
