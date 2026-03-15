import telebot
import os
import json
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("VERIFY_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

codes = {}

def load_users():
    try:
        with open("users.json") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open("users.json","w") as f:
        json.dump(users,f)

@bot.message_handler(commands=['start'])
def start(msg):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "✅ Verify",
            callback_data="verify"
        )
    )

    bot.send_message(
        msg.chat.id,
        "Riix Verify si aad u verify garayso.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c:True)
def verify(call):

    if call.data=="verify":

        code=random.randint(1000,9999)

        codes[call.from_user.id]=code

        bot.send_message(
            call.message.chat.id,
            f"Dir code-kan:\n\n{code}"
        )

@bot.message_handler(func=lambda m:True)
def check(msg):

    if msg.from_user.id in codes:

        if msg.text==str(codes[msg.from_user.id]):

            users=load_users()

            if msg.from_user.id not in users:
                users.append(msg.from_user.id)
                save_users(users)

            bot.send_message(
                msg.chat.id,
                "✅ Verification waa guulaystay"
            )

            del codes[msg.from_user.id]

        else:

            bot.send_message(
                msg.chat.id,
                "❌ Code khaldan"
            )

bot.infinity_polling()
