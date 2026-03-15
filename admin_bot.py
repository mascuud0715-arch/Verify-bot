import telebot
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ---------- ENV ----------

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# ---------- MONGODB ----------

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
downloads_collection = db["downloads"]
system_collection = db["system"]

# ---------- MENU ----------

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

    return kb


# ---------- START ----------

@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:

        bot.send_message(message.chat.id,"❌ Not Allowed")

        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )


# ---------- STATS ----------

@bot.message_handler(func=lambda m:m.text=="📊 Stats")
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


# ---------- MEDIA STATS ----------

@bot.message_handler(func=lambda m:m.text=="📊 Media Stats")
def media_stats(message):

    tiktok = downloads_collection.count_documents({"type":"tiktok"})
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


# ---------- BOTS PANEL ----------

@bot.message_handler(func=lambda m:m.text=="🤖 Bots")
def bots_panel(message):

    kb=InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("👤 Usernames",callback_data="bot_usernames")
    )

    kb.add(
        InlineKeyboardButton("🔑 API Tokens",callback_data="bot_api")
    )

    bot.send_message(
        message.chat.id,
        "🤖 Bots Panel",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call:call.data=="bot_usernames")
def bot_usernames(call):

    bots=bots_collection.find()

    text="🤖 Bots Usernames\n\n"

    i=1

    for b in bots:

        text+=f"{i}: {b.get('username')}\n"

        i+=1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


@bot.callback_query_handler(func=lambda call:call.data=="bot_api")
def bot_api(call):

    bots=bots_collection.find()

    text="🔑 Bots API\n\n"

    i=1

    for b in bots:

        text+=f"{i}: {b.get('token')}\n\n"

        i+=1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ---------- CLOSE BOTS ----------

@bot.message_handler(func=lambda m:m.text=="🚫 Close Bots")
def close_bots(message):

    system_collection.update_one(
        {"system":"bots"},
        {"$set":{"active":False}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🚫 All bots stopped"
    )


# ---------- OPEN BOTS ----------

@bot.message_handler(func=lambda m:m.text=="✅ Open Bots")
def open_bots(message):

    system_collection.update_one(
        {"system":"bots"},
        {"$set":{"active":True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "✅ Bots activated"
    )


# ---------- ADD CHANNEL ----------

@bot.message_handler(func=lambda m:m.text=="➕ Add Channel")
def add_channel(message):

    bot.send_message(
        message.chat.id,
        "Send channel username\nExample:\n@channel"
    )

    bot.register_next_step_handler(message,save_channel)


def save_channel(message):

    channel = message.text.strip()

    try:

        member = bot.get_chat_member(channel, bot.get_me().id)

        if member.status not in ["administrator","creator"]:

            bot.send_message(
                message.chat.id,
                "❌ Bot is not admin in this channel"
            )
            return

    except:

        bot.send_message(
            message.chat.id,
            "❌ Cannot access channel\nMake sure bot is admin"
        )
        return


    channels_collection.update_one(
        {"username":channel},
        {"$set":{"username":channel,"active":True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        f"✅ Channel Added\n{channel}"
    )


# ---------- CHANNEL LIST ----------

@bot.message_handler(func=lambda m:m.text=="📡 Channels")
def channels(message):

    channels=channels_collection.find({"active":True})

    text="📡 Force Join Channels\n\n"

    found=False

    for c in channels:

        text+=c["username"]+"\n"

        found=True

    if not found:

        text="No active channels"

    bot.send_message(message.chat.id,text)


# ---------- CLOSE CHANNELS ----------

@bot.message_handler(func=lambda m:m.text=="❌ Close Channels")
def close_channels(message):

    channels_collection.update_many(
        {},
        {"$set":{"active":False}}
    )

    bot.send_message(
        message.chat.id,
        "❌ All force join channels disabled"
    )


# ---------- BROADCAST ----------

broadcast_mode=False

@bot.message_handler(func=lambda m:m.text=="📢 Broadcast")
def broadcast(message):

    global broadcast_mode

    if message.from_user.id!=ADMIN_ID:
        return

    broadcast_mode=True

    bot.send_message(
        message.chat.id,
        "Send broadcast message"
    )


@bot.message_handler(func=lambda m:True)
def send_bc(message):

    global broadcast_mode

    if not broadcast_mode:
        return

    users=users_collection.find()

    sent=0

    for u in users:

        try:

            bot.send_message(
                u["user_id"],
                message.text
            )

            sent+=1

        except:
            pass

    broadcast_mode=False

    bot.send_message(
        message.chat.id,
        f"📢 Broadcast delivered to {sent} users",
        reply_markup=admin_menu()
    )


print("Admin Bot Running...")

bot.infinity_polling(skip_pending=True)
