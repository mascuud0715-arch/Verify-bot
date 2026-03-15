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

client = MongoClient(
    MONGO_URL,
    maxPoolSize=300
)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]
codes_collection = db["codes"]
system_collection = db["system"]

# ================= HTTP SESSION =================

session = requests.Session()

adapter = requests.adapters.HTTPAdapter(
    pool_connections=500,
    pool_maxsize=500,
    max_retries=3
)

session.mount("http://", adapter)
session.mount("https://", adapter)

# ================= THREAD POOL =================

download_pool = ThreadPoolExecutor(max_workers=700)

# ================= RUNNING BOTS =================

running_bots = {}

# ================= SAVE USER =================

def save_user(uid):

    users_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid}},
        upsert=True
    )

# ================= CHECK DOWNLOADER STATUS =================

def downloader_enabled():

    data = system_collection.find_one({"name": "system"})

    if not data:
        return True

    return data.get("downloader_status", True)

# ================= VERIFY USER =================

def verify_user(uid):

    data = codes_collection.find_one({"user_id": uid})

    if not data:
        return False

    # CHECK EXPIRE
    if data.get("expire", 0) < time.time():

        codes_collection.delete_one({"user_id": uid})

        return False

    return True

# ================= TIKTOK API =================

def download_tiktok(url):

    for i in range(5):

        try:

            api = f"https://tikwm.com/api/?url={url}"

            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            r = session.get(api, headers=headers, timeout=60)

            data = r.json()

            if data.get("code") != 0:
                time.sleep(1)
                continue

            d = data["data"]

            # PHOTO SLIDESHOW
            if d.get("images"):

                return {
                    "type": "photo",
                    "media": d["images"]
                }

            # VIDEO
            if d.get("play"):

                return {
                    "type": "video",
                    "media": d["play"]
                }

        except Exception as e:

            print("TikTok API error:", e)

            time.sleep(1)

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

        if not downloader_enabled():

            bot.send_message(
                chat_id,
                "⛔ Downloader is currently disabled by admin"
            )
            return

        if not verify_user(uid):

            bot.send_message(
                chat_id,
                "⚠️ You must verify first.\n\nGo to @Verify_owner_bot and get your code."
            )
            return

        bot.send_message(chat_id, "⏳ Downloading...")

        result = download_tiktok(url)

        if not result:

            bot.send_message(chat_id, "❌ Download failed")
            return

        bot_username = bot.get_me().username

        # VIDEO
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

            downloads_collection.insert_one({
                "type": "video",
                "user": uid
            })

        # PHOTO SLIDESHOW
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
            num_threads=120
        )

        running_bots[token] = bot

        # -------- START COMMAND --------

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

⚠️ Verification required before downloading.

Get your code from:
@Verify_owner_bot"""
            )

        # -------- CODE VERIFY --------

        @bot.message_handler(func=lambda m: m.text and m.text.isdigit())
        def verify_code(message):

            uid = message.from_user.id

            code = message.text.strip()

            data = codes_collection.find_one({"code": code})

            if not data:

                bot.send_message(
                    message.chat.id,
                    "❌ Invalid code"
                )
                return

            # CHECK EXPIRE
            if data.get("expire", 0) < time.time():

                bot.send_message(
                    message.chat.id,
                    "❌ Code expired"
                )

                codes_collection.delete_one({"code": code})

                return

            if data["user_id"] != uid:

                bot.send_message(
                    message.chat.id,
                    "❌ This code is not yours"
                )
                return

            # SAVE VERIFIED USER
            codes_collection.update_one(
                {"user_id": uid},
                {"$set": {"verified": True}}
            )

            bot.send_message(
                message.chat.id,
                "✅ Verification successful\n\nNow send TikTok link."
            )

        # -------- TIKTOK LINK --------

        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def tiktok(message):

            uid = message.from_user.id
            url = message.text.strip()

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

        # REMOVE BOTS IF DELETED

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
