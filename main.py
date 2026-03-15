import telebot
import os
import time
from telebot.types import *
from pymongo import MongoClient
from flask import Flask, request, jsonify
import threading

# ================= ENV =================

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]

# ================= FLASK APP =================

app = Flask(__name__)

# ================= MENU =================

def main_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(KeyboardButton("➕ Add Bot"))
    kb.add(KeyboardButton("🤖 My Bots"))

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

    channels = channels_collection.find({"active": True})

    not_joined = []

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

# ================= FORCE JOIN MESSAGE =================

def send_force_join(chat_id, channels):

    kb = InlineKeyboardMarkup()

    for ch in channels:

        link = f"https://t.me/{ch.replace('@','')}"

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

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    not_joined = check_channels(message.from_user.id)

    if not_joined:

        send_force_join(
            message.chat.id,
            not_joined
        )
        return

    text = """
🤖 Welcome to Verify Bot System

Add your Telegram bot and turn it into a downloader.

Steps:

1️⃣ Create bot via @BotFather
2️⃣ Copy the token
3️⃣ Click Add Bot
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )

# ================= CONFIRM JOIN =================

@bot.callback_query_handler(func=lambda c:c.data=="confirm_join")
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

@bot.message_handler(func=lambda m:m.text=="➕ Add Bot")
def add_bot(message):

    bot.send_message(
        message.chat.id,
        "Send your bot token from @BotFather"
    )

    bot.register_next_step_handler(message, save_bot)

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
                "owner": message.from_user.id
            }},
            upsert=True
        )

        bot.send_message(
            message.chat.id,
            f"✅ Bot Added\n\n@{info.username}"
        )

    except:

        bot.send_message(
            message.chat.id,
            "❌ Invalid bot token"
        )

# ================= MY BOTS =================

@bot.message_handler(func=lambda m:m.text=="🤖 My Bots")
def my_bots(message):

    bots = bots_collection.find({"owner": message.from_user.id})

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

# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"status":"error"})

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

            print(e)
            time.sleep(5)

# ================= START SYSTEM =================

if __name__ == "__main__":

    print("🚀 Main Bot Running...")
    print("🌐 Verify API Running...")

    threading.Thread(target=run_bot).start()

    app.run(
        host="0.0.0.0",
        port=5000
    )
