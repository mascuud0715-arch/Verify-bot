import telebot
import os
import requests
from telebot.types import ReplyKeyboardMarkup
from pymongo import MongoClient

# ================= MONGODB =================

client = MongoClient(os.getenv("MONGO_URL"))
db = client["telegram_system"]

bots_collection = db["bots"]
users_collection = db["users"]

# ================= TELEGRAM =================

TOKEN = os.getenv("MAIN_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

user_state = {}

# ================= SAVE USER =================

def save_user(user_id):

    if not users_collection.find_one({"user_id": user_id}):

        users_collection.insert_one({
            "user_id": user_id
        })


# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id

    save_user(user_id)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Bot","🤖 My Bots")

    bot.send_message(
        message.chat.id,
        "🤖 Welcome to Bot Manager\n\nChoose option:",
        reply_markup=kb
    )


# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text=="➕ Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "waiting_token"

    bot.send_message(
        message.chat.id,
        "📩 Send your Bot API Token"
    )


# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text=="🤖 My Bots")
def my_bots(message):

    user_id = message.from_user.id

    bots = list(bots_collection.find({"owner": user_id}))

    if not bots:

        bot.send_message(
            message.chat.id,
            "❌ You don't have bots added."
        )
        return

    text = "🤖 Your Bots:\n\n"

    i = 1

    for b in bots:

        text += f"{i}: {b['username']}\n"
        i += 1

    bot.send_message(message.chat.id,text)


# ================= RECEIVE TOKEN =================

@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def receive_token(message):

    user_id = message.from_user.id

    token = message.text.strip()

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:

        r = requests.get(url).json()

        if not r["ok"]:

            bot.send_message(
                message.chat.id,
                "❌ Invalid Bot Token"
            )

            return

        bot_username = "@" + r["result"]["username"]

    except:

        bot.send_message(
            message.chat.id,
            "❌ Token Check Failed"
        )

        return


    # check duplicate
    if bots_collection.find_one({"token": token}):

        bot.send_message(
            message.chat.id,
            "⚠️ This bot already added"
        )
        return


    # save bot
    bots_collection.insert_one({

        "owner": user_id,
        "token": token,
        "username": bot_username

    })


    del user_state[user_id]


    bot.send_message(
        message.chat.id,
        f"✅ Bot Added Successfully\n\n{bot_username}"
    )


# ================= RUN =================

print("Main Bot Running...")

bot.infinity_polling()
