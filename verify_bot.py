import telebot
import os
import random
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ---------------- CONFIG ----------------

TOKEN = os.getenv("VERIFY_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN, threaded=True)

# ---------------- DATABASE ----------------

client = MongoClient(MONGO_URL, maxPoolSize=200)

db = client["verify_system"]

users_collection = db["users"]
channels_collection = db["channels"]
codes_collection = db["codes"]

# ---------------- SAVE USER ----------------

def save_user(user_id):

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# ---------------- CHECK USER FROM MAIN BOTS ----------------

def allowed_user(user_id):

    user = users_collection.find_one({"user_id": user_id})

    if user:
        return True

    return False

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

    # ALLOW ONLY MAIN BOT USERS
    if not allowed_user(user_id):

        bot.send_message(
            message.chat.id,
            "⛔ You must come from downloader bot first."
        )
        return

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
            "🔐 Generate Code",
            callback_data="verify"
        )
    )

    bot.send_message(
        chat_id,
        "Press button to generate verification code",
        reply_markup=kb
    )

# ---------------- VERIFY JOIN ----------------

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join(call):

    user_id = call.from_user.id

    not_joined = check_join(user_id)

    if not_joined:

        bot.answer_callback_query(
            call.id,
            "❌ Join all channels first",
            show_alert=True
        )

        return

    bot.edit_message_text(
        "✅ Join verified",
        call.message.chat.id,
        call.message.message_id
    )

    send_verify_panel(call.message.chat.id)

# ---------------- GENERATE CODE ----------------

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):

    user_id = call.from_user.id

    # 6 DIGIT CODE
    code = str(random.randint(100000, 999999))

    expire_time = int(time.time()) + 300

    # SAVE CODE
    codes_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "code": code,
                "expire": expire_time
            }
        },
        upsert=True
    )

    msg = bot.send_message(

        call.message.chat.id,

f"""
✅ Verification Code

`{code}`

⏱ Expires in 5 minutes

Tap code to copy.
""",

        parse_mode="Markdown"
    )

    # AUTO DELETE AFTER 30 SEC
    threading.Thread(
        target=delete_code_message,
        args=(msg.chat.id, msg.message_id),
        daemon=True
    ).start()

# ---------------- AUTO DELETE ----------------

def delete_code_message(chat_id, msg_id):

    time.sleep(30)

    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

print("Verify Bot Running...")

bot.infinity_polling(skip_pending=True)
