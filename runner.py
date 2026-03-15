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

    if token in running_bots:
        return

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start(message):

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "✅ VERIFY",
                url="https://t.me/Verifyd_bot"
            )
        )

        bot.send_message(
            message.chat.id,
            "❌ You Can't Use this Bot before verify",
            reply_markup=kb
        )

    print("Bot started:", token)

    running_bots[token] = bot

    bot.infinity_polling()

def run_bot_thread(token):

    t = threading.Thread(
        target=start_bot,
        args=(token,)
    )

    t.start()

def start_all_bots():

    bots = load_bots()

    for b in bots:

        token = b["token"]

        if token not in running_bots:
            run_bot_thread(token)

while True:

    start_all_bots()

    time.sleep(20)
