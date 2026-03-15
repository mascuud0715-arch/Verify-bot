import telebot
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from pymongo import MongoClient

# ================= ENV =================

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

client = MongoClient(MONGO_URL)
db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]

# ================= MENU =================

def main_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("➕ Add Bot")
    )

    kb.add(
        KeyboardButton("🤖 My Bots")
    )

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

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

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

# ================= ADD BOT =================

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
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
            f"✅ Bot Added Successfully\n\nBot: @{info.username}"
        )

    except:

        bot.send_message(
            message.chat.id,
            "❌ Invalid bot token"
        )

# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    bots = bots_collection.find({"owner": message.from_user.id})

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        text += f"@{b['username']}\n"
        found = True

    if not found:

        text = "❌ You have no bots yet"

    bot.send_message(
        message.chat.id,
        text
    )

# ================= RUN =================

print("🚀 Verify Main Bot Running...")

bot.infinity_polling(skip_pending=True)
