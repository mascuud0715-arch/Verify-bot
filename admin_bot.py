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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(TOKEN)


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

    kb.add(
        KeyboardButton("📊 Stats"),
        KeyboardButton("📊 Media Stats")
    )

    kb.add(
        KeyboardButton("🤖 Bots")
    )

    kb.add(
        KeyboardButton("📢 Broadcast")
    )

    kb.add(
        KeyboardButton("➕ Add Channel"),
        KeyboardButton("📡 Channels")
    )

    kb.add(
        KeyboardButton("❌ Close Channels")
    )

    kb.add(
        KeyboardButton("🚫 Close Bots"),
        KeyboardButton("✅ Open Bots")
    )

    kb.add(
        KeyboardButton("🟢 Verify ON"),
        KeyboardButton("🔴 Verify OFF")
    )

    kb.add(
    KeyboardButton("🔄 Refresh Bots")
    )

    kb.add(
    KeyboardButton("🏆 Top Bots")
    )

    kb.add(
    KeyboardButton("👥 Top Bot Users"),
    KeyboardButton("👑 Top Users")
    )

    kb.add(
    KeyboardButton("🔍 See Target Bot")
    )

    return kb


# ==============================
# START
# ==============================

@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "❌ Not Allowed"
        )
        return

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL",
        reply_markup=admin_menu()
    )


# ==============================
# SYSTEM STATS
# ==============================

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):

    bots = bots_collection.count_documents({})
    users = users_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"""
📊 SYSTEM STATS

🤖 Bots: {bots}
👤 Users: {users}
"""
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
        f"""
📥 DOWNLOAD STATS

🎬 Videos: {video}
🖼 Photos: {photo}
📦 Total Downloads: {total}
"""
    )


# ==============================
# BOTS PANEL
# ==============================

@bot.message_handler(func=lambda m: m.text == "🤖 Bots")
def bots_panel(message):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "👤 Usernames",
            callback_data="bot_usernames"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🔑 API Tokens",
            callback_data="bot_api"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🗑 Remove Bot",
            callback_data="remove_bot"
        )
    )

    bot.send_message(
        message.chat.id,
        "🤖 Bots Panel",
        reply_markup=kb
    )


# ==============================
# SHOW BOT USERNAMES
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "bot_usernames")
def bot_usernames(call):

    bots = bots_collection.find({"active": True})

    text = "🤖 Bots Usernames\n\n"

    i = 1

    for b in bots:

        text += f"{i}: {b.get('username')}\n"

        i += 1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ==============================
# SHOW BOT TOKENS
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "bot_api")
def bot_api(call):

    bots = bots_collection.find({"active": True})

    text = "🔑 Bots API\n\n"

    i = 1

    for b in bots:

        text += f"{i}: {b.get('token')}\n\n"

        i += 1

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )


# ==============================
# REMOVE BOT START
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "remove_bot")
def remove_bot_start(call):

    msg = bot.send_message(
        call.message.chat.id,
        "🗑 Send bot username to remove\n\nExample:\n@mybot"
    )

    bot.register_next_step_handler(msg, remove_bot_process)


# ==============================
# REMOVE BOT PROCESS
# ==============================

def remove_bot_process(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:

        bot.send_message(
            message.chat.id,
            "❌ Bot not found in system"
        )
        return

    # delete bot from bots collection
    bots_collection.delete_one({"username": username})

    # delete downloads related to this bot
    downloads_collection.delete_many({"bot_username": username})

    # optional: remove bot users data
    users_collection.update_many(
        {},
        {"$pull": {"bots": username}}
    )

    bot.send_message(
        message.chat.id,
        f"""
✅ BOT REMOVED SUCCESSFULLY

🤖 Username: @{username}
🔑 API Token: Deleted
📦 Downloads: Cleaned
🚫 Bot cannot work anymore
"""
    )

# ==============================
# ADD CHANNEL
# ==============================

@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(message):

    total = channels_collection.count_documents({"active": True})

    if total >= 5:

        bot.send_message(
            message.chat.id,
            "❌ Maximum 5 channels allowed"
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "Send channel username\nExample:\n@channel"
    )

    bot.register_next_step_handler(msg, save_channel)


def save_channel(message):

    channel = message.text.strip()

    channels_collection.update_one(
        {"username": channel},
        {
            "$set": {
                "username": channel,
                "active": True
            }
        },
        upsert=True
    )

    system_collection.update_one(
        {"system": "verify"},
        {"$set": {"active": True}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        f"✅ Channel Added\n{channel}"
    )


# ================= TOP =================
@bot.message_handler(func=lambda m: m.text == "🏆 Top Bots")
def top_bots(message):

    try:

        pipeline = [
            {
                "$group": {
                    "_id": "$bot_username",
                    "total": {"$sum": 1}
                }
            },
            {
                "$sort": {"total": -1}
            },
            {
                "$limit": 10
            }
        ]

        results = list(downloads_collection.aggregate(pipeline))

        if not results:
            bot.send_message(
                message.chat.id,
                "❌ No download data yet"
            )
            return

        text = "🏆 TOP BOTS (Most Downloads)\n\n"

        i = 1

        for r in results:

            username = r["_id"]
            total = r["total"]

            text += f"{i}. @{username} — {total} downloads\n"
            i += 1

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Top bots error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Error fetching top bots"
            )

# ================= TARGET BOT =================

@bot.message_handler(func=lambda m: m.text == "🔍 See Target Bot")
def ask_target_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "🤖 Send bot username\n\nExample:\n@mybot"
    )

    bot.register_next_step_handler(msg, process_target_bot)

def process_target_bot(message):

    username = message.text.replace("@", "").strip()

    try:

        # CHECK BOT EXISTS
        bot_data = bots_collection.find_one({"username": username})

        if not bot_data:
            bot.send_message(
                message.chat.id,
                "❌ Bot not found in system"
            )
            return

        # TOTAL DOWNLOADS
        total = downloads_collection.count_documents({
            "bot_username": username
        })

        # VIDEOS
        videos = downloads_collection.count_documents({
            "bot_username": username,
            "type": {"$in": ["video", "tiktok_video"]}
        })

        # PHOTOS
        photos = downloads_collection.count_documents({
            "bot_username": username,
            "type": {"$in": ["photo", "image", "tiktok_photo"]}
        })

        # UNIQUE USERS
        users_pipeline = [
            {"$match": {"bot_username": username}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total_users"}
        ]

        result = list(downloads_collection.aggregate(users_pipeline))
        total_users = result[0]["total_users"] if result else 0

        # TOP USERS (USERNAME)
        top_users_pipeline = [
            {
                "$match": {
                    "bot_username": username,
                    "username": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$username",
                    "total": {"$sum": 1}
                }
            },
            {
                "$sort": {"total": -1}
            },
            {
                "$limit": 5
            }
        ]

        top_users = list(downloads_collection.aggregate(top_users_pipeline))

        top_text = ""
        i = 1

        for u in top_users:
            top_text += f"{i}. @{u['_id']} — {u['total']}\n"
            i += 1

        if not top_text:
            top_text = "No data"

        # RESPONSE
        text = f"""
🔍 BOT ANALYTICS

🤖 Bot: @{username}

👥 Users: {total_users}
📥 Downloads: {total}

🎬 Videos: {videos}
🖼 Photos: {photos}

👑 Top Users:
{top_text}
"""

        bot.send_message(message.chat.id, text)

    except Exception as e:

        print("Target bot error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Error fetching bot data"
        )

# ================= TOB USERS =================
@bot.message_handler(func=lambda m: m.text == "👑 Top Users")
def top_users(message):

    try:

        pipeline = [
            {
                "$match": {
                    "username": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$username",
                    "total": {"$sum": 1}
                }
            },
            {
                "$sort": {"total": -1}
            },
            {
                "$limit": 10
            }
        ]

        results = list(downloads_collection.aggregate(pipeline))

        if not results:
            bot.send_message(message.chat.id, "❌ No data yet")
            return

        text = "👑 TOP USERS (GLOBAL DOWNLOADS)\n\n"

        i = 1

        for r in results:

            username = r["_id"]
            total = r["total"]

            text += f"{i}. @{username} — {total} downloads\n"
            i += 1

        bot.send_message(message.chat.id, text)

    except Exception as e:
        print("Top users error:", e)
        bot.send_message(message.chat.id, "❌ Error")
        
# ================= TOP USER =================
@bot.message_handler(func=lambda m: m.text == "👥 Top Bot Users")
def top_bot_users(message):

    try:

        pipeline = [
            {
                "$group": {
                    "_id": {
                        "bot": "$bot_username",
                        "user": "$user_id"
                    }
                }
            },
            {
                "$group": {
                    "_id": "$_id.bot",
                    "users": {"$sum": 1}
                }
            },
            {
                "$sort": {"users": -1}
            },
            {
                "$limit": 10
            }
        ]

        results = list(downloads_collection.aggregate(pipeline))

        if not results:
            bot.send_message(
                message.chat.id,
                "❌ No user data yet"
            )
            return

        text = "👥 TOP BOTS (Most Users)\n\n"

        i = 1

        for r in results:

            username = r["_id"]
            total_users = r["users"]

            text += f"{i}. @{username} — {total_users} users\n"
            i += 1

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Top bot users error:", e)

        bot.send_message(
            message.chat.id,
            "❌ Error fetching data"
        )


# ==============================
# CHANNEL LIST
# ==============================

@bot.message_handler(func=lambda m: m.text == "📡 Channels")
def channels(message):

    channels = channels_collection.find({"active": True})

    text = "📡 Force Join Channels\n\n"

    count = 0

    for c in channels:

        text += c["username"] + "\n"
        count += 1

    if count == 0:
        text = "❌ No active channels"

    bot.send_message(
        message.chat.id,
        text
    )


# ==============================
# CLOSE CHANNELS
# ==============================

@bot.message_handler(func=lambda m: m.text == "❌ Close Channels")
def close_channels(message):

    channels_collection.update_many(
        {},
        {"$set": {"active": False}}
    )

    system_collection.update_one(
    {"name": "system"},
    {"$set": {"bots_status": False}},
    upsert=True
    )

    bot.send_message(
        message.chat.id,
        "❌ Force Join System Disabled"
    )

# ==============================
# REFRESH BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Bots")
def refresh_bots(message):

    bots_collection.delete_many({"active": False})

    total = bots_collection.count_documents({"active": True})

    bot.send_message(
        message.chat.id,
        f"""
🔄 SYSTEM REFRESHED

🤖 Active Bots: {total}

Removed bots cleared from system.
"""
    )


# ==============================
# CLOSE BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "🚫 Close Bots")
def close_bots(message):

    system_collection.update_one(
        {"system": "bots"},
        {"$set": {"active": False}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🚫 All bots stopped"
    )


# ==============================
# OPEN BOTS
# ==============================

@bot.message_handler(func=lambda m: m.text == "✅ Open Bots")
def open_bots(message):

    system_collection.update_one(
    {"name": "system"},
    {"$set": {"bots_status": True}},
    upsert=True
    )

    bot.send_message(
        message.chat.id,
        "✅ Bots activated"
    )


# ==============================
# VERIFY ON
# ==============================

@bot.message_handler(func=lambda m: m.text == "🟢 Verify ON")
def verify_on(message):

    system_collection.update_one(
    {"name": "system"},
    {"$set": {"verify_status": True}},
    upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🟢 Verification Enabled"
    )


# ==============================
# VERIFY OFF
# ==============================

@bot.message_handler(func=lambda m: m.text == "🔴 Verify OFF")
def verify_off(message):

    system_collection.update_one(
    {"name": "system"},
    {"$set": {"verify_status": False}},
    upsert=True
    )

    bot.send_message(
        message.chat.id,
        "🔴 Verification Disabled"
    )


# ==============================
# BROADCAST MENU
# ==============================

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):

    global broadcast_mode

    broadcast_mode = True

    # RESET EVERYTHING
    broadcast_data["text"] = None
    broadcast_data["buttons"] = []
    broadcast_data["style"] = ""
    broadcast_data["photo"] = None
    broadcast_data["video"] = None

    bot.send_message(
        message.chat.id,
        """
📢 BROADCAST MODE

Send one of the following:

✏️ Text  
🖼 Photo + caption  
🎬 Video + caption  

Then customize buttons/style.
"""
    )


# ==============================
# RECEIVE TEXT
# ==============================

@bot.message_handler(func=lambda m: broadcast_mode and broadcast_data["text"] is None, content_types=["text", "photo", "video"])
def get_text(message):

    # TEXT
    if message.text:
        broadcast_data["text"] = message.text

    # PHOTO
    elif message.photo:

    file_info = bot.get_file(message.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    broadcast_data["photo"] = file_url
    broadcast_data["text"] = message.caption or ""

elif message.video:

    file_info = bot.get_file(message.video.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    broadcast_data["video"] = file_url
    broadcast_data["text"] = message.caption or ""

    kb = InlineKeyboardMarkup()

    kb.add(InlineKeyboardButton("➕ Add Inline", callback_data="add_inline"))
    kb.add(InlineKeyboardButton("🎨 Color", callback_data="color"))
    kb.add(InlineKeyboardButton("👀 Preview", callback_data="preview"))
    kb.add(InlineKeyboardButton("📤 Send Broadcast", callback_data="send_bc"))

    bot.send_message(message.chat.id, "Saved. Choose option:", reply_markup=kb)


# ==============================
# ADD INLINE BUTTON
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "add_inline")
def add_inline(call):

    msg = bot.send_message(
        call.message.chat.id,
        "Send button text"
    )

    bot.register_next_step_handler(msg, inline_text)


def inline_text(message):

    text = message.text

    msg = bot.send_message(
        message.chat.id,
        "Send button URL"
    )

    bot.register_next_step_handler(msg, inline_url, text)


def inline_url(message, text):

    if len(broadcast_data["buttons"]) >= 5:

        bot.send_message(
            message.chat.id,
            "❌ Max 5 buttons allowed"
        )
        return

    broadcast_data["buttons"].append(
        (text, message.text)
    )

    bot.send_message(
        message.chat.id,
        "✅ Button added"
    )


# ==============================
# COLOR STYLE
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "color")
def color_menu(call):

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("🔴 Red", callback_data="style_red")
    )

    kb.add(
        InlineKeyboardButton("🟢 Green", callback_data="style_green")
    )

    kb.add(
        InlineKeyboardButton("🔵 Blue", callback_data="style_blue")
    )

    bot.send_message(
        call.message.chat.id,
        "Choose style",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("style"))
def set_style(call):

    if call.data == "style_red":
        broadcast_data["style"] = "🔴"

    if call.data == "style_green":
        broadcast_data["style"] = "🟢"

    if call.data == "style_blue":
        broadcast_data["style"] = "🔵"

    bot.send_message(
        call.message.chat.id,
        "✅ Style applied"
    )


# ==============================
# PREVIEW
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):

    text = f"{broadcast_data['style']} {broadcast_data['text']}"

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    # VIDEO FIRST
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

    # TEXT ONLY
    else:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=kb
        )


# ==============================
# SEND BROADCAST
# ==============================

@bot.callback_query_handler(func=lambda c: c.data == "send_bc")
def send_broadcast(call):

    global broadcast_mode

    text = f"{broadcast_data['style']} {broadcast_data['text']}"

    kb = InlineKeyboardMarkup()
    for btt in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(btt[0], url=btt[1]))

    bots = list(bots_collection.find())

    bots_used = 0
    delivered = 0

    for b in bots:
        try:
            send_bot = telebot.TeleBot(b["token"])
            bots_used += 1

            # ✅ ONLY USERS OF THIS BOT
            bot_users = users_collection.find()

            for u in bot_users:
                try:

                    # 🎬 VIDEO
                    if broadcast_data.get("video"):
                        send_bot.send_video(
                            u["user_id"],
                            broadcast_data["video"],
                            caption=text,
                            reply_markup=kb
                        )

                    # 🖼 PHOTO
                    elif broadcast_data.get("photo"):
                        send_bot.send_photo(
                            u["user_id"],
                            broadcast_data["photo"],
                            caption=text,
                            reply_markup=kb
                        )

                    # 💬 TEXT
                    else:
                        send_bot.send_message(
                            u["user_id"],
                            text,
                            reply_markup=kb
                        )

                    delivered += 1

                except Exception as e:
                    print("USER ERROR:", e)

        except Exception as e:
            print("BOT ERROR:", e)

    broadcast_mode = False

    # RESET DATA
    broadcast_data["text"] = None
    broadcast_data["buttons"] = []
    broadcast_data["photo"] = None
    broadcast_data["video"] = None

    bot.send_message(
        call.message.chat.id,
        f"""
📢 BROADCAST SENT

🤖 Bots Used: {bots_used}
📬 Delivered: {delivered}
"""
    )


# ==============================
# RUN BOT
# ==============================

print("Admin Bot Running...")

bot.infinity_polling(skip_pending=True)
