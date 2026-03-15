import telebot
import os
import requests
from telebot.types import ReplyKeyboardMarkup
from pymongo import MongoClient

# ================= ENV =================

MAIN_TOKEN = os.getenv("MAIN_BOT_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_BOT_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID"))

MONGO_URL = os.getenv("MONGO_URL")

# ================= MONGO =================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_db = db["bots"]
users_db = db["users"]
stats_db = db["stats"]

# ================= BOTS =================

main_bot = telebot.TeleBot(MAIN_TOKEN)
verify_bot = telebot.TeleBot(VERIFY_TOKEN)
admin_bot = telebot.TeleBot(ADMIN_TOKEN)

user_state = {}

# ================= SAVE USER =================

def save_user(uid):

    if not users_db.find_one({"user_id": uid}):

        users_db.insert_one({
            "user_id": uid
        })

# ================= START =================

@main_bot.message_handler(commands=["start"])
def start(message):

    uid = message.from_user.id

    save_user(uid)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("➕ Add Bot")
    kb.add("🤖 My Bots")

    main_bot.send_message(
        message.chat.id,
        "🤖 Verify System\n\nAdd your bot to start verification system.",
        reply_markup=kb
    )

# ================= ADD BOT =================

@main_bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "token"

    main_bot.send_message(
        message.chat.id,
        "📩 Send your Bot Token"
    )

# ================= MY BOTS =================

@main_bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def mybots(message):

    uid = message.from_user.id

    bots = bots_db.find({"owner": uid})

    text = "🤖 Your Bots\n\n"

    count = 0

    for b in bots:

        text += f"{b['username']}\n"
        count += 1

    if count == 0:

        text = "❌ No bots added."

    main_bot.send_message(message.chat.id, text)

# ================= RECEIVE TOKEN =================

@main_bot.message_handler(func=lambda m: m.from_user.id in user_state)
def receive_token(message):

    uid = message.from_user.id
    token = message.text.strip()

    try:

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe"
        ).json()

        if not r["ok"]:

            main_bot.send_message(
                message.chat.id,
                "❌ Invalid Token"
            )

            return

        username = "@" + r["result"]["username"]

    except:

        main_bot.send_message(
            message.chat.id,
            "❌ Token check failed"
        )

        return

    if bots_db.find_one({"token": token}):

        main_bot.send_message(
            message.chat.id,
            "⚠️ Bot already added"
        )

        return

    bots_db.insert_one({

        "owner": uid,
        "token": token,
        "username": username,
        "verified_users": 0

    })

    del user_state[uid]

    main_bot.send_message(
        message.chat.id,
        f"✅ Bot Added\n\n{username}"
    )

    admin_bot.send_message(
        ADMIN_ID,
        f"🆕 New Bot Added\n\nOwner: {uid}\nBot: {username}"
    )

# ================= VERIFY BOT =================

@verify_bot.message_handler(commands=["start"])
def verify_start(message):

    uid = message.from_user.id

    save_user(uid)

    verify_bot.send_message(
        message.chat.id,
        "✅ You are verified!"
    )

# ================= ADMIN PANEL =================

@admin_bot.message_handler(commands=["start"])
def admin_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    users = users_db.count_documents({})
    bots = bots_db.count_documents({})

    admin_bot.send_message(
        message.chat.id,
        f"""
📊 SYSTEM STATS

👤 Users: {users}
🤖 Bots: {bots}
"""
    )

# ================= RUN =================

print("System Running...")

import threading

threading.Thread(
    target=lambda: main_bot.infinity_polling(skip_pending=True)
).start()

threading.Thread(
    target=lambda: verify_bot.infinity_polling(skip_pending=True)
).start()

threading.Thread(
    target=lambda: admin_bot.infinity_polling(skip_pending=True)
).start()
