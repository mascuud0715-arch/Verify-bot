import telebot
import os
import time
import threading
import requests
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
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

# ================= GLOBAL =================
running_bots = {}
verified_users = {}
pending_links = {}

# ================= THREAD =================
download_pool = ThreadPoolExecutor(max_workers=10)

# ================= SESSION =================
def get_session():
    s = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=50,
        pool_maxsize=50,
        max_retries=2
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

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
    except Exception as e:
        print("Save user error:", e)

# ================= VERIFY =================
def verify_user(uid):
    _, verify_status, _ = system_status()

    if not verify_status:
        return True

    data = codes_collection.find_one({"user_id": uid})

    if not data:
        return False

    if data.get("expire", 0) < time.time():
        codes_collection.delete_one({"user_id": uid})
        return False

    return True

# ================= FORCE JOIN =================
def check_force_join(bot, user_id):
    _, _, channels_status = system_status()

    if not channels_status:
        return []

    if user_id in verified_users:
        return []

    not_joined = []

    for ch in channels_collection.find({"active": True}):
        username = ch.get("username")
        if not username:
            continue

        try:
            member = bot.get_chat_member(username, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(username)
        except:
            not_joined.append(username)

    if not not_joined:
        verified_users[user_id] = True

    return not_joined

# ================= JOIN BUTTON =================
def send_join(bot, chat_id, channels, url):
    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                "📢 Join Channel",
                url=f"https://t.me/{ch.replace('@','')}"
            )
        )

    kb.add(InlineKeyboardButton("✅ Confirm", callback_data="confirm_join"))

    pending_links[chat_id] = url

    bot.send_message(chat_id, "⚠️ Please join all channels first", reply_markup=kb)

# ================= TIKTOK API =================
def get_tiktok(url):
    apis = [
        f"https://tikwm.com/api/?url={url}",
        f"https://www.tikwm.com/api/?hd=1&url={url}"
    ]

    for api in apis:
        try:
            r = get_session().get(api, timeout=10)
            data = r.json()

            if data.get("code") != 0:
                continue

            d = data.get("data", {})

            if d.get("images"):
                return {"type": "photo", "media": d["images"]}

            if d.get("play"):
                return {"type": "video", "media": d["play"]}

        except:
            continue

    return None

# ================= DOWNLOAD =================
def download_file(url):
    try:
        r = get_session().get(url, stream=True, timeout=60)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            for chunk in r.iter_content(1024 * 512):
                if chunk:
                    f.write(chunk)

        return f.name

    except:
        return None

# ================= PROCESS DOWNLOAD =================
def process_download(bot, chat_id, uid, url):

    if not system_status()[0]:
        bot.send_message(chat_id, "⛔ Bots are OFF")
        return

    try:
        if not verify_user(uid):
            bot.send_message(chat_id, "⚠️ Verify first\n@Verify_owner_bot")
            return

        not_joined = check_force_join(bot, uid)

        if not_joined:
            send_join(bot, chat_id, not_joined, url)
            return

        msg = bot.send_message(chat_id, "⚡ Downloading...")
        result = get_tiktok(url)

        if not result:
            bot.send_message(chat_id, "❌ Failed")
            return

        bot_username = bot.get_me().username

        # VIDEO
        if result["type"] == "video":
            path = download_file(result["media"])

            if not path:
                bot.send_message(chat_id, "❌ Video failed")
                return

            with open(path, "rb") as v:
                bot.send_video(
                    chat_id,
                    v,
                    caption=f"Via: @{bot_username}",
                    supports_streaming=True
                )

            os.remove(path)

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "🤖 CREATE OWN BOT",
                    url="https://t.me/Verify_yourbot"
                )
            )

            bot.send_message(chat_id, "✨ Created: @Verify_yourbot", reply_markup=kb)

        # PHOTO
        elif result["type"] == "photo":
            for img in result["media"]:
                path = download_file(img)
                if not path:
                    continue

                with open(path, "rb") as p:
                    bot.send_photo(chat_id, p)

                os.remove(path)

        try:
            bot.delete_message(chat_id, msg.message_id)
        except:
            pass

        downloads_collection.insert_one({
            "user": uid,
            "time": time.time()
        })

    except Exception as e:
        print("Download error:", e)

# ================= START BOT =================
def start_user_bot(token):
    try:
        bot = telebot.TeleBot(token)
        bot.delete_webhook()
        bot.get_me()

        running_bots[token] = bot

        @bot.message_handler(commands=["start"])
        def start(message):
            save_user(message.from_user.id)

            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton("Create your bot"))

            bot.send_message(
                message.chat.id,
"""👋 Welcome to TikTok Downloader Bot

📥 Send any TikTok link and I will download it instantly.

Features
• No watermark
• Slideshow download
• Very fast

Send link now.

CREATED: @Verify_yourbot""",
                reply_markup=kb
            )

        @bot.message_handler(func=lambda m: m.text == "Create your bot")
        def create_bot(message):
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🤖 CREATE", url="https://t.me/Verify_yourbot"))

            bot.send_message(message.chat.id, "Click below 👇", reply_markup=kb)

        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def handle(message):
            download_pool.submit(
                process_download,
                bot,
                message.chat.id,
                message.from_user.id,
                message.text
            )

        @bot.callback_query_handler(func=lambda c: c.data == "confirm_join")
        def confirm(call):
            if call.message.chat.id in pending_links:
                url = pending_links.pop(call.message.chat.id)
                process_download(bot, call.message.chat.id, call.from_user.id, url)

        bot.infinity_polling()

    except Exception as e:
        print("Bot error:", e)

# ================= RUNNER =================
print("🚀 Runner Started")

while True:
    try:
        bots = list(bots_collection.find({"active": True}))
        active = []

        for b in bots:
            token = b.get("token")
            if not token:
                continue

            active.append(token)

            if token not in running_bots:
                threading.Thread(target=start_user_bot, args=(token,), daemon=True).start()
                time.sleep(1)

        for t in list(running_bots.keys()):
            if t not in active:
                del running_bots[t]

    except Exception as e:
        print("Runner error:", e)

    time.sleep(3)
