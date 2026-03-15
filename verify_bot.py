import telebot
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ---------------- CONFIG ----------------

TOKEN = os.getenv("VERIFY_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# ---------------- DATABASE ----------------

client = MongoClient(MONGO_URL)

db = client["verify_system"]

users_collection = db["users"]
channels_collection = db["channels"]
codes_collection = db["codes"]

# ---------------- SAVE USER ----------------

def save_user(user_id):

    if users_collection.find_one({"user_id": user_id}):

        return

    users_collection.insert_one(
        {
            "user_id": user_id
        }
    )


# ---------------- GET CHANNELS ----------------

def get_channels():

    channels = channels_collection.find({"active": True})

    result = []

    for c in channels:

        result.append(c["username"])

    return result


# ---------------- CHECK JOIN ----------------

def check_join(user_id):

    channels = get_channels()

    not_joined = []

    for ch in channels:

        try:

            member = bot.get_chat_member(ch, user_id)

            if member.status in ["left", "kicked"]:

                not_joined.append(ch)

        except:

            not_joined.append(ch)

    return not_joined


# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id

    save_user(user_id)

    not_joined = check_join(user_id)

    if not_joined:

        kb = InlineKeyboardMarkup()

        for ch in not_joined:

            kb.add(
                InlineKeyboardButton(
                    f"Join {ch}",
                    url=f"https://t.me/{ch.replace('@','')}"
                )
            )

        kb.add(
            InlineKeyboardButton(
                "✅ Verify Join",
                callback_data="verify_join"
            )
        )

        bot.send_message(

            message.chat.id,

            "⚠️ Please join all channels to continue",

            reply_markup=kb

        )

        return

    send_verify_panel(message.chat.id)


# ---------------- VERIFY PANEL ----------------

def send_verify_panel(chat_id):

    kb = InlineKeyboardMarkup()

    kb.add(

        InlineKeyboardButton(
            "🔐 Verify",
            callback_data="verify"
        )

    )

    bot.send_message(

        chat_id,

        "Press verify to continue",

        reply_markup=kb

    )


# ---------------- VERIFY JOIN BUTTON ----------------

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join(call):

    user_id = call.from_user.id

    not_joined = check_join(user_id)

    if not_joined:

        bot.answer_callback_query(

            call.id,

            "❌ You must join channels",

            show_alert=True

        )

        return

    bot.edit_message_text(

        "✅ Join verified",

        call.message.chat.id,

        call.message.message_id

    )

    send_verify_panel(call.message.chat.id)


# ---------------- VERIFY BUTTON ----------------

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):

    user_id = call.from_user.id

    code = str(user_id)

    codes_collection.insert_one(

        {
            "user_id": user_id,
            "code": code
        }

    )

    bot.send_message(

        call.message.chat.id,

        f"""
✅ Verification Complete

Your Code:

`{code}`

Send this code to website.
""",

        parse_mode="Markdown"

    )


print("Verify Bot Running...")

bot.infinity_polling(skip_pending=True)
