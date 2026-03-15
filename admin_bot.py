import telebot
import os
import json

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

broadcast_mode = False

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

@bot.message_handler(commands=["start"])
def admin_panel(message):

    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id,"❌ Not allowed")
        return

    text = """
⚙️ ADMIN PANEL

Commands:

/stats
/bots
/broadcast
"""

    bot.send_message(message.chat.id,text)

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    bots = load_bots()
    users = load_users()

    text = f"""
📊 STATS

🤖 Total Bots: {len(bots)}
👤 Total Users: {len(users)}
"""

    bot.send_message(message.chat.id,text)

@bot.message_handler(commands=["bots"])
def bots_list(message):

    if message.from_user.id != ADMIN_ID:
        return

    bots = load_bots()

    text="🤖 Bots List\n\n"

    for b in bots:
        text+=b["token"]+"\n\n"

    if len(bots)==0:
        text="No bots added"

    bot.send_message(message.chat.id,text)

@bot.message_handler(commands=["broadcast"])
def broadcast(message):

    global broadcast_mode

    if message.from_user.id != ADMIN_ID:
        return

    broadcast_mode = True

    bot.send_message(
        message.chat.id,
        "Send message to broadcast to all users"
    )

@bot.message_handler(func=lambda m: True)
def send_broadcast(message):

    global broadcast_mode

    if message.from_user.id != ADMIN_ID:
        return

    if broadcast_mode:

        users = load_users()

        for u in users:

            try:
                bot.send_message(u,message.text)
            except:
                pass

        bot.send_message(
            message.chat.id,
            "✅ Broadcast Sent"
        )

        broadcast_mode=False

bot.infinity_polling()
