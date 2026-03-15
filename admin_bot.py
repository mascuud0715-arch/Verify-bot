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

# ---------- STATES ----------

broadcast_mode=False
button_mode=False
broadcast_text=""
button_text=""
button_link=""

# ---------- MENU ----------

def admin_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("📊 Stats"),
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
def broadcast_steps(message):

    global broadcast_mode,button_mode,broadcast_text

    if message.from_user.id!=ADMIN_ID:
        return

    if broadcast_mode:

        broadcast_text=message.text
        broadcast_mode=False
        button_mode=True

        kb=ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("Add Button","No Button")

        bot.send_message(
            message.chat.id,
            "Add button?",
            reply_markup=kb
        )

        return


    if button_mode and message.text=="Add Button":

        bot.send_message(
            message.chat.id,
            "Send button text"
        )

        bot.register_next_step_handler(message,get_button_text)
        return


    if button_mode and message.text=="No Button":

        send_broadcast(message.chat.id,None)

        button_mode=False

        bot.send_message(
            message.chat.id,
            "✅ Broadcast Sent",
            reply_markup=admin_menu()
        )


def get_button_text(message):

    global button_text

    button_text=message.text

    bot.send_message(
        message.chat.id,
        "Send button link"
    )

    bot.register_next_step_handler(message,get_button_link)


def get_button_link(message):

    global button_link

    button_link=message.text

    kb=InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(button_text,url=button_link)
    )

    send_broadcast(message.chat.id,kb)


def send_broadcast(chat_id,kb):

    users=users_collection.find()
    bots=bots_collection.find()

    sent=0

    for b in bots:

        try:

            send_bot=telebot.TeleBot(b["token"])

            for u in users:

                try:

                    if kb:
                        send_bot.send_message(u["user_id"],broadcast_text,reply_markup=kb)
                    else:
                        send_bot.send_message(u["user_id"],broadcast_text)

                    sent+=1

                except:
                    pass

        except:
            pass


    bot.send_message(
        chat_id,
        f"📢 Broadcast delivered to {sent} users"
    )


print("Admin Bot Running...")
bot.infinity_polling(skip_pending=True)
