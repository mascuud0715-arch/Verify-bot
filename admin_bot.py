import telebot
import os
import json
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

broadcast_mode=False
button_mode=False
broadcast_text=""
button_text=""
button_link=""


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

    kb=ReplyKeyboardMarkup(resize_keyboard=True)

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

    if message.from_user.id!=ADMIN_ID:
        bot.send_message(message.chat.id,"❌ Not allowed")
        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )


# ================= STATS =================

@bot.message_handler(func=lambda m:m.text=="📊 Stats")
def stats(message):

    bots=load_bots()
    users=load_users()

    bot.send_message(
        message.chat.id,
        f"""
📊 SYSTEM STATS

🤖 Bots: {len(bots)}
👤 Users: {len(users)}
"""
    )


# ================= BOTS =================

@bot.message_handler(func=lambda m:m.text=="🤖 Bots")
def bots_panel(message):

    kb=InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("👤 Usernames",callback_data="bot_usernames")
    )

    kb.add(
        InlineKeyboardButton("🔑 See API",callback_data="bot_api")
    )

    bot.send_message(
        message.chat.id,
        "🤖 Bots Panel",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call:call.data=="bot_usernames")
def show_usernames(call):

    bots=load_bots()

    text="🤖 Bots Usernames\n\n"

    i=1

    for b in bots:
        text+=f"{i}: {b.get('username','Unknown')}\n"
        i+=1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


@bot.callback_query_handler(func=lambda call:call.data=="bot_api")
def show_api(call):

    bots=load_bots()

    text="🔑 Bots API Tokens\n\n"

    i=1

    for b in bots:
        text+=f"{i}: {b['token']}\n\n"
        i+=1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ================= BROADCAST =================

@bot.message_handler(func=lambda m:m.text=="📢 Broadcast")
def broadcast(message):

    global broadcast_mode

    broadcast_mode=True

    bot.send_message(
        message.chat.id,
        "Send broadcast message"
    )


@bot.message_handler(func=lambda m:True)
def broadcast_steps(message):

    global broadcast_mode,button_mode,broadcast_text,button_text,button_link

    if message.from_user.id!=ADMIN_ID:
        return


    # Step 1 receive message
    if broadcast_mode:

        broadcast_text=message.text
        broadcast_mode=False
        button_mode=True

        kb=ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("Add Button","No Button")

        bot.send_message(
            message.chat.id,
            "Do you want to add button?",
            reply_markup=kb
        )

        return


    # Step 2 choose button
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

    bot.send_message(
        message.chat.id,
        "✅ Broadcast Sent",
        reply_markup=admin_menu()
    )


def send_broadcast(chat_id,kb):

    users=load_users()

    sent=0

    for u in users:

        try:

            if kb:
                bot.send_message(u,broadcast_text,reply_markup=kb)
            else:
                bot.send_message(u,broadcast_text)

            sent+=1

        except:
            pass

    bot.send_message(
        chat_id,
        f"📢 Broadcast delivered to {sent} users"
    )


# ================= ADD CHANNEL =================

@bot.message_handler(func=lambda m:m.text=="➕ Add Channel")
def add_channel(message):

    bot.send_message(
        message.chat.id,
        "Send channel username\nExample:\n@channel"
    )

    bot.register_next_step_handler(message,save_channel)


def save_channel(message):

    channel=message.text.strip()

    channels=load_channels()

    channels.append(channel)

    save_channels(channels)

    bot.send_message(
        message.chat.id,
        f"✅ Channel Added\n{channel}"
    )


# ================= CHANNELS =================

@bot.message_handler(func=lambda m:m.text=="📡 Channels")
def channels_list(message):

    channels=load_channels()

    text="📡 Force Join Channels\n\n"

    for c in channels:
        text+=c+"\n"

    if len(channels)==0:
        text="No channels added"

    bot.send_message(message.chat.id,text)


print("Admin Bot Running...")
bot.infinity_polling()
