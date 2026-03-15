import telebot
import json
import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

running_bots = {}


def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []


def start_bot(token):

    try:
        bot = telebot.TeleBot(token)

        @bot.message_handler(commands=['start'])
        def start(message):

            user_id = message.from_user.id

            verify_link = f"https://t.me/Verify_owner_bot?start={user_id}"

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "✅ VERIFY",
                    url=verify_link
                )
            )

            bot.send_message(
                message.chat.id,
                "❌ You Can't Use this Bot before verify.",
                reply_markup=kb
            )

        print("Bot started:", token)

        bot.infinity_polling()

    except Exception as e:
        print("Bot failed:", token, e)


def run_bot(token):

    if token in running_bots:
        return

    t = threading.Thread(target=start_bot, args=(token,))
    t.daemon = True
    t.start()

    running_bots[token] = True


while True:

    bots = load_bots()

    for b in bots:

        token = b["token"]

        run_bot(token)

    time.sleep(10)
