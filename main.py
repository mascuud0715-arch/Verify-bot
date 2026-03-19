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

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================= TELEGRAM BOT =================

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=5
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

# indexes
bots_collection.create_index("token")
bots_collection.create_index("username")
bots_collection.create_index("owner")
users_collection.create_index("user_id")
channels_collection.create_index("username")

# ================= INIT SYSTEM =================

def init_system():
    try:
        data = system_collection.find_one({"name": "system"})

        if not data:
            system_collection.insert_one({
                "name": "system",
                "bots_status": True,
                "verify_status": True,
                "channels_status": True
            })
    except Exception as e:
        print("Init error:", e)

init_system()

# ================= FLASK =================

app = Flask(__name__)

# ================= SAVE USER =================

def save_user(user, bot_username="main"):
    try:
        users_collection.update_one(
            {
                "user_id": user.id,
                "bot": bot_username
            },
            {
                "$set": {
                    "user_id": user.id,
                    "username": user.username,
                    "bot": bot_username
                }
            },
            upsert=True
        )
    except Exception as e:
        print("Save user error:", e)

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

# ================= CHECK CHANNELS =================

def check_channels(user_id):

    not_joined = []

    try:
        for ch in channels_collection.find({"active": True}):

            username = ch.get("username")

            if not username:
                continue

            try:
                member = bot.get_chat_member(username, int(user_id))

                if member.status not in ["member", "administrator", "creator"]:
                    not_joined.append(username)

            except:
                not_joined.append(username)

    except Exception as e:
        print("Channel check error:", e)

    return not_joined

# ================= FORCE JOIN =================

def send_force_join(chat_id):

    channels = list(channels_collection.find({"active": True}))

    if not channels:
        return False

    kb = InlineKeyboardMarkup()

    for ch in channels:
        username = ch.get("username")

        if not username:
            continue

        kb.add(
            InlineKeyboardButton(
                "📢 Join Channel",
                url=f"https://t.me/{username.replace('@','')}"
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
        "⚠️ Please join all channels",
        reply_markup=kb
    )

    return True

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    try:
        active = channels_collection.count_documents({"active": True})

        if active > 0:

            not_joined = check_channels(message.from_user.id)

            if not_joined:
                send_force_join(message.chat.id)
                return

    except Exception as e:
        print("Start error:", e)

    text = """
🤖 Welcome to Bot System

You can connect your own Telegram bot and turn it into a **TikTok downloader**.

📥 Features your bot will have:

• Download TikTok videos  
• Download TikTok photo slides  
• Work automatically for users  
• Ultra fast downloads  

⚙️ Setup Steps

1️⃣ Create bot via @BotFather  
2️⃣ Copy Bot Token  
3️⃣ Click ➕ Add Bot  
4️⃣ Send token  

🚀 Your bot will start automatically.
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )

# ================= CONFIRM JOIN =================

@bot.callback_query_handler(func=lambda c: c.data == "confirm_join")
def confirm_join(call):

    not_joined = check_channels(call.from_user.id)

    if not not_joined:

        bot.answer_callback_query(call.id, "✅ Done")

        bot.send_message(
            call.message.chat.id,
            "🎉 Verified",
            reply_markup=main_menu()
        )

    else:
        bot.answer_callback_query(
            call.id,
            "❌ Join all first",
            show_alert=True
        )

# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send your bot token"
    )

    bot.register_next_step_handler(msg, save_bot)

def save_bot(message):

    token = message.text.strip()

    if ":" not in token:
        return bot.send_message(message.chat.id, "❌ Invalid token")

    try:

        test_bot = telebot.TeleBot(token, threaded=False)
        me = test_bot.get_me()

        username = me.username

        bots_collection.update_one(
            {"username": username},
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
            f"✅ Bot Added\n\n@{username}"
        )

    except Exception as e:
        print("Add bot error:", e)
        bot.send_message(message.chat.id, "❌ Token error")

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
        if b.get("username"):
            text += f"@{b['username']}\n"
            found = True

    if not found:
        text = "❌ No bots"

    bot.send_message(message.chat.id, text)

# ================= REMOVE BOT =================

@bot.message_handler(func=lambda m: m.text == "❌ Remove Bot")
def remove_bot(message):

    msg = bot.send_message(message.chat.id, "Send @username")

    bot.register_next_step_handler(msg, remove_bot_process)

def remove_bot_process(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:
        return bot.send_message(message.chat.id, "❌ Not found")

    if bot_data["owner"] != message.from_user.id:
        return bot.send_message(message.chat.id, "❌ Not yours")

    bots_collection.delete_one({"username": username})

    bot.send_message(message.chat.id, f"✅ @{username} removed")

# ================= STATS =================

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    users = users_collection.count_documents({})
    bots = bots_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"👤 Users: {users}\n🤖 Bots: {bots}"
    )

# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"status": "error"})

    active = channels_collection.count_documents({"active": True})

    if active == 0:
        return jsonify({"status": "joined"})

    not_joined = check_channels(user_id)

    if not not_joined:
        return jsonify({"status": "joined"})

    return jsonify({
        "status": "not_joined",
        "channels": not_joined
    })

# ================= RUN MAIN =================

def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Bot crash:", e)
            time.sleep(5)

def start_runner():
    try:
        import running
        threading.Thread(target=running.start_system, daemon=True).start()
    except Exception as e:
        print("Runner error:", e)

# ================= MAIN =================

if __name__ == "__main__":

    start_runner()

    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)
