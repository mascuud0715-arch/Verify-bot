import telebot
import os
import time
import threading
import requests
import tempfile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# -------- ENV --------

MONGO_URL = os.getenv("MONGO_URL")
VERIFY_API = os.getenv("VERIFY_API")

# -------- MONGODB --------

client = MongoClient(MONGO_URL)
db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]
system_collection = db["system"]
channels_collection = db["channels"]

# -------- RUNNING BOTS --------

running_bots = {}

# -------- PENDING LINKS --------

pending_links = {}

# -------- SAVE USER --------

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# -------- CHECK SYSTEM --------

def bots_active():

    s = system_collection.find_one({"system": "bots"})

    if not s:
        return True

    return s.get("active", True)

# -------- VERIFY JOIN --------

def verify_join(user_id):

    try:

        r = requests.get(
            VERIFY_API,
            params={"user_id": user_id},
            timeout=10
        )

        data = r.json()

        if "status" not in data:
            return {"status": "joined"}

        return data

    except Exception as e:

        print("VERIFY API ERROR:", e)

        return {"status": "joined"}

# -------- FORCE JOIN --------

def send_force_join(bot, chat_id):

    channels = list(channels_collection.find({"active": True}))

    if len(channels) == 0:
        return False

    kb = InlineKeyboardMarkup()

    for ch in channels:

        link = f"https://t.me/{ch['username'].replace('@','')}"

        kb.add(
            InlineKeyboardButton(
                "📢 Join Channel",
                url=link
            )
        )

    kb.add(
        InlineKeyboardButton(
            "✅ Confirm",
            callback_data="confirm_join"
        )
    )

    bot.send_message(
        chat_id,
        "⚠️ Please join all channels to continue",
        reply_markup=kb
    )

    return True

# -------- DOWNLOAD TIKTOK --------

def download_tiktok(url):

    try:

        api = f"https://tikwm.com/api/?url={url}"

        r = requests.get(api).json()

        if r["code"] != 0:
            return None

        data = r["data"]

        if data.get("play"):

            return {
                "type": "video",
                "media": data["play"]
            }

        if data.get("images"):

            return {
                "type": "photo",
                "media": data["images"]
            }

    except Exception as e:

        print("TikTok API Error:", e)

    return None

# -------- PROCESS DOWNLOAD --------

def process_download(bot, chat_id, uid, url):

    bot.send_message(chat_id, "⏳ Downloading...")

    result = download_tiktok(url)

    if not result:
        bot.send_message(chat_id, "❌ Download failed")
        return

    bot_username = bot.get_me().username

    try:

        if result["type"] == "video":

            video = requests.get(result["media"]).content

            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(video)
                path = f.name

            bot.send_video(
                chat_id,
                open(path, "rb"),
                caption=f"Via @{bot_username}"
            )

            bot.send_message(
                chat_id,
                "Created: @Verify_yourbot"
            )

        elif result["type"] == "photo":

            for img in result["media"]:

                photo = requests.get(img).content

                bot.send_photo(
                    chat_id,
                    photo
                )

            bot.send_message(
                chat_id,
                f"Via @{bot_username}\n\nCreated: @Verify_yourbot"
            )

    except Exception as e:

        print("SEND MEDIA ERROR:", e)

        bot.send_message(
            chat_id,
            "❌ Failed to send media"
        )

# -------- START USER BOT --------

def start_user_bot(token):

    try:

        bot = telebot.TeleBot(token)

        @bot.message_handler(commands=["start"])
        def start(message):

            if not bots_active():

                bot.send_message(
                    message.chat.id,
                    "⚠️ Bots are temporarily disabled"
                )
                return

            uid = message.from_user.id
            save_user(uid)

            if send_force_join(bot, message.chat.id):
                return

            bot.send_message(
                message.chat.id,
"""👋 Welcome to TikTok Downloader Bot

📥 Send any TikTok link and I will download it instantly.

Features:
• No watermark video
• Photo slideshow download
• Fast download

Just send a TikTok link to begin.

━━━━━━━━━━━━━━

Create your own downloader:
@Verify_yourbot"""
            )

        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def tiktok(message):

            uid = message.from_user.id
            url = message.text

            process_download(
                bot,
                message.chat.id,
                uid,
                url
            )

        print("✅ Bot Started")

        bot.infinity_polling(skip_pending=True)

    except Exception as e:

        print("❌ Bot start error:", e)

# -------- RUNNER LOOP --------

print("🚀 Runner Started...")

while True:

    try:

        bots = list(bots_collection.find())

        active_tokens = []

        for b in bots:

            token = b.get("token")
            active = b.get("active", True)

            if not token:
                continue

            if active:

                active_tokens.append(token)

                if token not in running_bots:

                    t = threading.Thread(
                        target=start_user_bot,
                        args=(token,),
                        daemon=True
                    )

                    t.start()

                    running_bots[token] = True

                    print("🟢 Bot Started:", token)

            else:

                if token in running_bots:

                    print("🔴 Bot Removed:", token)

                    del running_bots[token]

        # remove bots not in database
        for token in list(running_bots.keys()):

            if token not in active_tokens:

                print("🛑 Bot Stopped:", token)

                del running_bots[token]

    except Exception as e:

        print("Runner error:", e)

    time.sleep(20)
