import telebot
import os
import time
import threading
import requests
from pymongo import MongoClient

# -------- ENV --------

MONGO_URL = os.getenv("MONGO_URL")

# -------- MONGODB --------

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]
system_collection = db["system"]

# -------- RUNNING BOTS --------

running_bots = {}

# -------- SAVE USER --------

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# -------- CHECK SYSTEM --------

def bots_active():

    s = system_collection.find_one({"system":"bots"})

    if not s:
        return True

    return s.get("active",True)

# -------- TIKTOK DOWNLOAD --------

def download_tiktok(url):

    try:

        api = f"https://tikwm.com/api/?url={url}"

        r = requests.get(api).json()

        if r["code"] != 0:
            return None

        data = r["data"]

        if data.get("play"):

            return {
                "type":"video",
                "media":data["play"]
            }

        if data.get("images"):

            return {
                "type":"photo",
                "media":data["images"]
            }

    except:
        pass

    return None

# -------- START USER BOT --------

def start_user_bot(token):

    if token in running_bots:
        return

    try:

        bot = telebot.TeleBot(token)

        # START
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

            bot.send_message(
                message.chat.id,
                "🎬 Send TikTok link to download video or photos"
            )


        # TIKTOK HANDLER
        @bot.message_handler(func=lambda m: "tiktok.com" in m.text)
        def tiktok(message):

            if not bots_active():

                bot.send_message(
                    message.chat.id,
                    "⚠️ Bots are temporarily disabled"
                )
                return

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


        running_bots[token] = bot

        print("✅ Started bot:", token)

        bot.infinity_polling(skip_pending=True)

    except Exception as e:

        print("❌ Bot start error:", e)


# -------- LOAD BOTS --------

def load_all_bots():

    bots = bots_collection.find()

    for b in bots:

        token = b.get("token")

        if not token:
            continue

        if token not in running_bots:

            threading.Thread(
                target=start_user_bot,
                args=(token,),
                daemon=True
            ).start()


# -------- RUNNER LOOP --------

print("🚀 Runner Started...")

while True:

    try:

        load_all_bots()

    except Exception as e:

        print("Runner error:", e)

    time.sleep(20)
