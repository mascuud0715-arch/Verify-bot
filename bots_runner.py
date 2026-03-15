import telebot
import json
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

VERIFY_BOT = "@Verifyd_bot"

with open("bots.json") as f:
    bots = json.load(f)

def run_bot(token):

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start(msg):

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "✅ Verify",
                url=f"https://t.me/{VERIFY_BOT}?start={msg.from_user.id}"
            )
        )

        bot.send_message(
            msg.chat.id,
            "Welcome!\n\nFadlan Verify samee si aad u sii wadato.",
            reply_markup=kb
        )

    bot.infinity_polling()

for bot_id, data in bots.items():

    token = data["token"]

    t = threading.Thread(target=run_bot, args=(token,))
    t.start()
