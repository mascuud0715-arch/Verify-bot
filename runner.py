import telebot
import os
import time
import threading
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# -------- ENV --------

MONGO_URL = os.getenv("MONGO_URL")
VERIFY_API = os.getenv("VERIFY_API")   # main bot api

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

# -------- SAVE LINKS BEFORE JOIN --------

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

    s = system_collection.find_one({"system":"bots"})

    if not s:
        return True

    return s.get("active",True)

# -------- VERIFY JOIN (MAIN BOT API) --------

def verify_join(user_id):

    try:

        r = requests.get(
            VERIFY_API,
            params={"user_id":user_id},
            timeout=10
        ).json()

        return r

    except:

        return {"status":"error"}

# -------- FORCE JOIN MESSAGE --------

def send_force_join(bot, chat_id):

    # qaado channels active ah
    channels = list(channels_collection.find({"active": True}))

    # haddii channels jirin → ha dirin force join
    if len(channels) == 0:
        return False

    kb = InlineKeyboardMarkup()

    for ch in channels:

        link = f"https://t.me/{ch['username'].replace('@','')}"

        kb.add(
            InlineKeyboardButton(
                "JOIN CHANNEL",
                url=link
            )
        )

    kb.add(
        InlineKeyboardButton(
            "CONFIRM",
            callback_data="confirm_join"
        )
    )

    bot.send_message(
        chat_id,
        "⚠️ Please join all channels to continue",
        reply_markup=kb
    )

    return True

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

# -------- DOWNLOAD PROCESS --------

def process_download(bot, message, url):

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
    uid = message.from_user.id

    if result["type"] == "video":

        bot.send_video(
            message.chat.id,
            result["media"],
            caption=f"Via @{bot_username}"
        )

        downloads_collection.insert_one({
            "type":"tiktok_video",
            "user":uid
        })

    elif result["type"] == "photo":

        for img in result["media"]:

            bot.send_photo(
                message.chat.id,
                img,
                caption=f"Via @{bot_username}"
            )

        downloads_collection.insert_one({
            "type":"photo",
            "user":uid
        })

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

            save_user(message.from_user.id)

            send_force_join(bot, message.chat.id)

        # CONFIRM JOIN
        @bot.callback_query_handler(func=lambda call:call.data=="confirm_join")
        def confirm(call):

            uid = call.from_user.id

            r = verify_join(uid)

            if r["status"] != "joined":

                bot.answer_callback_query(
                    call.id,
                    "❌ Join all channels first",
                    show_alert=True
                )
                return

            bot.answer_callback_query(
                call.id,
                "✅ Verification successful"
            )

            if uid in pending_links:

                url = pending_links.pop(uid)

                process_download(bot, call.message, url)

            else:

                bot.edit_message_text(
                    "✅ Verification successful\n\nSend TikTok link",
                    call.message.chat.id,
                    call.message.message_id
                )

        # TIKTOK LINK
        @bot.message_handler(func=lambda m: m.text and "tiktok.com" in m.text)
        def tiktok(message):

            if not bots_active():

                bot.send_message(
                    message.chat.id,
                    "⚠️ Bots are temporarily disabled"
                )
                return

            uid = message.from_user.id
            url = message.text

            r = verify_join(uid)

            if r["status"] != "joined":

                pending_links[uid] = url

                send_force_join(bot, message.chat.id)
                return

            process_download(bot, message, url)

        running_bots[token] = bot

        print("✅ Started bot")

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
