import telebot
import os
import time
import threading
from pymongo import MongoClient

# -------- MONGODB CONNECTION --------

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]

# -------- RUNNING BOTS STORAGE --------

running_bots = {}

# -------- SAVE USER --------

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# -------- START USER BOT --------

def start_user_bot(token):

    if token in running_bots:
        return

    try:

        bot = telebot.TeleBot(token)

        @bot.message_handler(commands=["start"])
        def start(message):

            uid = message.from_user.id

            save_user(uid)

            bot.send_message(
                message.chat.id,
                "✅ Bot is working!\n\nThis bot is connected to Verify System."
            )

        running_bots[token] = bot

        print("✅ Started bot:", token)

        bot.infinity_polling(skip_pending=True)

    except Exception as e:

        print("❌ Bot start error:", e)

# -------- LOAD ALL BOTS FROM DATABASE --------

def load_all_bots():

    bots = bots_collection.find()

    for b in bots:

        token = b.get("token")

        if not token:
            continue

        if token not in running_bots:

            threading.Thread(
                target=start_user_bot,
                args=(token,),
                daemon=True
            ).start()

# -------- RUNNER LOOP --------

print("🚀 Runner Started...")

while True:

    try:

        load_all_bots()

    except Exception as e:

        print("Runner error:", e)

    time.sleep(20)
