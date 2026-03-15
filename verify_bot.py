import telebot
import os
import json
import random

TOKEN = os.getenv("VERIFY_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

def load_codes():
    try:
        with open("codes.json","r") as f:
            return json.load(f)
    except:
        return {}

def save_codes(data):
    with open("codes.json","w") as f:
        json.dump(data,f)

@bot.message_handler(commands=["start"])
def start(message):

    user_id = str(message.from_user.id)

    code = random.randint(100000,999999)

    data = load_codes()
    data[user_id] = code
    save_codes(data)

    bot.send_message(
        message.chat.id,
        f"✅ Your verify code:\n\n`{code}`\n\nSend this code to the bot you want to use.",
        parse_mode="Markdown"
    )

bot.infinity_polling()
