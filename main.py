import telebot
import requests
import os
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ================= ENV =================

TOKEN = os.getenv("MAIN_BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE =================

client = MongoClient(MONGO_URL)

db = client["verify_system"]

users_collection = db["users"]
channels_collection = db["channels"]
system_collection = db["system"]
downloads_collection = db["downloads"]

# ================= SAVE USER =================

def save_user(user):

    users_collection.update_one(
        {"user_id": user.id},
        {"$set": {
            "user_id": user.id,
            "username": user.username
        }},
        upsert=True
    )

# ================= SYSTEM STATUS =================

def bots_active():

    data = system_collection.find_one({"system": "bots"})

    if not data:
        return True

    return data.get("active", True)

# ================= FORCE JOIN CHECK =================

def check_force_join(user_id):

    channels = channels_collection.find({"active": True})

    not_joined = []

    for ch in channels:

        try:

            member = bot.get_chat_member(ch["username"], user_id)

            if member.status not in ["member", "administrator", "creator"]:

                not_joined.append(ch["username"])

        except:

            not_joined.append(ch["username"])

    return not_joined

# ================= FORCE JOIN MESSAGE =================

def send_force_join(chat_id, channels):

    kb = InlineKeyboardMarkup()

    for ch in channels:

        link = f"https://t.me/{ch.replace('@','')}"

        kb.add(
            InlineKeyboardButton("JOIN CHANNEL", url=link)
        )

    kb.add(
        InlineKeyboardButton("CONFIRM", callback_data="confirm_join")
    )

    bot.send_message(
        chat_id,
        "⚠️ Please join all channels to continue",
        reply_markup=kb
    )

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):

    if not bots_active():

        bot.send_message(
            message.chat.id,
            "🚫 Bot is temporarily disabled"
        )
        return

    save_user(message.from_user)

    not_joined = check_force_join(message.from_user.id)

    if not_joined:

        send_force_join(message.chat.id, not_joined)
        return

    bot.send_message(
        message.chat.id,
        f"""
🤖 Welcome To TikTok Downloader

Send a TikTok video or photo link.

The bot will download it instantly.

Powered by @{bot.get_me().username}
"""
    )

# ================= CONFIRM JOIN =================

@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
def confirm_join(call):

    not_joined = check_force_join(call.from_user.id)

    if not_joined:

        bot.answer_callback_query(
            call.id,
            "❌ You must join all channels",
            show_alert=True
        )

        return

    bot.edit_message_text(
        "✅ Verification successful\n\nSend TikTok link to download",
        call.message.chat.id,
        call.message.message_id
    )

# ================= TIKTOK API =================

def download_tiktok(url):

    try:

        api = f"https://tikwm.com/api/?url={url}"

        r = requests.get(api).json()

        if r["code"] == 0:

            data = r["data"]

            video = data.get("play")
            images = data.get("images")

            return video, images

    except:
        pass

    return None, None

# ================= HANDLE LINKS =================

@bot.message_handler(func=lambda m: True)
def handle_links(message):

    if not bots_active():

        bot.send_message(
            message.chat.id,
            "🚫 Bot is temporarily disabled"
        )
        return

    if not message.text:
        return

    text = message.text

    # -------- FORCE JOIN CHECK --------

    not_joined = check_force_join(message.from_user.id)

    if not_joined:

        send_force_join(message.chat.id, not_joined)
        return

    # -------- TIKTOK LINK --------

    if "tiktok.com" in text or "vt.tiktok.com" in text:

        bot.send_message(
            message.chat.id,
            "⏳ Downloading..."
        )

        video, images = download_tiktok(text)

        # -------- PHOTO SLIDES --------

        if images:

            for img in images:

                try:

                    bot.send_photo(
                        message.chat.id,
                        img
                    )

                except:
                    pass

            downloads_collection.insert_one({
                "user": message.from_user.id,
                "type": "photo",
                "time": int(time.time())
            })

            bot.send_message(
                message.chat.id,
                f"Via @{bot.get_me().username}"
            )

            bot.send_message(
                message.chat.id,
                "Created:@Verify_yourbot"
            )

            return

        # -------- VIDEO --------

        if video:

            try:

                bot.send_video(
                    message.chat.id,
                    video,
                    caption=f"Via @{bot.get_me().username}"
                )

                downloads_collection.insert_one({
                    "user": message.from_user.id,
                    "type": "tiktok",
                    "time": int(time.time())
                })

                bot.send_message(
                    message.chat.id,
                    "Created:@Verify_yourbot"
                )

            except:

                bot.send_message(
                    message.chat.id,
                    "❌ Failed to send video"
                )

            return

        bot.send_message(
            message.chat.id,
            "❌ Download failed")

# ================= RUN BOT =================

print("🚀 Downloader Bot Running...")

bot.infinity_polling(skip_pending=True)
