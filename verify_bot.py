import telebot
import os
import random
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ================= CONFIG =================

TOKEN = os.getenv("VERIFY_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN, threaded=True)

# ================= DATABASE =================

client = MongoClient(MONGO_URL, maxPoolSize=200)
db = client["verify_system"]

users_collection = db["users"]
channels_collection = db["channels"]
codes_collection = db["codes"]

# indexes
users_collection.create_index("user_id")
channels_collection.create_index("username")

# ================= SAVE USER =================

def save_user(user_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# ================= ALLOWED USER =================

def allowed_user(user_id):
    # USER waa inuu kasoo muuqdaa system-ka (runner bots)
    user = users_collection.find_one({"user_id": user_id})
    return True if user else False

# ================= GET CHANNELS =================

def get_channels():

    result = []

    for c in channels_collection.find({"active": True}):
        username = c.get("username")
        if username:
            result.append(username)

    return result

# ================= CHECK JOIN =================

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

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id

    # ONLY downloader users allowed
    if not allowed_user(user_id):

        bot.send_message(
            message.chat.id,
            "⛔ You must use downloader bot first."
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
            "⚠️ Join all channels to continue",
            reply_markup=kb
        )
        return

    send_verify_panel(message.chat.id)

# ================= VERIFY PANEL =================

def send_verify_panel(chat_id):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "🔐 Generate Code",
            callback_data="generate_code"
        )
    )

    bot.send_message(
        chat_id,
        "Press button to generate verification code",
        reply_markup=kb
    )

# ================= VERIFY JOIN =================

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

    bot.answer_callback_query(call.id, "✅ Verified")

    try:
        bot.edit_message_text(
            "✅ Join verified",
            call.message.chat.id,
            call.message.message_id
        )
    except:
        pass

    send_verify_panel(call.message.chat.id)

# ================= GENERATE CODE =================

@bot.callback_query_handler(func=lambda call: call.data == "generate_code")
def generate_code(call):

    user_id = call.from_user.id

    # 6 digit code
    code = str(random.randint(100000, 999999))
    expire_time = int(time.time()) + 300

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
""",
        parse_mode="Markdown"
    )

    # auto delete
    threading.Thread(
        target=delete_code_message,
        args=(msg.chat.id, msg.message_id),
        daemon=True
    ).start()

# ================= DELETE CODE MSG =================

def delete_code_message(chat_id, msg_id):

    time.sleep(30)

    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

# ================= RUN =================

def run():
    while True:
        try:
            print("🔐 Verify Bot Running...")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Verify crash:", e)
            time.sleep(5)

# ================= MAIN =================

if __name__ == "__main__":
    run()
