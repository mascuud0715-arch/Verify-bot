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
    threaded=False
)

# ================= DATABASE =================

client = MongoClient(
    MONGO_URL,
    maxPoolSize=100
)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
system_collection = db["system"]

bots_collection.create_index("token")
bots_collection.create_index("owner")

# ================= INIT SYSTEM =================

def init_system():

    try:

        data = system_collection.find_one({"name": "system"})

        if not data:

            system_collection.insert_one({
                "name": "system",
                "bots_status": True,
                "verify_status": True
            })

    except Exception as e:

        print("Init system error:", e)


init_system()

# ================= FLASK =================

app = Flask(__name__)

# ================= SAVE USER =================

def save_user(user):

    try:

        users_collection.update_one(
            {"user_id": user.id},
            {
                "$set": {
                    "user_id": user.id,
                    "username": user.username
                }
            },
            upsert=True
        )

    except Exception as e:

        print("Save user error:", e)

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

# ================= CHECK CHANNELS =================

def check_channels(user_id):

    not_joined = []

    try:

        channels = channels_collection.find({"active": True})

        for ch in channels:

            username = ch.get("username")

            if not username:
                continue

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

    except Exception as e:

        print("Check channel error:", e)

    return not_joined

# ================= CHANNELS API =================

@app.route("/channels")
def get_channels():

    channels = []

    try:

        for ch in channels_collection.find({"active": True}):

            username = ch.get("username")

            if username:
                channels.append(username)

    except Exception as e:

        print("Channel API error:", e)

    return jsonify({
        "channels": channels
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

    try:

        active_channels = channels_collection.count_documents(
            {"active": True}
        )

        if active_channels > 0:

            not_joined = check_channels(
                message.from_user.id
            )

            if not not_joined:

                pass

            else:

                send_force_join(
                    message.chat.id
                )

                return

    except Exception as e:

        print("Start check error:", e)

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

    if not not_joined:

        bot.answer_callback_query(
            call.id,
            "✅ Verification successful"
        )

        bot.send_message(
            call.message.chat.id,
            "🎉 Verification successful",
            reply_markup=main_menu()
        )

    else:

        bot.answer_callback_query(
            call.id,
            "❌ Join all channels first",
            show_alert=True
        )

# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

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

        bots_collection.update_one(
            {"token": token},
            {
                "$set": {
                    "token": token,
                    "username": username,
                    "owner": message.from_user.id,
                    "active": True,
                    "created": time.time()
                }
            },
            upsert=True
        )

        bot.send_message(
            message.chat.id,
f"""✅ Bot Added Successfully

🤖 Bot: @{username}

🚀 Your bot will automatically become a TikTok downloader.

Send any TikTok link to your bot and it will download instantly."""
        )

        print("New bot added:", username)

    except Exception as e:

        print("Bot add error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Invalid bot token.\nMake sure you started the bot first."
        )

# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    try:

        bots = bots_collection.find({
            "owner": message.from_user.id,
            "active": True
        })

        text = "🤖 Your Bots\n\n"

        found = False

        for b in bots:

            username = b.get("username")

            if username:

                text += f"@{username}\n"
                found = True

        if not found:

            text = "❌ No bots yet"

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("My bots error:", e)

# ================= REMOVE BOT =================

@bot.message_handler(func=lambda m: m.text == "❌ Remove Bot")
def remove_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send bot username to remove\nExample:\n@mybot"
    )

    bot.register_next_step_handler(
        msg,
        remove_bot_process
    )

def remove_bot_process(message):

    username = message.text.replace("@", "")

    try:

        bot_data = bots_collection.find_one({"username": username})

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
            {"username": username},
            {"$set": {"active": False}}
        )

        bot.send_message(
            message.chat.id,
            f"✅ @{username} removed and disabled"
        )

    except Exception as e:

        print("Remove bot error:", e)

# ================= STATS =================

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        total_users = users_collection.count_documents({})
        total_bots = bots_collection.count_documents({})

        text = f"""
📊 System Statistics

👤 Total Users: {total_users}
🤖 Total Bots: {total_bots}
"""

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Stats error:", e)

# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:

        return jsonify({"status": "error"})

    try:

        active_channels = channels_collection.count_documents({"active": True})

        if active_channels == 0:

            return jsonify({"status": "joined"})

        not_joined = check_channels(user_id)

        if not not_joined:

            return jsonify({"status": "joined"})

        else:

            return jsonify({
                "status": "not_joined",
                "channels": not_joined
            })

    except Exception as e:

        print("Verify API error:", e)

        return jsonify({"status": "error"})

# ================= RUN BOT =================

def run_bot():

    while True:

        try:

            print("🤖 Verify Bot Running...")

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

        except Exception as e:

            print("Bot crashed:", e)

            time.sleep(5)

# ================= START =================

if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
        )
