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
        KeyboardButton("🤖 Bots")
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

    kb.add(
    KeyboardButton("🔄 Refresh Bots")
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
# MEDIA STATS
# ==============================

@bot.message_handler(func=lambda m: m.text == "📊 Media Stats")
def media_stats(message):

    tiktok = downloads_collection.count_documents({"type":"tiktok_video"})
    photo = downloads_collection.count_documents({"type":"photo"})
    total = downloads_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"""
📥 DOWNLOAD STATS

🎬 TikTok Videos: {tiktok}
🖼 Photos: {photo}
📦 Total Downloads: {total}
"""
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

        text += f"{i}: {b.get('username')}\n"

        i += 1

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
        "🗑 Send bot username to remove\n\nExample:\n@mybot"
    )

    bot.register_next_step_handler(msg, remove_bot_process)


# ==============================
# REMOVE BOT PROCESS
# ==============================

def remove_bot_process(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:

        bot.send_message(
            message.chat.id,
            "❌ Bot not found in system"
        )
        return

    # delete bot from bots collection
    bots_collection.delete_one({"username": username})

    # delete downloads related to this bot
    downloads_collection.delete_many({"bot_username": username})

    # optional: remove bot users data
    users_collection.update_many(
        {},
        {"$pull": {"bots": username}}
    )

    bot.send_message(
        message.chat.id,
        f"""
✅ BOT REMOVED SUCCESSFULLY

🤖 Username: @{username}
🔑 API Token: Deleted
📦 Downloads: Cleaned
🚫 Bot cannot work anymore
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
    {"$set": {"bots_status": False}},
    upsert=True
    )

    bot.send_message(
        message.chat.id,
        "❌ Force Join System Disabled"
    )

# ==============================
# REFRESH BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Bots")
def refresh_bots(message):

    bots = list(bots_collection.find())

    total = len(bots)

    bot.send_message(
        message.chat.id,
        f"""
🔄 SYSTEM REFRESHED

🤖 Active Bots: {total}

Removed bots cleared from system.
"""
    )


# ==============================
# CLOSE BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🚫 Close Bots")
def close_bots(message):

    system_collection.update_one(
        {"system": "bots"},
        {"$set": {"active": False}},
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
# ADD INLINE BUTTON
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "add_inline")
def add_inline(call):

    msg = bot.send_message(
        call.message.chat.id,
        "Send button text"
    )

    bot.register_next_step_handler(msg, inline_text)


def inline_text(message):

    text = message.text

    msg = bot.send_message(
        message.chat.id,
        "Send button URL"
    )

    bot.register_next_step_handler(msg, inline_url, text)


def inline_url(message, text):

    if len(broadcast_data["buttons"]) >= 5:

        bot.send_message(
            message.chat.id,
            "❌ Max 5 buttons allowed"
        )
        return

    broadcast_data["buttons"].append(
        (text, message.text)
    )

    bot.send_message(
        message.chat.id,
        "✅ Button added"
    )


# ==============================
# COLOR STYLE
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "color")
def color_menu(call):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("🔴 Red", callback_data="style_red")
    )

    kb.add(
        InlineKeyboardButton("🟢 Green", callback_data="style_green")
    )

    kb.add(
        InlineKeyboardButton("🔵 Blue", callback_data="style_blue")
    )

    bot.send_message(
        call.message.chat.id,
        "Choose style",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("style"))
def set_style(call):

    if call.data == "style_red":
        broadcast_data["style"] = "🔴"

    if call.data == "style_green":
        broadcast_data["style"] = "🟢"

    if call.data == "style_blue":
        broadcast_data["style"] = "🔵"

    bot.send_message(
        call.message.chat.id,
        "✅ Style applied"
    )


# ==============================
# PREVIEW
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):

    text = f"{broadcast_data['style']} {broadcast_data['text']}"

    kb = InlineKeyboardMarkup()

    for b in broadcast_data["buttons"]:

        kb.add(
            InlineKeyboardButton(
                b[0],
                url=b[1]
            )
        )

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=kb
    )


# ==============================
# SEND BROADCAST
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "send_bc")
def send_broadcast(call):

    global broadcast_mode

    text = f"{broadcast_data['style']} {broadcast_data['text']}"

    kb = InlineKeyboardMarkup()

    for b in broadcast_data["buttons"]:
        kb.add(
            InlineKeyboardButton(
                b[0],
                url=b[1]
            )
        )

    bots = list(bots_collection.find())
    users = list(users_collection.find())

    bots_used = 0
    delivered = 0

    for b in bots:

        try:

            send_bot = telebot.TeleBot(b["token"])
            bots_used += 1

            for u in users:

                try:

                    send_bot.send_message(
                        u["user_id"],
                        text,
                        reply_markup=kb
                    )

                    delivered += 1

                except:
                    pass

        except:
            pass

    broadcast_mode = False

    bot.send_message(
        call.message.chat.id,
        f"""
📢 BROADCAST SENT

🤖 Bots Used: {bots_used}
👥 Total Users: {len(users)}
📬 Delivered: {delivered}
"""
    )


# ==============================
# RUN BOT
# ==============================

print("Admin Bot Running...")

bot.infinity_polling(skip_pending=True)
