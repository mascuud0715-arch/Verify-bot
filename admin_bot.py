import telebot
import os

from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from pymongo import MongoClient


# ==============================
# ENV
# ==============================

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)


# ==============================
# DATABASE
# ==============================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
downloads_collection = db["downloads"]
system_collection = db["system"]


# ==============================
# STATES
# ==============================

broadcast_mode = False

broadcast_data = {
    "text": None,
    "buttons": [],
    "style": ""
}


# ==============================
# ADMIN MENU
# ==============================

def admin_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("📊 Stats"),
        KeyboardButton("📊 Media Stats")
    )

    kb.add(
        KeyboardButton("🤖 Bots"),
        KeyboardButton("🔥 Top Bots")
    )

    kb.add(
        KeyboardButton("📢 Broadcast")
    )

    kb.add(
        KeyboardButton("➕ Add Channel"),
        KeyboardButton("📡 Channels")
    )

    kb.add(
        KeyboardButton("❌ Close Channels")
    )

    kb.add(
        KeyboardButton("🚫 Close Bots"),
        KeyboardButton("✅ Open Bots")
    )

    kb.add(
        KeyboardButton("🟢 Verify ON"),
        KeyboardButton("🔴 Verify OFF")
    )

    return kb


# ==============================
# START
# ==============================

@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "❌ Not Allowed"
        )
        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )


# ==============================
# SYSTEM STATS
# ==============================

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):

    bots = bots_collection.count_documents({})
    users = users_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"""
📊 SYSTEM STATS

🤖 Bots: {bots}
👤 Users: {users}
"""
    )


# ==============================
# MEDIA STATS (UPDATED)
# ==============================

@bot.message_handler(func=lambda m: m.text == "📊 Media Stats")
def media_stats(message):

    total_download = downloads_collection.count_documents({})
    total_video = downloads_collection.count_documents({"type":"video"})
    total_photo = downloads_collection.count_documents({"type":"photo"})

    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 3}
    ]

    top_users = list(downloads_collection.aggregate(pipeline))

    top_text = ""

    i = 1

    for u in top_users:

        top_text += f"{i} - {u['_id']} ({u['count']})\n"
        i += 1

    if top_text == "":
        top_text = "No data"

    bot.send_message(
        message.chat.id,
        f"""
📥 DOWNLOAD STATS

📦 Total Downloads: {total_download}
🎬 Total Videos: {total_video}
🖼 Total Photos: {total_photo}

🏆 TOP USERS
{top_text}
"""
    )


# ==============================
# TOP BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🔥 Top Bots")
def top_bots(message):

    pipeline = [
        {
            "$group": {
                "_id": "$bot_username",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]

    bots = list(downloads_collection.aggregate(pipeline))

    text = "🔥 TOP 20 BOTS\n\n"

    i = 1

    for b in bots:

        text += f"{i} - @{b['_id']} ({b['count']})\n"
        i += 1

    if i == 1:
        text = "No download data"

    bot.send_message(
        message.chat.id,
        text
    )

# ==============================
# BOTS PANEL
# ==============================

@bot.message_handler(func=lambda m: m.text == "🤖 Bots")
def bots_panel(message):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "👤 Usernames",
            callback_data="bot_usernames"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🔑 API Tokens",
            callback_data="bot_api"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🗑 Remove Bot",
            callback_data="remove_bot"
        )
    )

    bot.send_message(
        message.chat.id,
        "🤖 Bots Panel",
        reply_markup=kb
    )


# ==============================
# SHOW BOT USERNAMES
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "bot_usernames")
def bot_usernames(call):

    bots = bots_collection.find()

    text = "🤖 Bots Usernames\n\n"

    i = 1

    for b in bots:

        text += f"{i}: @{b.get('username')}\n"

        i += 1

    if i == 1:
        text = "❌ No bots found"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ==============================
# SHOW BOT TOKENS
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "bot_api")
def bot_api(call):

    bots = bots_collection.find()

    text = "🔑 Bots API\n\n"

    i = 1

    for b in bots:

        text += f"{i}: {b.get('token')}\n\n"

        i += 1

    if i == 1:
        text = "❌ No bots found"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ==============================
# REMOVE BOT START
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "remove_bot")
def remove_bot_start(call):

    msg = bot.send_message(
        call.message.chat.id,
        "Send bot username to remove\nExample:\n@mybot"
    )

    bot.register_next_step_handler(msg, remove_bot_process)


# ==============================
# REMOVE BOT PROCESS
# ==============================

def remove_bot_process(message):

    username = message.text.replace("@","").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:

        bot.send_message(
            message.chat.id,
            "❌ Bot not found"
        )
        return

    # delete bot from database
    bots_collection.delete_one({"username": username})

    # also delete related downloads (optional cleanup)
    downloads_collection.delete_many({"bot_username": username})

    bot.send_message(
        message.chat.id,
        f"""
🗑 BOT REMOVED

🤖 Username: @{username}
🔑 API Token: Deleted
📦 System: Cleaned
"""
    )

# ==============================
# ADD CHANNEL
# ==============================

@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(message):

    total = channels_collection.count_documents({"active": True})

    if total >= 5:

        bot.send_message(
            message.chat.id,
            "❌ Maximum 5 channels allowed"
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "Send channel username\nExample:\n@channel"
    )

    bot.register_next_step_handler(msg, save_channel)


def save_channel(message):

    channel = message.text.strip()

    channels_collection.update_one(
        {"username": channel},
        {
            "$set": {
                "username": channel,
                "active": True
            }
        },
        upsert=True
    )

    system_collection.update_one(
        {"system": "verify"},
        {"$set": {"active": True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        f"✅ Channel Added\n{channel}"
    )


# ==============================
# CHANNEL LIST
# ==============================

@bot.message_handler(func=lambda m: m.text == "📡 Channels")
def channels(message):

    channels = channels_collection.find({"active": True})

    text = "📡 Force Join Channels\n\n"

    count = 0

    for c in channels:

        text += c["username"] + "\n"
        count += 1

    if count == 0:
        text = "❌ No active channels"

    bot.send_message(
        message.chat.id,
        text
    )


# ==============================
# CLOSE CHANNELS
# ==============================

@bot.message_handler(func=lambda m: m.text == "❌ Close Channels")
def close_channels(message):

    channels_collection.update_many(
        {},
        {"$set": {"active": False}}
    )

    system_collection.update_one(
        {"name": "system"},
        {"$set": {"channels_status": False}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "❌ Force Join System Disabled"
    )


# ==============================
# CLOSE BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🚫 Close Bots")
def close_bots(message):

    system_collection.update_one(
        {"name": "system"},
        {"$set": {"bots_status": False}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🚫 All bots stopped"
    )


# ==============================
# OPEN BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "✅ Open Bots")
def open_bots(message):

    system_collection.update_one(
        {"name": "system"},
        {"$set": {"bots_status": True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "✅ Bots activated"
    )


# ==============================
# VERIFY ON
# ==============================

@bot.message_handler(func=lambda m: m.text == "🟢 Verify ON")
def verify_on(message):

    system_collection.update_one(
        {"name": "system"},
        {"$set": {"verify_status": True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🟢 Verification Enabled"
    )


# ==============================
# VERIFY OFF
# ==============================

@bot.message_handler(func=lambda m: m.text == "🔴 Verify OFF")
def verify_off(message):

    system_collection.update_one(
        {"name": "system"},
        {"$set": {"verify_status": False}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🔴 Verification Disabled"
    )


# ==============================
# BROADCAST MENU
# ==============================

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):

    global broadcast_mode

    broadcast_mode = True
    broadcast_data["text"] = None
    broadcast_data["buttons"] = []

    bot.send_message(
        message.chat.id,
        "📢 Send broadcast text"
    )


# ==============================
# RECEIVE TEXT
# ==============================

@bot.message_handler(func=lambda m: broadcast_mode and broadcast_data["text"] is None)
def get_text(message):

    broadcast_data["text"] = message.text

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("➕ Add Inline", callback_data="add_inline")
    )

    kb.add(
        InlineKeyboardButton("🎨 Color", callback_data="color")
    )

    kb.add(
        InlineKeyboardButton("👀 Preview", callback_data="preview")
    )

    kb.add(
        InlineKeyboardButton("📤 Send Broadcast", callback_data="send_bc")
    )

    bot.send_message(
        message.chat.id,
        "Message saved. Choose option:",
        reply_markup=kb
    )


# ==============================
# RUN BOT
# ==============================

print("Admin Bot Running...")

bot.infinity_polling(skip_pending=True)
