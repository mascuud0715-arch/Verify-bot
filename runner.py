import telebot
import json
import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

VERIFY_BOT="Verifyd_bot"

def run_bot(token):

    bot=telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start(msg):

        kb=InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "✅ Verify",
                url=f"https://t.me/{VERIFY_BOT}"
            )
        )

        bot.send_message(
            msg.chat.id,
            "Welcome!\n\nFadlan Verify samee.",
            reply_markup=kb
        )

    bot.infinity_polling()

def load():

    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return {}

while True:

    bots=load()

    for b in bots.values():

        token=b["token"]

        t=threading.Thread(
            target=run_bot,
            args=(token,)
        )

        t.start()

    time.sleep(999999)
