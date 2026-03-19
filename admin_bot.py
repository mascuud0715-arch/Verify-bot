import telebot
import os
import time
import threading
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor

# ==============================
# ENV
# ==============================
TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGO_URL = os.getenv("MONGO_URL")
RECEIVER_TOKEN = os.getenv("RECEIVER_BOT_TOKEN")

if not TOKEN or not MONGO_URL:
    raise Exception("❌ ENV VARIABLES MISSING")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

receiver_bot = None
if RECEIVER_TOKEN:
    receiver_bot = telebot.TeleBot(RECEIVER_TOKEN)

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
# SYSTEM INIT (FIXED)
# ==============================
def init_system():
    if not system_collection.find_one({"_id": "system"}):
        system_collection.insert_one({
            "_id": "system",
            "bots_active": True
        })

    if not system_collection.find_one({"_id": "verify"}):
        system_collection.insert_one({
            "_id": "verify",
            "status": True
        })

    if not system_collection.find_one({"_id": "receiver"}):
        system_collection.insert_one({
            "_id": "receiver",
            "status": True
        })

init_system()

# ==============================
# GLOBAL STATES
# ==============================
broadcast_mode = False

broadcast_data = {
    "text": None,
    "buttons": [],
    "photo": None,
    "video": None
}

broadcast_lock = threading.Lock()

# ==============================
# SYSTEM SETTINGS
# ==============================
def set_verify(status: bool):
    system_collection.update_one(
        {"_id": "verify"},
        {"$set": {"status": status}},
        upsert=True
    )

def get_verify():
    data = system_collection.find_one({"_id": "verify"})
    return data.get("status", True) if data else True

def set_bots_status(status: bool):
    system_collection.update_one(
        {"_id": "system"},
        {"$set": {"bots_active": status}},
        upsert=True
    )

def bots_status():
    data = system_collection.find_one({"_id": "system"})
    return data.get("bots_active", True) if data else True

def is_receive_on():
    data = system_collection.find_one({"_id": "receiver"})
    return data.get("status", True) if data else True

# ==============================
# ADMIN MENU (ALL BUTTONS)
# ==============================
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("📊 Stats", "📊 Media Stats")
    kb.add("🤖 Bots", "📢 Broadcast")

    kb.add("➕ Add Channel", "📡 Channels")
    kb.add("❌ Close Channels")

    kb.add("🚫 Close Bots", "✅ Open Bots")

    kb.add("🟢 Verify ON", "🔴 Verify OFF")

    kb.add("🔄 Refresh Bots", "🏆 Top Bots")

    kb.add("👥 Top Bot Users", "👑 Top Users")

    kb.add("🔍 See Target Bot", "🗑 Remove Bot")

    kb.add("📥 RECEIVE MESSAGE", "❌ CLOSE RECEIVE")

    return kb

# ==============================
# ADMIN CHECK
# ==============================
def admin_only(func):
    def wrapper(message, *args, **kwargs):
        if message.from_user.id != ADMIN_ID:
            return
        return func(message, *args, **kwargs)
    return wrapper

# ==============================
# START
# ==============================
@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Not Allowed")

    bot.send_message(
        message.chat.id,
        "⚙️ ADMIN PANEL READY",
        reply_markup=admin_menu()
    )

# ==============================
# STATS
# ==============================
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
@admin_only
def stats(message):

    bots = bots_collection.count_documents({})
    users = users_collection.count_documents({})

    bot.send_message(
        message.chat.id,
        f"📊 SYSTEM\n\n🤖 Bots: {bots}\n👤 Users: {users}"
    )

# ==============================
# VERIFY CONTROL
# ==============================
@bot.message_handler(func=lambda m: m.text == "🟢 Verify ON")
@admin_only
def verify_on(message):
    set_verify(True)
    bot.send_message(message.chat.id, "✅ VERIFY ENABLED")

@bot.message_handler(func=lambda m: m.text == "🔴 Verify OFF")
@admin_only
def verify_off(message):
    set_verify(False)
    bot.send_message(message.chat.id, "❌ VERIFY DISABLED")

# ==============================
# BOTS CONTROL
# ==============================
@bot.message_handler(func=lambda m: m.text == "🚫 Close Bots")
@admin_only
def close_bots(message):
    set_bots_status(False)
    bot.send_message(message.chat.id, "🚫 ALL BOTS CLOSED")

@bot.message_handler(func=lambda m: m.text == "✅ Open Bots")
@admin_only
def open_bots(message):
    set_bots_status(True)
    bot.send_message(message.chat.id, "✅ ALL BOTS OPENED")

# ==============================
# REFRESH BOTS
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Bots")
@admin_only
def refresh_bots(message):

    valid = 0
    removed = 0

    for b in bots_collection.find():
        try:
            telebot.TeleBot(b["token"]).get_me()
            valid += 1
        except:
            bots_collection.delete_one({"_id": b["_id"]})
            removed += 1

    bot.send_message(
        message.chat.id,
        f"🔄 DONE\n\n✅ Active: {valid}\n❌ Removed: {removed}"
    )

# ==============================
# TOP USERS
# ==============================
@bot.message_handler(func=lambda m: m.text == "👑 Top Users")
@admin_only
def top_users(message):

    ranking = []

    for u in users_collection.find():
        downloads = downloads_collection.count_documents({"user_id": u["user_id"]})

        ranking.append({
            "username": u.get("username","NoUsername"),
            "downloads": downloads
        })

    ranking = sorted(ranking, key=lambda x: x["downloads"], reverse=True)[:10]

    text = "👑 TOP USERS\n\n"

    for i, r in enumerate(ranking, 1):
        text += f"{i}. @{r['username']} → {r['downloads']}\n"

    bot.send_message(message.chat.id, text)

# ==============================
# THREAD SAFE SEND
# ==============================
def send_to_user(send_bot, user_id, text, kb, photo=None, video=None):
    try:

        if video:
            send_bot.send_video(user_id, video, caption=text or "", reply_markup=kb)
        elif photo:
            send_bot.send_photo(user_id, photo, caption=text or "", reply_markup=kb)
        else:
            send_bot.send_message(user_id, text or "", reply_markup=kb)

        return 1

    except Exception as e:
        print("Send error:", e)
        return 0

# ==============================
# BROADCAST MENU
# ==============================
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
@admin_only
def broadcast_menu(message):

    global broadcast_mode

    broadcast_mode = True

    # RESET
    broadcast_data["text"] = None
    broadcast_data["buttons"] = []
    broadcast_data["photo"] = None
    broadcast_data["video"] = None

    bot.send_message(
        message.chat.id,
        "📢 Send broadcast:\n\nText / Photo / Video"
    )

# ==============================
# GET CONTENT
# ==============================
@bot.message_handler(func=lambda m: broadcast_mode, content_types=["text","photo","video"])
def get_broadcast_content(message):

    global broadcast_mode

    if message.from_user.id != ADMIN_ID:
        return

    # CLEAR MEDIA
    broadcast_data["photo"] = None
    broadcast_data["video"] = None

    if message.content_type == "text":
        broadcast_data["text"] = message.text

    elif message.content_type == "photo":
        broadcast_data["photo"] = message.photo[-1].file_id
        broadcast_data["text"] = message.caption or ""

    elif message.content_type == "video":
        broadcast_data["video"] = message.video.file_id
        broadcast_data["text"] = message.caption or ""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Add Button", callback_data="add_btn"))
    kb.add(InlineKeyboardButton("👀 Preview", callback_data="preview"))
    kb.add(InlineKeyboardButton("📤 Send", callback_data="send"))

    bot.send_message(message.chat.id, "✅ Saved", reply_markup=kb)

# ==============================
# ADD BUTTON
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "add_btn")
def add_button(call):

    if call.from_user.id != ADMIN_ID:
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(call.message.chat.id, "Send button text")
    bot.register_next_step_handler(msg, get_button_text)

def get_button_text(message):

    text = message.text

    if not text:
        return bot.send_message(message.chat.id, "❌ Invalid text")

    msg = bot.send_message(message.chat.id, "Send URL")
    bot.register_next_step_handler(msg, save_button, text)

def save_button(message, text):

    url = message.text

    if not url.startswith("http"):
        return bot.send_message(message.chat.id, "❌ Invalid URL")

    broadcast_data["buttons"].append((text, url))

    bot.send_message(message.chat.id, "✅ Button added")

# ==============================
# PREVIEW
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview_broadcast(call):

    if call.from_user.id != ADMIN_ID:
        return

    bot.answer_callback_query(call.id)

    text = broadcast_data.get("text") or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    try:

        if broadcast_data["video"]:
            bot.send_video(call.message.chat.id, broadcast_data["video"], caption=text, reply_markup=kb)

        elif broadcast_data["photo"]:
            bot.send_photo(call.message.chat.id, broadcast_data["photo"], caption=text, reply_markup=kb)

        else:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)

    except Exception as e:
        print("Preview error:", e)
        bot.send_message(call.message.chat.id, "❌ Preview failed")

# ==============================
# BROADCAST SEND (FINAL FIX 💥)
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "send")
def send_broadcast(call):

    if call.from_user.id != ADMIN_ID:
        return

    bot.answer_callback_query(call.id)

    global broadcast_mode

    text = broadcast_data.get("text")
    photo = broadcast_data.get("photo")
    video = broadcast_data.get("video")

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    bots = list(bots_collection.find())

    total_sent = 0
    bots_used = 0
    total_users = 0

    with broadcast_lock:

        with ThreadPoolExecutor(max_workers=30) as executor:

            futures = []

            for b in bots:

                if b.get("banned"):
                    continue

                try:
                    send_bot = telebot.TeleBot(b["token"])
                    bots_used += 1

                    # 🔥 IMPORTANT FIX (BOT MATCHING)
                    users = list(users_collection.find({
                        "$or": [
                            {"bot": b["username"]},
                            {"bot": f"@{b['username']}"}
                        ]
                    }))

                    print(f"🤖 {b['username']} → {len(users)} users")

                    total_users += len(users)

                    for u in users:

                        user_id = u.get("user_id")

                        if not user_id:
                            continue

                        futures.append(
                            executor.submit(
                                send_to_user,
                                send_bot,
                                user_id,
                                text,
                                kb,
                                photo,
                                video
                            )
                        )

                except Exception as e:
                    print("Bot error:", e)

            for f in futures:
                try:
                    total_sent += f.result()
                except:
                    pass

    # RESET
    broadcast_mode = False
    broadcast_data.update({
        "text": None,
        "buttons": [],
        "photo": None,
        "video": None
    })

    bot.send_message(
        call.message.chat.id,
        f"""
📢 BROADCAST DONE

🤖 Bots Used: {bots_used}
👥 Users Found: {total_users}
📬 Sent: {total_sent}
"""
)

# ==============================
# BOTS MENU
# ==============================
@bot.message_handler(func=lambda m: m.text == "🤖 Bots")
@admin_only
def bots_menu(message):

    bots = list(bots_collection.find())

    if not bots:
        return bot.send_message(message.chat.id, "❌ No bots")

    text = "🤖 BOTS LIST\n\n"

    for i, b in enumerate(bots, 1):
        status = "🚫 BANNED" if b.get("banned") else "✅ ACTIVE"
        text += f"{i}. @{b.get('username')} → {status}\n"

    bot.send_message(message.chat.id, text)

# ==============================
# REMOVE BOT
# ==============================
@bot.message_handler(func=lambda m: m.text == "🗑 Remove Bot")
@admin_only
def remove_bot(message):

    msg = bot.send_message(message.chat.id, "Send bot username (without @)")
    bot.register_next_step_handler(msg, confirm_remove_bot)

def confirm_remove_bot(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:
        return bot.send_message(message.chat.id, "❌ Bot not found")

    bots_collection.delete_one({"username": username})

    # 🔥 REMOVE USERS OF THIS BOT
    deleted = users_collection.delete_many({
        "$or": [
            {"bot": username},
            {"bot": f"@{username}"}
        ]
    })

    bot.send_message(
        message.chat.id,
        f"🗑 Bot Removed\n👥 Users Deleted: {deleted.deleted_count}"
    )

# ==============================
# TARGET BOT
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔍 See Target Bot")
@admin_only
def see_target(message):

    msg = bot.send_message(message.chat.id, "Send bot username")
    bot.register_next_step_handler(msg, show_target)

def show_target(message):

    username = message.text.replace("@","").strip()

    users = users_collection.count_documents({
        "$or": [
            {"bot": username},
            {"bot": f"@{username}"}
        ]
    })

    downloads = downloads_collection.count_documents({
        "bot": username
    })

    bot.send_message(
        message.chat.id,
        f"""🔍 BOT: @{username}

👥 Users: {users}
📥 Downloads: {downloads}
"""
    )

# ==============================
# TOP BOTS
# ==============================
@bot.message_handler(func=lambda m: m.text == "🏆 Top Bots")
@admin_only
def top_bots(message):

    ranking = []

    for b in bots_collection.find():

        username = b.get("username")

        downloads = downloads_collection.count_documents({
            "bot": username
        })

        users = users_collection.count_documents({
            "$or": [
                {"bot": username},
                {"bot": f"@{username}"}
            ]
        })

        ranking.append({
            "username": username,
            "downloads": downloads,
            "users": users
        })

    ranking = sorted(ranking, key=lambda x: x["downloads"], reverse=True)[:10]

    text = "🏆 TOP BOTS\n\n"

    for i, r in enumerate(ranking, 1):
        text += f"{i}. @{r['username']}\n👥 {r['users']} | 📥 {r['downloads']}\n\n"

    bot.send_message(message.chat.id, text)

# ==============================
# BAN / UNBAN BOT
# ==============================
@bot.message_handler(func=lambda m: m.text == "🚫 Ban Bot")
@admin_only
def ban_bot(message):

    msg = bot.send_message(message.chat.id, "Send bot username")
    bot.register_next_step_handler(msg, do_ban)

def do_ban(message):

    username = message.text.replace("@","").strip()

    result = bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": True}}
    )

    if result.modified_count:
        bot.send_message(message.chat.id, "🚫 Bot banned")
    else:
        bot.send_message(message.chat.id, "❌ Not found")

@bot.message_handler(func=lambda m: m.text == "✅ Unban Bot")
@admin_only
def unban_bot(message):

    msg = bot.send_message(message.chat.id, "Send bot username")
    bot.register_next_step_handler(msg, do_unban)

def do_unban(message):

    username = message.text.replace("@","").strip()

    result = bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": False}}
    )

    if result.modified_count:
        bot.send_message(message.chat.id, "✅ Bot unbanned")
    else:
        bot.send_message(message.chat.id, "❌ Not found")

# ==============================
# CHANNEL ADD
# ==============================
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
@admin_only
def add_channel(message):

    msg = bot.send_message(message.chat.id, "Send channel username (with @)")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):

    username = message.text.strip()

    if not username.startswith("@"):
        return bot.send_message(message.chat.id, "❌ Must start with @")

    channels_collection.update_one(
        {"username": username},
        {"$set": {"username": username, "active": True}},
        upsert=True
    )

    bot.send_message(message.chat.id, "✅ Channel added")

# ==============================
# CHANNEL LIST
# ==============================
@bot.message_handler(func=lambda m: m.text == "📡 Channels")
@admin_only
def list_channels(message):

    channels = list(channels_collection.find())

    if not channels:
        return bot.send_message(message.chat.id, "❌ No channels")

    text = "📡 CHANNELS\n\n"

    for ch in channels:
        status = "✅" if ch.get("active") else "❌"
        text += f"{ch['username']} → {status}\n"

    bot.send_message(message.chat.id, text)

# ==============================
# CLOSE CHANNELS
# ==============================
@bot.message_handler(func=lambda m: m.text == "❌ Close Channels")
@admin_only
def close_channels(message):

    channels_collection.update_many({}, {"$set": {"active": False}})

    bot.send_message(message.chat.id, "❌ All channels disabled")

# ==============================
# RECEIVE CONTROL
# ==============================
@bot.message_handler(func=lambda m: m.text == "📥 RECEIVE MESSAGE")
@admin_only
def enable_receive(message):

    system_collection.update_one(
        {"_id": "receiver"},
        {"$set": {"status": True}},
        upsert=True
    )

    bot.send_message(message.chat.id, "📥 RECEIVE ENABLED")

@bot.message_handler(func=lambda m: m.text == "❌ CLOSE RECEIVE")
@admin_only
def disable_receive(message):

    system_collection.update_one(
        {"_id": "receiver"},
        {"$set": {"status": False}},
        upsert=True
    )

    bot.send_message(message.chat.id, "❌ RECEIVE DISABLED")

    # ==============================
# MEDIA STATS
# ==============================
@bot.message_handler(func=lambda m: m.text == "📊 Media Stats")
@admin_only
def media_stats(message):

    photos = downloads_collection.count_documents({"type": "photo"})
    videos = downloads_collection.count_documents({"type": "video"})

    bot.send_message(
        message.chat.id,
        f"""📊 MEDIA STATS

🖼 Photos: {photos}
🎬 Videos: {videos}
"""
    )

# ==============================
# AUTO SAVE USERS (VERY IMPORTANT 💥)
# ==============================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def auto_save_users(message):
    try:
        # ❗ THIS MAKES BROADCAST WORK
        users_collection.update_one(
            {"user_id": message.from_user.id},
            {
                "$set": {
                    "user_id": message.from_user.id,
                    "username": message.from_user.username or "",
                    "bot": message.chat.username or ""  # fallback
                }
            },
            upsert=True
        )
    except Exception as e:
        print("Auto save error:", e)

# ==============================
# RECEIVE MEDIA TO ADMIN
# ==============================
@bot.message_handler(content_types=["photo","video"])
def receive_media(message):

    if message.from_user.id != ADMIN_ID:
        return

    if not is_receive_on():
        return

    if not receiver_bot:
        return

    try:

        caption = f"""📥 RECEIVED

👤 ID: <code>{message.from_user.id}</code>
📛 @{message.from_user.username or "None"}
"""

        if message.content_type == "photo":
            receiver_bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=caption
            )

        elif message.content_type == "video":
            receiver_bot.send_video(
                ADMIN_ID,
                message.video.file_id,
                caption=caption
            )

    except Exception as e:
        print("Receive error:", e)

# ==============================
# GLOBAL CLEAN USERS (AUTO FIX)
# ==============================
def clean_users():

    while True:
        try:
            for u in users_collection.find():
                if not u.get("user_id"):
                    users_collection.delete_one({"_id": u["_id"]})
        except Exception as e:
            print("Clean error:", e)

        time.sleep(300)

# ==============================
# HEARTBEAT (ANTI FREEZE)
# ==============================
def heartbeat():

    while True:
        try:
            print("💓 SYSTEM RUNNING...")
        except:
            pass
        time.sleep(30)

# ==============================
# START BACKGROUND TASKS
# ==============================
def start_tasks():
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=clean_users, daemon=True).start()

# ==============================
# MAIN RUN
# ==============================
def run_bot():

    print("🚀 ADMIN BOT STARTED SUCCESSFULLY")

    start_tasks()

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    run_bot()
