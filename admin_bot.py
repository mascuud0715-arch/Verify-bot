import telebot
import os
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pymongo import MongoClient

# ==============================
# ENV
# ==============================
TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==============================
# DATABASE
# ==============================
client = MongoClient(MONGO_URL)
db = client["verify_system"]

bots_collection = db["bots"]
users_collection = db["users"]
channels_collection = db["channels"]
downloads_collection = db["downloads"]
system_collection = db["system"]

# ==============================
# STATES
# ==============================
broadcast_mode = False

broadcast_data = {
    "text": None,
    "buttons": [],
    "style": "",
    "photo": None,
    "video": None
}

# ==============================
# ADMIN MENU
# ==============================
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(KeyboardButton("📊 Stats"), KeyboardButton("📊 Media Stats"))
    kb.add(KeyboardButton("🤖 Bots"))
    kb.add(KeyboardButton("📢 Broadcast"))
    kb.add(KeyboardButton("➕ Add Channel"), KeyboardButton("📡 Channels"))
    kb.add(KeyboardButton("❌ Close Channels"))
    kb.add(KeyboardButton("🚫 Close Bots"), KeyboardButton("✅ Open Bots"))
    kb.add(KeyboardButton("🟢 Verify ON"), KeyboardButton("🔴 Verify OFF"))
    kb.add(KeyboardButton("🔄 Refresh Bots"))
    kb.add(KeyboardButton("🏆 Top Bots"))
    kb.add(KeyboardButton("👥 Top Bot Users"), KeyboardButton("👑 Top Users"))
    kb.add(KeyboardButton("🔍 See Target Bot"))

    return kb

# ==============================
# START
# ==============================
@bot.message_handler(commands=["start"])
def start(message):
    print("START RECEIVED:", message.from_user.id)

    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Not Allowed")
        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )

# ==============================
# STATS
# ==============================
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):
    bots = bots_collection.count_documents({})
    users = users_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"📊 SYSTEM STATS\n\n🤖 Bots: {bots}\n👤 Users: {users}"
    )

# ==============================
# MEDIA STATS
# ==============================
@bot.message_handler(func=lambda m: m.text == "📊 Media Stats")
def media_stats(message):
    video = downloads_collection.count_documents({
        "type": {"$in": ["tiktok_video", "video"]}
    })

    photo = downloads_collection.count_documents({
        "type": {"$in": ["photo", "image", "tiktok_photo"]}
    })

    total = downloads_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"📥 DOWNLOAD STATS\n\n🎬 Videos: {video}\n🖼 Photos: {photo}\n📦 Total: {total}"
    )

# ==============================
# BROADCAST MENU
# ==============================
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):
    global broadcast_mode

    broadcast_mode = True

    broadcast_data.update({
        "text": None,
        "buttons": [],
        "style": "",
        "photo": None,
        "video": None
    })

    bot.send_message(
        message.chat.id,
        "📢 Send:\n\nText / Photo / Video"
    )

# ==============================
# RECEIVE CONTENT (FIXED 🔥)
# ==============================
@bot.message_handler(func=lambda m: broadcast_mode and broadcast_data["text"] is None,
                     content_types=["text", "photo", "video"])
def get_content(message):

    # TEXT
    if message.text:
        broadcast_data["text"] = message.text

    # PHOTO
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

        broadcast_data["photo"] = file_url
        broadcast_data["text"] = message.caption or ""

    # VIDEO
    elif message.video:
        file_info = bot.get_file(message.video.file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

        broadcast_data["video"] = file_url
        broadcast_data["text"] = message.caption or ""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Button", callback_data="add_btn"))
    kb.add(InlineKeyboardButton("👀 Preview", callback_data="preview"))
    kb.add(InlineKeyboardButton("📤 Send", callback_data="send"))

    bot.send_message(message.chat.id, "✅ Saved", reply_markup=kb)

# ==============================
# ADD BUTTON
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "add_btn")
def add_btn(call):
    msg = bot.send_message(call.message.chat.id, "Send button text")
    bot.register_next_step_handler(msg, get_btn_text)

def get_btn_text(message):
    text = message.text
    msg = bot.send_message(message.chat.id, "Send URL")
    bot.register_next_step_handler(msg, save_btn, text)

def save_btn(message, text):
    broadcast_data["buttons"].append((text, message.text))
    bot.send_message(message.chat.id, "✅ Button added")

# ==============================
# PREVIEW
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    try:
        # VIDEO
        if broadcast_data["video"]:
            bot.send_video(
                call.message.chat.id,
                broadcast_data["video"],
                caption=text,
                reply_markup=kb
            )

        # PHOTO
        elif broadcast_data["photo"]:
            bot.send_photo(
                call.message.chat.id,
                broadcast_data["photo"],
                caption=text,
                reply_markup=kb
            )

        # TEXT
        else:
            bot.send_message(
                call.message.chat.id,
                text,
                reply_markup=kb
            )

    except Exception as e:
        print("Preview error:", e)


# ==============================
# SEND BROADCAST (FAST 🚀)
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "send")
def send_broadcast(call):

    global broadcast_mode

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    bots = list(bots_collection.find())

    bots_used = 0
    delivered = 0

    for b in bots:
        try:
            send_bot = telebot.TeleBot(b["token"])
            bots_used += 1

            # 👉 ALL USERS
            users = users_collection.find()

            for u in users:
                try:
                    user_id = u.get("user_id")

                    if not user_id:
                        continue

                    # VIDEO
                    if broadcast_data["video"]:
                        send_bot.send_video(
                            user_id,
                            broadcast_data["video"],
                            caption=text,
                            reply_markup=kb
                        )

                    # PHOTO
                    elif broadcast_data["photo"]:
                        send_bot.send_photo(
                            user_id,
                            broadcast_data["photo"],
                            caption=text,
                            reply_markup=kb
                        )

                    # TEXT
                    else:
                        send_bot.send_message(
                            user_id,
                            text,
                            reply_markup=kb
                        )

                    delivered += 1

                except Exception as e:
                    print("USER ERROR:", e)

        except Exception as e:
            print("BOT ERROR:", e)

    # RESET
    broadcast_mode = False
    broadcast_data.update({
        "text": None,
        "buttons": [],
        "style": "",
        "photo": None,
        "video": None
    })

    bot.send_message(
        call.message.chat.id,
        f"""
📢 BROADCAST DONE

🤖 Bots: {bots_used}
📬 Delivered: {delivered}
"""
    )


# ==============================
# SAFE RUN
# ==============================
print("🚀 Admin Bot Running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling error:", e)
