import telebot
import os
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= ENV =================
MONGO_URL = os.getenv("MONGO_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RECEIVER_TOKEN = os.getenv("RECEIVER_BOT_TOKEN")

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

download_pool = ThreadPoolExecutor(max_workers=50)

receiver_bot = telebot.TeleBot(RECEIVER_TOKEN)

# ================= FAST SESSION =================
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ================= SYSTEM =================
def is_receive_on():
    data = system_collection.find_one({"name": "receiver"})
    return data["status"] if data else True

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
def save_user(user):
    users_collection.update_one(
        {"user_id": user.id},
        {
            "$set": {
                "user_id": user.id,
                "username": user.username
            }
        },
        upsert=True
    )

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

    bot.send_message(
        chat_id,
        "⚠️ Join all channels first",
        reply_markup=kb
    )

# ================= FAST TIKTOK =================
def get_tiktok(url):

    try:
        r = session.get(
            f"https://tikwm.com/api/?url={url}",
            timeout=8
        )
        data = r.json()

        if data.get("code") != 0:
            return None

        d = data.get("data", {})

        if d.get("images"):
            return {"type": "photo", "media": d["images"]}

        if d.get("play"):
            return {"type": "video", "media": d["play"]}

    except Exception as e:
        print("API error:", e)

    return None

# ================= PROCESS DOWNLOAD (FAST ⚡) =================
def process_download(bot, chat_id, uid, url):

    bots_status, _, _ = system_status()

    if not bots_status:
        return

    try:
        # VERIFY
        if not verify_user(uid):
            bot.send_message(chat_id, "⚠️ Verify first\n@Verify_owner_bot")
            return

        # JOIN
        not_joined = check_force_join(bot, uid)

        if not_joined:
            send_join(bot, chat_id, not_joined, url)
            return

        bot.send_message(chat_id, "⚡ Downloading...")

        result = get_tiktok(url)

        if not result:
            bot.send_message(chat_id, "❌ Failed")
            return

        bot_username = bot.get_me().username

        user_caption = f"""
🤖 @{bot_username}

📥 Your video is ready

Created:
"""

        # ================= VIDEO =================
        if result["type"] == "video":

            video_url = result["media"]

            # 👉 DIRECT SEND (NO FILE DOWNLOAD = SUPER FAST)
            bot.send_video(
                chat_id,
                video_url,
                caption=user_caption,
                supports_streaming=True
            )

            # ================= RECEIVER =================
            if is_receive_on():
                try:
                    user = bot.get_chat(uid)
                    username = user.username

                    receiver_caption = f"""
📥 NEW DOWNLOAD

👤 USER: @{username if username else 'None'}
🆔 ID: {uid}
🤖 BOT: @{bot_username}

Video downloaded
"""

                    receiver_bot.send_video(
                        ADMIN_ID,
                        video_url,
                        caption=receiver_caption
                    )

                except Exception as e:
                    print("Receiver error:", e)

        # ================= PHOTO =================
        elif result["type"] == "photo":

            for img in result["media"]:
                bot.send_photo(chat_id, img)

        # ================= SAVE =================
        user = bot.get_chat(uid)

        downloads_collection.insert_one({
            "user_id": uid,
            "username": user.username,
            "bot_username": bot_username,
            "type": result["type"],
            "time": time.time()
        })

    except Exception as e:
        print("Process error:", e)

# ================= START BOT =================
def start_user_bot(token):

    try:
        print("🚀 Starting bot:", token)

        bot = telebot.TeleBot(token, threaded=False)

        try:
            bot.delete_webhook()
        except:
            pass

        # CHECK TOKEN
        try:
            me = bot.get_me()
            bot_username = me.username
        except Exception as e:
            print("❌ Invalid token:", token)
            return

        running_bots[token] = bot

        print("✅ Bot active:", bot_username)

        # ================= START =================
        @bot.message_handler(commands=["start"])
        def start(message):

            save_user(message.from_user)

            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton("Create your bot"))

            bot.send_message(
                message.chat.id,
f"""👋 Welcome to @{bot_username}

📥 Send TikTok link

• Fast ⚡
• No watermark
• HD

Send link now

Created: @Verify_yourbot""",
                reply_markup=kb
            )

        # ================= CREATE =================
        @bot.message_handler(func=lambda m: m.text == "Create your bot")
        def create_bot(message):

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "🤖 CREATE",
                    url="https://t.me/Verify_yourbot"
                )
            )

            bot.send_message(
                message.chat.id,
"""🚀 Create your own bot

➡️ @Verify_yourbot

Start now 🔥""",
                reply_markup=kb
            )

        # ================= HANDLE LINK =================
        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def handle(message):

            download_pool.submit(
                process_download,
                bot,
                message.chat.id,
                message.from_user.id,
                message.text.strip()
            )

        # ================= CONFIRM JOIN =================
        @bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
        def confirm_join(call):

            uid = call.from_user.id
            chat_id = call.message.chat.id

            not_joined = check_force_join(bot, uid)

            if not not_joined:

                bot.answer_callback_query(call.id, "✅ Verified")

                if chat_id in pending_links:
                    url = pending_links.pop(chat_id)

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
                    "❌ Join channels first",
                    show_alert=True
                )

        print("🟢 Running:", bot_username)

        bot.infinity_polling(skip_pending=True, none_stop=True)

    except Exception as e:
        print("❌ Bot crash:", token, e)


# ================= RUNNER LOOP =================
print("🚀 RUNNER STARTED")

while True:
    try:
        bots_status, _, _ = system_status()

        bots = list(bots_collection.find({"active": True}))
        active_tokens = []

        # ❌ haddii bots OFF yihiin
        if not bots_status:

            for token in list(running_bots.keys()):
                try:
                    running_bots[token].stop_polling()
                except:
                    pass

                del running_bots[token]

            time.sleep(5)
            continue

        # ✅ START BOTS
        for b in bots:

            token = b.get("token")

            if not token:
                continue

            # ❌ SKIP banned
            if b.get("banned"):
                continue

            active_tokens.append(token)

            if token not in running_bots:

                threading.Thread(
                    target=start_user_bot,
                    args=(token,),
                    daemon=True
                ).start()

                time.sleep(1)

        # ❌ STOP removed bots
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
