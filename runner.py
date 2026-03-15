import telebot
import os
import time
import threading
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor
from telebot.types import InputMediaPhoto
from pymongo import MongoClient

# ================= ENV =================

MONGO_URL = os.getenv("MONGO_URL")
VERIFY_API = os.getenv("VERIFY_API")

# ================= DATABASE =================

client = MongoClient(MONGO_URL)
db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]
system_collection = db["system"]
channels_collection = db["channels"]

# ================= RUNNING BOTS =================

running_bots = {}

# ================= HIGH SPEED THREAD POOL =================

download_pool = ThreadPoolExecutor(max_workers=200)

# ================= SAVE USER =================

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# ================= DOWNLOAD TIKTOK =================
def download_tiktok(url):

    try:

        api = f"https://tikwm.com/api/?url={url}"

        r = requests.get(api, timeout=60).json()

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


# ================= PROCESS DOWNLOAD =================

def process_download(bot, chat_id, uid, url):

    bot.send_message(chat_id, "⏳ Downloading...")

    result = download_tiktok(url)

    if not result:

        bot.send_message(chat_id, "❌ Download failed")
        return

    bot_username = bot.get_me().username

    try:

        # ================= VIDEO =================

        if result["type"] == "video":

            r = requests.get(result["media"], stream=True, timeout=120)

            with tempfile.NamedTemporaryFile(delete=False) as f:

                for chunk in r.iter_content(chunk_size=1024*1024):

                    if chunk:
                        f.write(chunk)

                path = f.name

            bot.send_video(
                chat_id,
                open(path, "rb"),
                caption=f"Via @{bot_username}",
                supports_streaming=True
            )

            bot.send_message(
                chat_id,
                "Created: @Verify_yourbot"
            )

            downloads_collection.insert_one({
                "type": "video",
                "user": uid
            })


        # ================= PHOTO SLIDESHOW =================

        elif result["type"] == "photo":

            media_group = []

            for img in result["media"]:

                r = requests.get(img, stream=True, timeout=60)

                with tempfile.NamedTemporaryFile(delete=False) as f:

                    for chunk in r.iter_content(chunk_size=1024*1024):

                        if chunk:
                            f.write(chunk)

                    photo_path = f.name

                media_group.append(
                    InputMediaPhoto(
                        open(photo_path, "rb")
                    )
                )

            if media_group:

                bot.send_media_group(
                    chat_id,
                    media_group
                )

            bot.send_message(
                chat_id,
                f"Via @{bot_username}\n\nCreated: @Verify_yourbot"
            )

            downloads_collection.insert_one({
                "type": "photo",
                "user": uid
            })

    except Exception as e:

        print("SEND MEDIA ERROR:", e)

        bot.send_message(
            chat_id,
            "❌ Failed to send media"
        )


# ================= START USER BOT =================

def start_user_bot(token):

    try:

        bot = telebot.TeleBot(token, threaded=True)

        running_bots[token] = bot

        @bot.message_handler(commands=["start"])
        def start(message):

            uid = message.from_user.id
            save_user(uid)

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
            url = message.text.strip()

            # HIGH SPEED THREAD DOWNLOAD
            download_pool.submit(
                process_download,
                bot,
                message.chat.id,
                uid,
                url
            )

        print("🟢 Bot Started")

        bot.infinity_polling(skip_pending=True)

    except Exception as e:

        print("❌ Bot start error:", e)

# ================= RUNNER LOOP =================

print("🚀 Runner Started...")

while True:

    try:

        bots = list(bots_collection.find())
        active_tokens = []

        # ================= START / STOP BOTS =================

        for b in bots:

            token = b.get("token")
            active = b.get("active", True)

            if not token:
                continue

            # ===== BOT SHOULD RUN =====

            if active:

                active_tokens.append(token)

                if token not in running_bots:

                    print("🟢 Starting bot:", token)

                    threading.Thread(
                        target=start_user_bot,
                        args=(token,),
                        daemon=True
                    ).start()

            # ===== BOT SHOULD STOP =====

            else:

                if token in running_bots:

                    print("🔴 Stopping bot:", token)

                    try:

                        running_bots[token].stop_polling()

                    except:
                        pass

                    try:
                        del running_bots[token]
                    except:
                        pass


        # ================= REMOVE BOT =================

        for token in list(running_bots.keys()):

            if token not in active_tokens:

                print("🛑 Bot removed:", token)

                try:

                    running_bots[token].stop_polling()

                except:
                    pass

                try:
                    del running_bots[token]
                except:
                    pass


    except Exception as e:

        print("⚠ Runner error:", e)

    # ===== LOOP DELAY =====
    time.sleep(20)
