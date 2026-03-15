import telebot
import os
import random
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("VERIFY_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)


def load_codes():
    try:
        with open("codes.json") as f:
            return json.load(f)
    except:
        return {}


def save_codes(data):
    with open("codes.json", "w") as f:
        json.dump(data, f)


@bot.message_handler(commands=["start"])
def start(message):

    parts = message.text.split()

    # haddii user si toos ah u yimid
    if len(parts) == 1:

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "Open Verify System",
                url="https://t.me/Verify_yourbot"
            )
        )

        bot.send_message(
            message.chat.id,
            """
❌ You are not registered in the verify system.

Please register your bot first.
""",
            reply_markup=kb
        )
        return

    # user ka yimid bot system
    user_id = parts[1]

    code = random.randint(100000, 999999)

    data = load_codes()

    data[str(user_id)] = code

    save_codes(data)

    bot.send_message(
        message.chat.id,
        f"""
🔐 VERIFY SYSTEM

Your verification code:

{code}

Send this code to the bot you want to use.
"""
    )


print("Verify Bot Running...")
bot.infinity_polling()
