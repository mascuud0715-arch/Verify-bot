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

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

client = MongoClient(MONGO_URL)
db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
system_collection = db["system"]

# ================= FLASK =================

app = Flask(__name__)

# ================= MENU =================

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

# ================= SAVE USER =================

def save_user(user):

    users_collection.update_one(
        {"user_id": user.id},
        {"$set":{
            "user_id": user.id,
            "username": user.username
        }},
        upsert=True
    )

# ================= CHECK CHANNELS =================

def check_channels(user_id):

    not_joined = []

    channels = channels_collection.find({"active": True})

    for ch in channels:

        try:

            member = bot.get_chat_member(
                ch["username"],
                int(user_id)
            )

            if member.status not in ["member","administrator","creator"]:

                not_joined.append(ch["username"])

        except:

            not_joined.append(ch["username"])

    return not_joined

# ================= GET CHANNELS API =================

@app.route("/channels")
def get_channels():

    channels = []

    for ch in channels_collection.find({"active":True}):

        channels.append(ch["username"])

    return jsonify({
        "channels":channels
    })

# ================= FORCE JOIN =================

def send_force_join(chat_id):

    channels = list(channels_collection.find({"active": True}))

    if len(channels) == 0:
        return False

    kb = InlineKeyboardMarkup()

    for ch in channels:

        username = ch.get("username")

        if not username:
            continue

        link = f"https://t.me/{username.replace('@','')}"

        kb.add(
            InlineKeyboardButton(
                "📢 Join Channel",
                url=link
            )
        )

    kb.add(
        InlineKeyboardButton(
            "✅ Confirm",
            callback_data="confirm_join"
        )
    )

    bot.send_message(
        chat_id,
        "⚠️ Please join all channels to continue",
        reply_markup=kb
    )

    return True

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    active_channels = channels_collection.count_documents({"active":True})

    if active_channels > 0:

        not_joined = check_channels(message.from_user.id)

        if not_joined:

            send_force_join(message.chat.id)
            return

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

# ================= CONFIRM JOIN =================

@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):

    user_id = call.from_user.id

    not_joined = check_channels(user_id)

    if not_joined:

        bot.answer_callback_query(
            call.id,
            "❌ Join all channels first",
            show_alert=True
        )
        return

    bot.answer_callback_query(
        call.id,
        "✅ Verification successful"
    )

    bot.send_message(
        call.message.chat.id,
        "🎉 Verification successful",
        reply_markup=main_menu()
    )

# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send your bot token from @BotFather"
    )

    bot.register_next_step_handler(msg, save_bot)

# ================= SAVE BOT =================

def save_bot(message):

    token = message.text.strip()

    try:

        new_bot = telebot.TeleBot(token)

        info = new_bot.get_me()

        bots_collection.update_one(
            {"token": token},
            {"$set":{
                "token": token,
                "username": info.username,
                "owner": message.from_user.id,
                "active":True
            }},
            upsert=True
        )

        bot.send_message(
            message.chat.id,
            f"✅ Bot Added\n\n@{info.username}\n\nRunner will start it automatically."
        )

    except:

        bot.send_message(
            message.chat.id,
            "❌ Invalid bot token"
        )

# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    bots = bots_collection.find({"owner": message.from_user.id})

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        text += f"@{b['username']}\n"
        found = True

    if not found:

        text = "❌ No bots yet"

    bot.send_message(message.chat.id, text)

# ================= REMOVE BOT =================

@bot.message_handler(func=lambda m: m.text == "❌ Remove Bot")
def remove_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send bot username to remove\n\nExample:\n@mybot"
    )

    bot.register_next_step_handler(msg, remove_bot_process)

def remove_bot_process(message):

    username = message.text.replace("@","")

    bot_data = bots_collection.find_one({"username":username})

    if not bot_data:

        bot.send_message(
            message.chat.id,
            "❌ Bot not found"
        )
        return

    if bot_data["owner"] != message.from_user.id:

        bot.send_message(
            message.chat.id,
            "❌ You are not owner of this bot"
        )
        return

    bots_collection.update_one(
        {"username":username},
        {"$set":{"active":False}}
    )

    bot.send_message(
        message.chat.id,
        f"✅ @{username} removed and disabled"
    )

# ================= STATS =================

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    total_users = users_collection.count_documents({})

    text = f"""
📊 Bot Statistics

👤 Total Users: {total_users}
"""

    bot.send_message(
        message.chat.id,
        text
    )

# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"status":"error"})

    active_channels = channels_collection.count_documents({"active": True})

    if active_channels == 0:
        return jsonify({"status":"joined"})

    not_joined = check_channels(user_id)

    if not not_joined:

        return jsonify({
            "status":"joined"
        })

    else:

        return jsonify({
            "status":"not_joined",
            "channels":not_joined
        })

# ================= RUN BOT =================

def run_bot():

    while True:

        try:

            bot.infinity_polling(skip_pending=True)

        except Exception as e:

            print("BOT ERROR:", e)
            time.sleep(5)

# ================= START =================

if __name__ == "__main__":

    print("🚀 Main Bot Running...")
    print("🌐 Verify API Running...")

    threading.Thread(target=run_bot).start()

    port = int(os.environ.get("PORT",5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
