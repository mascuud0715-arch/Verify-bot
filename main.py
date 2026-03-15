import telebot
import os
import requests
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# -------- ENV --------

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# -------- DATABASE --------

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]

# -------- STATE --------

user_state = {}

# -------- SAVE USER --------

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# -------- GET BOT USERNAME --------

def get_bot_username(token):

    try:

        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe"
        ).json()

        if r["ok"]:
            return "@" + r["result"]["username"]

    except:
        pass

    return None

# -------- GET CHANNELS --------

def get_channels():

    channels = channels_collection.find({"active": True})

    result = []

    for c in channels:
        result.append(c["username"])

    return result

# -------- CHECK JOIN --------

def check_join(user_id):

    channels = get_channels()

    for ch in channels:

        try:

            member = bot.get_chat_member(ch, user_id)

            if member.status in ["left","kicked"]:
                return False

        except:
            return False

    return True

# -------- START --------

@bot.message_handler(commands=["start"])
def start(message):

    uid = message.from_user.id

    save_user(uid)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("➕ Add Bot")
    kb.add("🤖 My Bots")

    bot.send_message(
        message.chat.id,
        "🤖 Welcome To Video Downloader System\n\nChoose option:",
        reply_markup=kb
    )

# -------- ADD BOT --------

@bot.message_handler(func=lambda m: m.text == "➕ Add Bot")
def add_bot(message):

    user_state[message.from_user.id] = "token"

    bot.send_message(
        message.chat.id,
        "📩 Send your Bot Token"
    )

# -------- MY BOTS --------

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    uid = message.from_user.id

    bots = bots_collection.find({"owner": uid})

    text = "🤖 Your Bots\n\n"

    found = False

    for b in bots:

        text += f"{b['username']}\n"
        found = True

    if not found:
        text = "❌ You don't have bots added."

    bot.send_message(message.chat.id,text)

# -------- RECEIVE TOKEN --------

@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def receive_token(message):

    uid = message.from_user.id

    token = message.text.strip()

    username = get_bot_username(token)

    if not username:

        bot.send_message(
            message.chat.id,
            "❌ Invalid Bot Token"
        )
        return

    if bots_collection.find_one({"token": token}):

        bot.send_message(
            message.chat.id,
            "⚠️ Bot already added"
        )
        return

    bots_collection.insert_one({

        "owner": uid,
        "token": token,
        "username": username

    })

    del user_state[uid]

    bot.send_message(
        message.chat.id,
        f"✅ Bot Added Successfully\n\n{username}\n\nBot will start automatically."
    )

# -------- FORCE JOIN --------

def force_join(chat_id,user_id):

    if check_join(user_id):
        return True

    channels = get_channels()

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "JOIN",
            url=f"https://t.me/{channels[0].replace('@','')}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "CONFIRM",
            callback_data="confirm_join"
        )
    )

    bot.send_message(
        chat_id,
        "⚠️ Please join all channels to continue",
        reply_markup=kb
    )

    return False

# -------- CONFIRM JOIN --------

@bot.callback_query_handler(func=lambda call: call.data=="confirm_join")
def confirm_join(call):

    uid = call.from_user.id

    if not check_join(uid):

        bot.answer_callback_query(
            call.id,
            "❌ Join channel first",
            show_alert=True
        )
        return

    bot.edit_message_text(
        "✅ Verified\n\nSend TikTok link",
        call.message.chat.id,
        call.message.message_id
    )

# -------- TIKTOK DOWNLOAD --------

def download_tiktok(url):

    try:

        api = f"https://tikwm.com/api/?url={url}"

        r = requests.get(api).json()

        if r["code"] != 0:
            return None

        data = r["data"]

        # VIDEO
        if data.get("play"):

            return {
                "type": "video",
                "media": data["play"]
            }

        # PHOTO SLIDES
        if data.get("images"):

            return {
                "type": "photo",
                "media": data["images"]
            }

    except:
        pass

    return None

# -------- HANDLE LINKS --------
@bot.message_handler(func=lambda m: "tiktok.com" in m.text)
def handle_tiktok(message):

    uid = message.from_user.id
    url = message.text

    bot.send_message(
        message.chat.id,
        "⏳ Downloading..."
    )

    result = download_tiktok(url)

    if not result:

        bot.send_message(
            message.chat.id,
            "❌ Download failed"
        )

        return


    bot_username = bot.get_me().username


    # VIDEO
    if result["type"] == "video":

        bot.send_video(
            message.chat.id,
            result["media"],
            caption=f"Via @{bot_username}"
        )

        downloads_collection.insert_one({
            "type":"tiktok_video"
        })


    # PHOTOS
    elif result["type"] == "photo":

        for img in result["media"]:

            bot.send_photo(
                message.chat.id,
                img,
                caption=f"Via @{bot_username}"
            )

        downloads_collection.insert_one({
            "type":"photo"
        })


    bot.send_message(
        message.chat.id,
        "Created: @Verify_yourbot"
        )


# -------- RUN --------

print("Main Bot Running...")

bot.infinity_polling(skip_pending=True)
