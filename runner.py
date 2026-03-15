import telebot
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def load_codes():
    try:
        with open("codes.json") as f:
            return json.load(f)
    except:
        return {}

def start_bot(token):

    bot = telebot.TeleBot(token)

    verified_users = set()

    @bot.message_handler(commands=["start"])
    def start(message):

        if message.from_user.id not in verified_users:

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "VERIFY",
                    url="https://t.me/Verifyd_bot"
                )
            )

            bot.send_message(
                message.chat.id,
                "❌ You Can't Use this Bot before verify",
                reply_markup=kb
            )

        else:
            bot.send_message(
                message.chat.id,
                "✅ Welcome! You are verified."
            )

    @bot.message_handler(func=lambda m: True)
    def verify_code(message):

        codes = load_codes()

        user_id = str(message.from_user.id)

        if user_id in codes:

            if message.text == str(codes[user_id]):

                verified_users.add(message.from_user.id)

                bot.send_message(
                    message.chat.id,
                    "✅ Verified Successfully!"
                )

    bot.infinity_polling()
