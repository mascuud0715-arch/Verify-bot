import telebot
import os
import time
import threading
from telebot.types import *
from pymongo import MongoClient
from flask import Flask, request, jsonify

# ================= ENV =================

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

ADMIN_ID = 7983838654

# ================= TELEBOT =================

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=100
)

# ================= DATABASE =================

client = MongoClient(
    MONGO_URL,
    maxPoolSize=200
)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
system_collection = db["system"]

bots_collection.create_index("token")
bots_collection.create_index("owner")
bots_collection.create_index("username")

# ================= FLASK =================

app = Flask(__name__)

# ================= SAVE USER =================

def save_user(user):

    users_collection.update_one(
        {"user_id": user.id},
        {
            "$set":{
                "user_id": user.id,
                "username": user.username
            }
        },
        upsert=True
    )

# ================= MAIN MENU =================

def main_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("➕ Add Bot"),
        KeyboardButton("🤖 My Bots")
    )

    kb.add(
        KeyboardButton("❌ Remove Bot")
    )

    return kb

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    text = """
🤖 Welcome to Verify Bot System

This system allows you to connect your own Telegram bot and turn it into a powerful TikTok downloader.

📥 What your bot will do:
• Download TikTok videos
• Download TikTok photo slides
• Work automatically for your users
• Show download credits via your bot

⚙️ How to setup your bot:

1️⃣ Create a bot using @BotFather  
2️⃣ Copy the Bot Token  
3️⃣ Click ➕ Add Bot and send the token  

🚀 After adding your bot, it will start automatically and become a TikTok downloader.

Choose an option below to continue.
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )

# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    user_bots = bots_collection.count_documents({
        "owner": message.from_user.id,
        "active": True
    })

    if user_bots >= 5:

        bot.send_message(
            message.chat.id,
            "❌ You reached number of limit bots\n\nRemove bots to add new bot"
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "Send your bot token from @BotFather"
    )

    bot.register_next_step_handler(
        msg,
        save_bot
    )

# ================= SAVE BOT =================

def save_bot(message):

    token = message.text.strip()

    if ":" not in token:

        bot.send_message(
            message.chat.id,
            "❌ Invalid token format"
        )
        return

    try:

        test_bot = telebot.TeleBot(token)

        me = test_bot.get_me()

        username = me.username

        exist = bots_collection.find_one({
            "username": username
        })

        if exist:

            bot.send_message(
                message.chat.id,
                "❌ This bot already added"
            )
            return

        bots_collection.insert_one({

            "token": token,
            "username": username,
            "owner": message.from_user.id,
            "active": True,
            "created": time.time()

        })

        bot.send_message(
            message.chat.id,
            f"""
✅ Bot Added Successfully

🤖 Bot: @{username}

Your bot will start automatically.
"""
        )

    except Exception as e:

        print("Bot add error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Invalid bot token or bot not started.\n\nStart your bot first then send the token."
        )

# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    bots = bots_collection.find({
        "owner": message.from_user.id,
        "active": True
    })

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        text += f"@{b['username']}\n"
        found = True

    if not found:

        text = "❌ No bots yet"

    bot.send_message(
        message.chat.id,
        text
    )

# ================= REMOVE BOT =================

@bot.message_handler(func=lambda m: m.text == "❌ Remove Bot")
def remove_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send bot username to remove\n\nExample:\n@mybot"
    )

    bot.register_next_step_handler(
        msg,
        remove_bot_process
    )


def remove_bot_process(message):

    username = message.text.replace("@","").strip()

    try:

        bot_data = bots_collection.find_one({
            "username": username,
            "owner": message.from_user.id,
            "active": True
        })

        if not bot_data:

            bot.send_message(
                message.chat.id,
                "❌ Bot not found or you are not owner"
            )
            return

        bots_collection.update_one(
            {"username": username},
            {"$set": {"active": False}}
        )

        bot.send_message(
            message.chat.id,
            f"✅ @{username} removed successfully"
        )

    except Exception as e:

        print("Remove bot error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Error removing bot"
        )


# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:

        return jsonify({
            "status": "error"
        })

    try:

        channels = channels_collection.find({"active": True})

        not_joined = []

        for ch in channels:

            username = ch.get("username")

            try:

                member = bot.get_chat_member(
                    username,
                    int(user_id)
                )

                if member.status not in [
                    "member",
                    "administrator",
                    "creator"
                ]:

                    not_joined.append(username)

            except:

                not_joined.append(username)

        if len(not_joined) == 0:

            return jsonify({
                "status": "joined"
            })

        else:

            return jsonify({
                "status": "not_joined",
                "channels": not_joined
            })

    except Exception as e:

        print("Verify API error:", e)

        return jsonify({
            "status": "error"
        })


# ================= STATS =================

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        total_users = users_collection.count_documents({})

        total_bots = bots_collection.count_documents({
            "active": True
        })

        text = f"""
📊 System Statistics

👤 Users: {total_users}
🤖 Bots: {total_bots}
"""

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Stats error:", e)


# ================= BOT RUN =================

def run_bot():

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print("BOT ERROR:", e)

            time.sleep(5)


# ================= START SYSTEM =================

if __name__ == "__main__":

    print("🚀 Main Bot Running...")
    print("🌐 API Running...")

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
        )
