import telebot
import os
import requests
from telebot.types import ReplyKeyboardMarkup
from pymongo import MongoClient

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# -------- MONGODB CONNECTION --------

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]

user_state = {}

# -------- SAVE USER --------

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# -------- GET BOT USERNAME --------

def get_bot_username(token):

    try:

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe"
        ).json()

        if r["ok"]:

            return "@" + r["result"]["username"]

    except:
        pass

    return None

# -------- START --------

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

# -------- ADD BOT --------

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "token"

    bot.send_message(
        message.chat.id,
        "📩 Send your Bot Token"
    )

# -------- MY BOTS --------

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    uid = message.from_user.id

    bots = bots_collection.find({"owner": uid})

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        text += f"{b['username']}\n"
        found = True

    if not found:

        text = "❌ You don't have bots added."

    bot.send_message(message.chat.id, text)

# -------- RECEIVE TOKEN --------

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

    if bots_collection.find_one({"token": token}):

        bot.send_message(
            message.chat.id,
            "⚠️ Bot already added"
        )
        return

    bots_collection.insert_one({

        "owner": uid,
        "token": token,
        "username": username

    })

    del user_state[uid]

    bot.send_message(
        message.chat.id,
        f"✅ Bot Added Successfully\n\n{username}"
    )

# -------- RUN --------

print("Main Bot Running...")

bot.infinity_polling(skip_pending=True)
