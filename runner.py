import telebot
import os
import time
import threading
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient

# ================= ENV =================

MONGO_URL = os.getenv("MONGO_URL")

# ================= DATABASE =================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]

# ================= HTTP SESSION (ULTRA FAST) =================

session = requests.Session()

adapter = requests.adapters.HTTPAdapter(
    pool_connections=500,
    pool_maxsize=500,
    max_retries=3
)

session.mount("http://", adapter)
session.mount("https://", adapter)

# ================= THREAD POOL =================

download_pool = ThreadPoolExecutor(max_workers=500)

# ================= RUNNING BOTS =================

running_bots = {}

# ================= SAVE USER =================

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# ================= TIKTOK API =================

def download_tiktok(url):

    for _ in range(3):

        try:

            api = f"https://tikwm.com/api/?url={url}"

            r = session.get(api, timeout=60)

            data = r.json()

            if data["code"] != 0:
                continue

            d = data["data"]

            if d.get("play"):

                return {
                    "type": "video",
                    "media": d["play"]
                }

            if d.get("images"):

                return {
                    "type": "photo",
                    "media": d["images"]
                }

        except Exception as e:

            print("TikTok API error:", e)

    return None

# ================= DOWNLOAD VIDEO =================

def download_video(url):

    try:

        r = session.get(url, stream=True, timeout=120)

        with tempfile.NamedTemporaryFile(delete=False) as f:

            for chunk in r.iter_content(1024 * 1024):

                if chunk:
                    f.write(chunk)

            return f.name

    except Exception as e:

        print("Video download error:", e)

    return None

# ================= DOWNLOAD PHOTO =================

def download_photo(url):

    try:

        r = session.get(url, stream=True, timeout=60)

        with tempfile.NamedTemporaryFile(delete=False) as f:

            for chunk in r.iter_content(1024 * 1024):

                if chunk:
                    f.write(chunk)

            return f.name

    except Exception as e:

        print("Photo download error:", e)

    return None

# ================= PROCESS DOWNLOAD =================

def process_download(bot, chat_id, uid, url):

    try:

        bot.send_message(chat_id, "⏳ Downloading...")

        result = download_tiktok(url)

        if not result:

            bot.send_message(chat_id, "❌ Download failed")
            return

        bot_username = bot.get_me().username

        # ================= VIDEO =================

        if result["type"] == "video":

            path = download_video(result["media"])

            if not path:

                bot.send_message(chat_id, "❌ Video failed")
                return

            with open(path, "rb") as v:

                bot.send_video(
                    chat_id,
                    v,
                    caption=f"Via @{bot_username}",
                    supports_streaming=True
                )

            os.remove(path)

            bot.send_message(
                chat_id,
                "Created: @Verify_yourbot"
            )

            downloads_collection.insert_one({
                "type": "video",
                "user": uid
            })

        # ================= PHOTO =================

        elif result["type"] == "photo":

            for img in result["media"]:

                path = download_photo(img)

                if not path:
                    continue

                with open(path, "rb") as p:

                    bot.send_photo(
                        chat_id,
                        p
                    )

                os.remove(path)

            bot.send_message(
                chat_id,
                f"Via @{bot_username}\n\nCreated: @Verify_yourbot"
            )

            downloads_collection.insert_one({
                "type": "photo",
                "user": uid
            })

    except Exception as e:

        print("Process error:", e)

        bot.send_message(chat_id, "❌ Download error")

# ================= START USER BOT =================

def start_user_bot(token):

    try:

        bot = telebot.TeleBot(
            token,
            threaded=True,
            num_threads=100
        )

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

            # HIGH SPEED DOWNLOAD
            download_pool.submit(
                process_download,
                bot,
                message.chat.id,
                uid,
                url
            )

        print("🟢 Bot Started:", token)

        bot.infinity_polling(
            skip_pending=True,
            timeout=60,
            long_polling_timeout=60
        )

    except Exception as e:

        print("❌ Bot start error:", e)


# ================= RUNNER LOOP =================

print("🚀 Runner Started...")

while True:

    try:

        bots = list(bots_collection.find())

        active_tokens = []

        # ===== START / STOP BOTS =====

        for b in bots:

            token = b.get("token")

            active = b.get("active", True)

            if not token:
                continue

            if active:

                active_tokens.append(token)

                if token not in running_bots:

                    print("🟢 Starting bot:", token)

                    threading.Thread(
                        target=start_user_bot,
                        args=(token,),
                        daemon=True
                    ).start()

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

        # ===== REMOVE BOT IF DELETED FROM DATABASE =====

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

    time.sleep(15)
