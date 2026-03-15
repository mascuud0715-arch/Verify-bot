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

def load_codes():
    try:
        with open("codes.json") as f:
            return json.load(f)
    except:
        return {}

def start_bot(token):

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start(message):

        user_id = str(message.from_user.id)

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "VERIFY",
                url=f"https://t.me/Verify_owner_bot?start={user_id}"
            )
        )

        bot.send_message(
            message.chat.id,
            "You Can't Use this Bot before verify",
            reply_markup=kb
        )

    @bot.message_handler(func=lambda m: True)
    def verify_code(message):

        user_id = str(message.from_user.id)
        code = message.text.strip()

        codes = load_codes()

        if user_id in codes and str(codes[user_id]) == code:

            bot.send_message(
                message.chat.id,
                "✅ Verification Successful!\nYou can now use this bot."
            )

            del codes[user_id]

            with open("codes.json","w") as f:
                json.dump(codes,f)

        else:

            bot.send_message(
                message.chat.id,
                "❌ Invalid code.\nPlease verify first."
            )

    print("Bot started:", token)

    bot.infinity_polling()

def run_bot(token):

    if token in running_bots:
        return

    t = threading.Thread(target=start_bot,args=(token,))
    t.start()

    running_bots[token] = True


while True:

    bots = load_bots()

    for b in bots:

        token = b["token"]

        run_bot(token)

    time.sleep(10)
