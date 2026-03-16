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
    maxPoolSize=500
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

download_pool = ThreadPoolExecutor(max_workers=1000)

# ================= RUNNING BOTS =================

running_bots = {}

# ================= SAVE USER =================

def save_user(uid):

    try:

        users_collection.update_one(
            {"user_id": uid},
            {"$set": {"user_id": uid}},
            upsert=True
        )

    except Exception as e:

        print("Save user error:", e)

# ================= SYSTEM STATUS =================

def system_status():

    data = system_collection.find_one({"name": "system"})

    if not data:

        system_collection.insert_one({
            "name": "system",
            "bots_status": True,
            "verify_status": True
        })

        return True, True

    return data.get("bots_status", True), data.get("verify_status", True)

# ================= VERIFY USER =================

def verify_user(uid):

    bots_status, verify_status = system_status()

    if verify_status == False:
        return True

    data = codes_collection.find_one({"user_id": uid})

    if not data:
        return False

    if data.get("expire", 0) < time.time():

        codes_collection.delete_one({"user_id": uid})
        return False

    return True

# ================= BOT STATUS =================

def bots_enabled():

    bots_status, verify_status = system_status()

    if bots_status == False:
        return False

    return True

# ================= TIKTOK API =================

def download_tiktok(url):

    apis = [
        f"https://tikwm.com/api/?url={url}",
        f"https://www.tikwm.com/api/?hd=1&url={url}"
    ]

    headers = {"User-Agent": "Mozilla/5.0"}

    for api in apis:

        try:

            r = session.get(api, headers=headers, timeout=15)

            data = r.json()

            if data.get("code") != 0:
                continue

            d = data["data"]

            if d.get("images"):

                return {
                    "type": "photo",
                    "media": d["images"]
                }

            if d.get("play"):

                return {
                    "type": "video",
                    "media": d["play"]
                }

        except Exception as e:

            print("API error:", e)

    return None

# ================= DOWNLOAD VIDEO =================

def download_video(url):

    for i in range(5):

        try:

            r = session.get(
                url,
                stream=True,
                timeout=60
            )

            with tempfile.NamedTemporaryFile(delete=False) as f:

                for chunk in r.iter_content(1024 * 512):

                    if chunk:
                        f.write(chunk)

                return f.name

        except Exception as e:

            print("Video download error:", e)

            time.sleep(1)

    return None


# ================= DOWNLOAD PHOTO =================

def download_photo(url):

    for i in range(3):

        try:

            r = session.get(
                url,
                stream=True,
                timeout=60
            )

            with tempfile.NamedTemporaryFile(delete=False) as f:

                for chunk in r.iter_content(512 * 1024):

                    if chunk:
                        f.write(chunk)

                return f.name

        except Exception as e:

            print("Photo download error:", e)

            time.sleep(1)

    return None


# ================= PROCESS DOWNLOAD =================

def process_download(bot, chat_id, uid, url):

    if not bots_enabled():

        bot.send_message(
            chat_id,
            "⛔ Bots are currently closed by admin."
        )
        return

    try:

        if not verify_user(uid):

            bot.send_message(
                chat_id,
                "⚠️ You must verify first.\n\nGo to @Verify_owner_bot"
            )
            return

        bot.send_message(chat_id, "⏳ Downloading...")

        result = download_tiktok(url)

        if not result:

            bot.send_message(chat_id, "❌ Download failed")
            return

        bot_username = bot.get_me().username


        # ===== VIDEO =====

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

            try:
                os.remove(path)
            except:
                pass


        # ===== PHOTO SLIDESHOW =====

        elif result["type"] == "photo":

            for img in result["media"]:

                path = download_photo(img)

                if not path:
                    continue

                with open(path, "rb") as p:

                    bot.send_photo(chat_id, p)

                try:
                    os.remove(path)
                except:
                    pass

        try:

            downloads_collection.insert_one({
                "user": uid,
                "time": time.time()
            })

        except:
            pass

    except Exception as e:

        print("Download error:", e)



# ================= START USER BOT =================

def start_user_bot(token):

    while True:

        try:

            bot = telebot.TeleBot(
                token,
                threaded=True,
                num_threads=50
            )

            running_bots[token] = bot


            # ===== START =====

            @bot.message_handler(commands=["start"])
            def start(message):

                uid = message.from_user.id

                save_user(uid)

                bot.send_message(

message.chat.id,

"""👋 Welcome to TikTok Downloader

Send any TikTok link

Features
• No watermark
• Photo slideshow
• Fast download
"""
                )


            # ===== LINK HANDLER =====

            @bot.message_handler(func=lambda m: m.text and ("tiktok.com" in m.text or "vt.tiktok.com" in m.text))
            def tiktok(message):

                download_pool.submit(
                    process_download,
                    bot,
                    message.chat.id,
                    message.from_user.id,
                    message.text.strip()
                )


            print("🟢 Bot Started:", token)

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print("Bot crash:", token, e)

            time.sleep(5)



# ================= RUNNER SYSTEM =================

print("🚀 Runner Started")

while True:

    try:

        bots_status, verify_status = system_status()

        bots = list(bots_collection.find({"active": True}))

        active_tokens = []

        if not bots_status:

            for token in list(running_bots.keys()):

                try:
                    running_bots[token].stop_polling()
                except:
                    pass

                del running_bots[token]

            time.sleep(5)
            continue


        # ===== START NEW BOTS =====

        for b in bots:

            token = b.get("token")

            if not token:
                continue

            active_tokens.append(token)

            if token not in running_bots:

                threading.Thread(
                    target=start_user_bot,
                    args=(token,),
                    daemon=True
                ).start()

                time.sleep(0.1)


        # ===== STOP REMOVED BOTS =====

        for token in list(running_bots.keys()):

            if token not in active_tokens:

                try:
                    running_bots[token].stop_polling()
                except:
                    pass

                del running_bots[token]


    except Exception as e:

        print("Runner error:", e)


    # FAST SCAN

    time.sleep(3)
