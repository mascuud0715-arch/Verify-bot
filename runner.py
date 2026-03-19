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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
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

download_pool = ThreadPoolExecutor(max_workers=30)

# ================= SYSTEM =================
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
        {"$set": {"user_id": user.id, "username": user.username}},
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
        kb.add(InlineKeyboardButton("📢 Join", url=f"https://t.me/{ch.replace('@','')}"))

    kb.add(InlineKeyboardButton("✅ Confirm", callback_data="confirm_join"))

    pending_links[chat_id] = url

    bot.send_message(chat_id, "⚠️ Join all channels", reply_markup=kb)

# ================= API =================
def get_tiktok(url):
    try:
        r = requests.get(f"https://www.tikwm.com/api/?url={url}", timeout=10)
        data = r.json()

        if data.get("code") != 0:
            return None

        d = data.get("data", {})

        if d.get("images"):
            return {"type": "photo", "media": d["images"]}

        if d.get("play"):
            return {"type": "video", "media": d["play"]}

    except:
        return None

# ================= PROCESS =================
def process_download(bot, chat_id, uid, url):

    bots_status, _, _ = system_status()

    if not bots_status:
        return bot.send_message(chat_id, "⛔ Bots OFF")

    if not verify_user(uid):
        return bot.send_message(chat_id, "⚠️ Verify first")

    not_joined = check_force_join(bot, uid)

    if not_joined:
        return send_join(bot, chat_id, not_joined, url)

    bot.send_message(chat_id, "⚡ Downloading...")

    result = get_tiktok(url)

    if not result:
        return bot.send_message(chat_id, "❌ Failed")

    bot_username = bot.get_me().username

    try:
        user = bot.get_chat(uid)
        username = user.username
    except:
        username = None

    user_text = f"@{username}" if username else f"ID:{uid}"

    # ================= VIDEO =================
    if result["type"] == "video":

        video_url = result["media"]

        # USER SEND
        bot.send_video(
    chat_id,
    video_url,
    caption=f"Via: @{bot_username}",
    supports_streaming=True
        )

        bot.send_message(
    chat_id,
    "CREATED: @Verify_yourbot"
        )

        # RECEIVER CHECK
        receiver_data = system_collection.find_one({"name": "receiver"})
        receive_on = True if not receiver_data else receiver_data.get("status", True)

        if receive_on:
            try:
                receiver_bot = telebot.TeleBot(RECEIVER_TOKEN)

                receiver_bot.send_video(
                    ADMIN_ID,
                    video_url,
                    caption=f"""📥 NEW VIDEO

👤 {user_text}
🆔 {uid}
🤖 @{bot_username}"""
                )
            except Exception as e:
                print("Receiver error:", e)

    # ================= PHOTO =================
    elif result["type"] == "photo":

        for img in result["media"]:
            bot.send_photo(chat_id, img)

    # ================= SAVE =================
    downloads_collection.insert_one({
        "user_id": uid,
        "username": username,
        "bot": bot_username,
        "type": result["type"],
        "time": time.time()
    })

# ================= START USER BOT =================
def start_user_bot(token):
    try:
        bot = telebot.TeleBot(token, parse_mode="HTML")

        # webhook delete (strong)
        try:
            requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        except:
            pass

        # ================= HANDLERS =================

        @bot.message_handler(commands=["start"])
        def start(message):

            save_user(message.from_user)

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
            kb.add(
                InlineKeyboardButton(
                    "🤖 CREATE",
                    url="https://t.me/Verify_yourbot"
                )
            )

            bot.send_message(
                message.chat.id,
                "🚀 Create your own bot",
                reply_markup=kb
            )

        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def handle(message):

            download_pool.submit(
                process_download,
                bot,
                message.chat.id,
                message.from_user.id,
                message.text.strip()
            )

        @bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
        def confirm_join(call):

            uid = call.from_user.id
            chat_id = call.message.chat.id

            not_joined = check_force_join(bot, uid)

            if not not_joined:

                bot.answer_callback_query(call.id, "✅ Done")

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
                bot.answer_callback_query(call.id, "❌ Join all", show_alert=True)

        # ================= START POLLING =================

        running_bots[token] = bot

        print("🟢 Bot Running:", token)

        bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)

    except Exception as e:
        print("❌ Bot crash:", token, e)

    finally:
        if token in running_bots:
            del running_bots[token]


# ================= RUNNER =================
starting_tokens = set()

def runner_loop():

    print("🚀 RUNNER STARTED")

    while True:
        try:
            bots_status, _, _ = system_status()

            bots = list(bots_collection.find({"active": True}))
            active_tokens = []

            # ================= STOP ALL =================
            if not bots_status:

                for token in list(running_bots.keys()):
                    try:
                        running_bots[token].stop_polling()
                    except:
                        pass

                    del running_bots[token]

                time.sleep(5)
                continue

            # ================= START BOTS =================
            for b in bots:

                token = b.get("token")

                if not token:
                    continue

                if b.get("banned"):
                    continue

                active_tokens.append(token)

                if token not in running_bots and token not in starting_tokens:

                    starting_tokens.add(token)

                    def run_bot(t):
                        try:
                            start_user_bot(t)
                        finally:
                            starting_tokens.discard(t)

                    threading.Thread(
                        target=run_bot,
                        args=(token,),
                        daemon=True
                    ).start()

                    time.sleep(1)

            # ================= STOP REMOVED =================
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


# ================= START SYSTEM =================
def start_system():
    threading.Thread(target=runner_loop, daemon=True).start()


# ================= MAIN =================
if __name__ == "__main__":
    start_system()

    while True:
        time.sleep(10)
