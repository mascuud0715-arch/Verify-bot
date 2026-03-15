import telebot
import os
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

broadcast_mode = False
button_mode = False
broadcast_text = ""


def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []


def load_users():
    try:
        with open("users.json") as f:
            return json.load(f)
    except:
        return []


def load_channels():
    try:
        with open("channels.json") as f:
            return json.load(f)
    except:
        return []


def save_channels(data):
    with open("channels.json","w") as f:
        json.dump(data,f)


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

    return kb


@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id,"❌ Not allowed")
        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )


# STATS
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):

    bots = load_bots()
    users = load_users()

    bot.send_message(
        message.chat.id,
        f"""
📊 SYSTEM STATS

🤖 Bots: {len(bots)}
👤 Users: {len(users)}
"""
    )


# BOTS LIST
@bot.message_handler(func=lambda m: m.text == "🤖 Bots")
def bots_list(message):

    bots = load_bots()

    text="🤖 Bots List\n\n"

    for b in bots:
        text+=b["token"]+"\n\n"

    if len(bots)==0:
        text="No bots added"

    bot.send_message(message.chat.id,text)


# BROADCAST
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast(message):

    global broadcast_mode

    broadcast_mode = True

    bot.send_message(
        message.chat.id,
        "Send broadcast message"
    )


# ADD CHANNEL
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(message):

    bot.send_message(
        message.chat.id,
        "Send channel username\nExample:\n@mychannel"
    )

    bot.register_next_step_handler(message,save_channel)


def save_channel(message):

    channel = message.text.strip()

    channels = load_channels()

    channels.append(channel)

    save_channels(channels)

    bot.send_message(
        message.chat.id,
        f"✅ Channel Added\n{channel}"
    )


# LIST CHANNELS
@bot.message_handler(func=lambda m: m.text == "📡 Channels")
def channels_list(message):

    channels = load_channels()

    text="📡 Force Join Channels\n\n"

    for c in channels:
        text+=c+"\n"

    if len(channels)==0:
        text="No channels added"

    bot.send_message(message.chat.id,text)


# SEND BROADCAST
@bot.message_handler(func=lambda m: True)
def send_broadcast(message):

    global broadcast_mode

    if message.from_user.id != ADMIN_ID:
        return

    if broadcast_mode:

        users = load_users()

        sent = 0

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "🌐 Visit",
                url="https://example.com"
            )
        )

        for u in users:

            try:
                bot.send_message(
                    u,
                    message.text,
                    reply_markup=kb
                )
                sent+=1
            except:
                pass

        bot.send_message(
            message.chat.id,
            f"✅ Broadcast sent to {sent} users"
        )

        broadcast_mode = False


print("Admin Bot Running...")
bot.infinity_polling()
