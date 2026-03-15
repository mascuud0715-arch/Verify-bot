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


def save_codes(data):
    with open("codes.json","w") as f:
        json.dump(data,f)


def load_users():
    try:
        with open("users.json") as f:
            return json.load(f)
    except:
        return []


def save_users(data):
    with open("users.json","w") as f:
        json.dump(data,f)


def load_channels():
    try:
        with open("channels.json") as f:
            return json.load(f)
    except:
        return []


def check_join(bot,user_id):

    channels = load_channels()

    if len(channels) == 0:
        return True

    for ch in channels:

        try:

            member = bot.get_chat_member(ch,user_id)

            if member.status == "left":
                return False

        except:
            return False

    return True


def start_bot(token):

    bot = telebot.TeleBot(token)

    verified_users = set()

    @bot.message_handler(commands=['start'])
    def start(message):

        user_id = message.from_user.id
        user_str = str(user_id)

        users = load_users()

        if user_id not in users:
            users.append(user_id)
            save_users(users)

        if user_id in verified_users:

            if not check_join(bot,user_id):

                channels = load_channels()

                kb = InlineKeyboardMarkup()

                for ch in channels:
                    kb.add(
                        InlineKeyboardButton(
                            "Join Channel",
                            url=f"https://t.me/{ch.replace('@','')}"
                        )
                    )

                bot.send_message(
                    message.chat.id,
                    "❌ You must join all channels",
                    reply_markup=kb
                )

                return

            bot.send_message(
                message.chat.id,
                "✅ Bot Ready\nYou can now use the bot."
            )

            return


        kb = InlineKeyboardMarkup()

        kb.add(
            InlineKeyboardButton(
                "VERIFY",
                url=f"https://t.me/Verify_owner_bot?start={user_str}"
            )
        )

        bot.send_message(
            message.chat.id,
            "You Can't Use this Bot before verify",
            reply_markup=kb
        )


    @bot.message_handler(func=lambda m: True)
    def verify_code(message):

        user_id = message.from_user.id
        user_str = str(user_id)

        code = message.text.strip()

        codes = load_codes()

        if user_str in codes and str(codes[user_str]) == code:

            verified_users.add(user_id)

            del codes[user_str]
            save_codes(codes)

            if not check_join(bot,user_id):

                channels = load_channels()

                kb = InlineKeyboardMarkup()

                for ch in channels:

                    kb.add(
                        InlineKeyboardButton(
                            "Join Channel",
                            url=f"https://t.me/{ch.replace('@','')}"
                        )
                    )

                bot.send_message(
                    message.chat.id,
                    "❌ You must join all channels",
                    reply_markup=kb
                )

                return

            bot.send_message(
                message.chat.id,
                "✅ Verification Successful!\nYou can now use this bot."
            )

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
