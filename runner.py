import telebot
import os
import time
import threading
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= ENV =================

MONGO_URL = os.getenv("MONGO_URL")

# ================= DATABASE =================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
downloads_collection = db["downloads"]
codes_collection = db["codes"]
system_collection = db["system"]
channels_collection = db["channels"]

# ================= RUNNING BOTS =================

running_bots = {}

# ================= CACHE =================

verified_users = {}
pending_links = {}

# ================= HTTP SESSION =================

session = requests.Session()

adapter = requests.adapters.HTTPAdapter(
    pool_connections=1000,
    pool_maxsize=1000,
    max_retries=3
)

session.mount("http://", adapter)
session.mount("https://", adapter)

# ================= THREAD POOL =================

download_pool = ThreadPoolExecutor(max_workers=500)

# ================= SYSTEM STATUS =================

def system_status():

    data = system_collection.find_one({"name": "system"})

    if not data:

        system_collection.insert_one({
            "name": "system",
            "bots_status": True,
            "verify_status": True,
            "channels_status": True
        })

        return True, True, True

    return (
        data.get("bots_status", True),
        data.get("verify_status", True),
        data.get("channels_status", True)
    )

# ================= SAVE USER =================

def save_user(uid):

    try:

        users_collection.update_one(
            {"user_id": uid},
            {"$set": {"user_id": uid}},
            upsert=True
        )

    except:
        pass

# ================= VERIFY CHECK =================

def verify_user(uid):

    bots_status, verify_status, channels_status = system_status()

    if verify_status == False:
        return True

    data = codes_collection.find_one({"user_id": uid})

    if not data:
        return False

    if data.get("expire", 0) < time.time():

        codes_collection.delete_one({"user_id": uid})
        return False

    return True

# ================= FORCE JOIN CHECK =================

def check_force_join(bot, user_id):

    bots_status, verify_status, channels_status = system_status()

    if channels_status == False:
        return []

    if user_id in verified_users:
        return []

    not_joined = []

    channels = channels_collection.find({"active": True})

    for ch in channels:

        username = ch.get("username")

        if not username:
            continue

        try:

            member = bot.get_chat_member(username, user_id)

            if member.status not in [
                "member",
                "administrator",
                "creator"
            ]:

                not_joined.append(username)

        except:

            not_joined.append(username)

    if not not_joined:
        verified_users[user_id] = True

    return not_joined

# ================= SEND JOIN BUTTONS =================

def send_join(bot, chat_id, channels, url):

    kb = InlineKeyboardMarkup()

    for ch in channels:

        link = f"https://t.me/{ch.replace('@','')}"

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

    pending_links[chat_id] = url

    bot.send_message(
        chat_id,
        "⚠️ Please join channels first",
        reply_markup=kb
    )

# ================= FAST TIKTOK API =================

def get_tiktok(url):

    apis = [
        f"https://tikwm.com/api/?url={url}",
        f"https://www.tikwm.com/api/?hd=1&url={url}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for api in apis:

        try:

            r = session.get(api, headers=headers, timeout=10)

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

        except:
            pass

    return None

# ================= DOWNLOAD FILE =================

def download_file(url):

    try:

        r = session.get(url, stream=True, timeout=60)

        with tempfile.NamedTemporaryFile(delete=False) as f:

            for chunk in r.iter_content(1024*1024):

                if chunk:
                    f.write(chunk)

            return f.name

    except:
        return None

# ================= PROCESS DOWNLOAD =================

def process_download(bot, chat_id, uid, url):

    bots_status, verify_status, channels_status = system_status()

    if not bots_status:

        bot.send_message(
            chat_id,
            "⛔ Bots are currently OFF by admin."
        )
        return

    try:

        # ===== VERIFY CHECK =====

        if not verify_user(uid):

            bot.send_message(
                chat_id,
                "⚠️ You must verify first.\n\nGo to @Verify_owner_bot"
            )
            return


        # ===== FORCE JOIN CHECK =====

        not_joined = check_force_join(bot, uid)

        if not_joined:

            send_join(bot, chat_id, not_joined, url)
            return


        bot.send_message(chat_id, "⚡ Downloading...")


        # ===== GET MEDIA =====

        result = get_tiktok(url)

        if not result:

            bot.send_message(chat_id, "❌ Download failed")
            return


        bot_username = bot.get_me().username


        # ===== VIDEO =====

        if result["type"] == "video":

            video_url = result["media"]

            path = download_file(video_url)

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


        # ===== PHOTO =====

        elif result["type"] == "photo":

            for img in result["media"]:

                path = download_file(img)

                if not path:
                    continue

                with open(path, "rb") as p:

                    bot.send_photo(chat_id, p)

                try:
                    os.remove(path)
                except:
                    pass


        # ===== SAVE DOWNLOAD =====

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
                num_threads=100
            )

            running_bots[token] = bot


            # ===== START COMMAND =====

            @bot.message_handler(commands=["start"])
            def start(message):

                uid = message.from_user.id

                save_user(uid)

                bot.send_message(

                    message.chat.id,

"""👋 Welcome to TikTok Downloader Bot

📥 Send any TikTok link and I will download it instantly.

Features:
• No watermark
• Slideshow download
• Very fast

Send link now.
"""
                )

            bot.send_message(

                    message.chat.id,
                """CREATED: @Verify_yourbot
                """
            )


            # ===== LINK HANDLER =====

            @bot.message_handler(func=lambda m: m.text and ("tiktok.com" in m.text or "vt.tiktok.com" in m.text))
            def tiktok(message):

                url = message.text.strip()

                download_pool.submit(
                    process_download,
                    bot,
                    message.chat.id,
                    message.from_user.id,
                    url
                )


            # ===== CONFIRM JOIN =====

            @bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
            def confirm_join(call):

                uid = call.from_user.id
                chat_id = call.message.chat.id

                not_joined = check_force_join(bot, uid)

                if not not_joined:

                    bot.answer_callback_query(
                        call.id,
                        "✅ Verified"
                    )

                    if chat_id in pending_links:

                        url = pending_links[chat_id]

                        del pending_links[chat_id]

                        download_pool.submit(
                            process_download,
                            bot,
                            chat_id,
                            uid,
                            url
                        )

                else:

                    bot.answer_callback_query(
                        call.id,
                        "❌ Join all channels first",
                        show_alert=True
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

        bots_status, verify_status, channels_status = system_status()

        bots = list(bots_collection.find({"active": True}))

        active_tokens = []


        # ===== SYSTEM OFF =====

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

                time.sleep(0.2)


        # ===== REMOVE BOT =====

        for token in list(running_bots.keys()):

            if token not in active_tokens:

                try:
                    running_bots[token].stop_polling()
                except:
                    pass

                del running_bots[token]


    except Exception as e:

        print("Runner error:", e)


    time.sleep(3)
