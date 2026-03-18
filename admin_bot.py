import telebot
import os
import time
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
RECEIVER_TOKEN = os.getenv("RECEIVER_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
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
# STATES
# ==============================
broadcast_mode = False

broadcast_data = {
    "text": None,
    "buttons": [],
    "photo": None,
    "video": None
}

# ==============================
# RECEIVE STATUS FIX
# ==============================
def is_receive_on():
    data = system_collection.find_one({"name": "receiver"})
    return True if not data else data.get("status", True)

# ==============================
# ADMIN MENU
# ==============================
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("📊 Stats","📊 Media Stats")
    kb.add("🤖 Bots")
    kb.add("📢 Broadcast")
    kb.add("➕ Add Channel","📡 Channels")
    kb.add("❌ Close Channels")
    kb.add("🚫 Close Bots","✅ Open Bots")
    kb.add("🟢 Verify ON","🔴 Verify OFF")
    kb.add("🔄 Refresh Bots")
    kb.add("🏆 Top Bots")
    kb.add("👥 Top Bot Users","👑 Top Users")
    kb.add("🔍 See Target Bot")
    kb.add("🗑 Remove Bot")
    kb.add("📥 RECEIVE MESSAGE","❌ CLOSE RECEIVE")

    return kb

# ==============================
# START
# ==============================
@bot.message_handler(commands=["start"])
def start(message):

    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Not Allowed")

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
# REMOVE BOT
# ==============================
@bot.message_handler(func=lambda m: m.text == "🗑 Remove Bot")
def remove_bot_start(message):
    msg = bot.send_message(message.chat.id, "Send Bot Username (without @)")
    bot.register_next_step_handler(msg, remove_bot)

def remove_bot(message):

    username = message.text.replace("@", "").strip()
    result = bots_collection.delete_one({"username": username})

    if result.deleted_count > 0:
        bot.send_message(message.chat.id, f"✅ Bot @{username} removed")
    else:
        bot.send_message(message.chat.id, "❌ Bot not found")

# ==============================
# RECEIVE MODE ON
# ==============================
@bot.message_handler(func=lambda m: m.text == "📥 RECEIVE MESSAGE")
def receive_on(message):

    system_collection.update_one(
        {"name": "receiver"},
        {"$set": {"status": True}},
        upsert=True
    )

    bot.send_message(message.chat.id, "✅ RECEIVE MODE ON")

# ==============================
# RECEIVE MODE OFF
# ==============================
@bot.message_handler(func=lambda m: m.text == "❌ CLOSE RECEIVE")
def receive_off(message):

    system_collection.update_one(
        {"name": "receiver"},
        {"$set": {"status": False}},
        upsert=True
    )

    bot.send_message(message.chat.id, "❌ RECEIVE MODE OFF")

# ==============================
# RECEIVE MEDIA (FIXED CLEAN)
# ==============================
@bot.message_handler(content_types=["video", "photo"])
def receive_media(message):

    if message.from_user.id != ADMIN_ID:
        return

    if not is_receive_on():
        return

    try:
        caption = f"""
📥 NEW MEDIA

👤 ID: <code>{message.from_user.id}</code>
📛 USERNAME: @{message.from_user.username or "None"}
"""

        if message.content_type == "video":
            bot.send_video(ADMIN_ID, message.video.file_id, caption=caption)
        else:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption)

    except Exception as e:
        print("Receive error:", e)

# ==============================
# BROADCAST START
# ==============================
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):

    global broadcast_mode

    broadcast_mode = True

    broadcast_data.update({
        "text": None,
        "buttons": [],
        "photo": None,
        "video": None
    })

    bot.send_message(
        message.chat.id,
        "📢 Send:\n\nText / Photo / Video"
    )

# ==============================
# GET CONTENT (FIXED)
# ==============================
@bot.message_handler(content_types=["text","photo","video"])
def get_content(message):

    global broadcast_mode

    if not broadcast_mode:
        return

    if message.content_type == "text":
        broadcast_data["text"] = message.text

    elif message.content_type == "photo":
        broadcast_data["photo"] = message.photo[-1].file_id
        broadcast_data["text"] = message.caption or ""

    elif message.content_type == "video":
        broadcast_data["video"] = message.video.file_id
        broadcast_data["text"] = message.caption or ""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Button", callback_data="add_btn"))
    kb.add(InlineKeyboardButton("👀 Preview", callback_data="preview"))
    kb.add(InlineKeyboardButton("📤 Send", callback_data="send"))

    bot.send_message(message.chat.id, "✅ Saved", reply_markup=kb)

from concurrent.futures import ThreadPoolExecutor

# ==============================
# ADD BUTTON
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "add_btn")
def add_btn(call):
    bot.answer_callback_query(call.id)

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
# PREVIEW (CAPTION CLEAN FIX)
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):
    bot.answer_callback_query(call.id)

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    try:
        # 👉 NO EXTRA MESSAGE / CLEAN CAPTION
        if broadcast_data["video"]:
            bot.send_video(
                call.message.chat.id,
                broadcast_data["video"],
                caption=text,
                reply_markup=kb
            )

        elif broadcast_data["photo"]:
            bot.send_photo(
                call.message.chat.id,
                broadcast_data["photo"],
                caption=text,
                reply_markup=kb
            )

        else:
            bot.send_message(
                call.message.chat.id,
                text,
                reply_markup=kb
            )

    except Exception as e:
        print("Preview error:", e)

# ==============================
# SYSTEM STATUS
# ==============================
def get_system():
    data = system_collection.find_one({"_id": "system"})

    if not data:
        system_collection.insert_one({
            "_id": "system",
            "bots_active": True
        })
        return {"bots_active": True}

    return data

def set_bots_status(status: bool):
    system_collection.update_one(
        {"_id": "system"},
        {"$set": {"bots_active": status}},
        upsert=True
    )

# ==============================
# CLOSE BOTS
# ==============================
@bot.message_handler(func=lambda m: m.text == "🚫 Close Bots")
def close_bots(message):
    set_bots_status(False)
    bot.send_message(message.chat.id, "🚫 All bots stopped")

# ==============================
# OPEN BOTS
# ==============================
@bot.message_handler(func=lambda m: m.text == "✅ Open Bots")
def open_bots(message):
    set_bots_status(True)
    bot.send_message(message.chat.id, "✅ All bots active")

# ==============================
# REFRESH BOTS
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔄 Refresh Bots")
def refresh_bots(message):

    bots = list(bots_collection.find())
    removed = 0

    for b in bots:
        try:
            test_bot = telebot.TeleBot(b["token"])
            test_bot.get_me()
        except:
            bots_collection.delete_one({"_id": b["_id"]})
            removed += 1

    bot.send_message(
        message.chat.id,
        f"🔄 Refresh Done\n❌ Removed: {removed}"
    )

# ==============================
# SEND FUNCTION (FAST)
# ==============================
def send_to_user(send_bot, user_id, text, kb):
    try:

        if broadcast_data["video"]:
            send_bot.send_video(
                chat_id=user_id,
                video=broadcast_data["video"],
                caption=text or "",
                reply_markup=kb
            )

        elif broadcast_data["photo"]:
            send_bot.send_photo(
                chat_id=user_id,
                photo=broadcast_data["photo"],
                caption=text or "",
                reply_markup=kb
            )

        else:
            send_bot.send_message(
                chat_id=user_id,
                text=text or "",
                reply_markup=kb
            )

        return 1

    except Exception as e:
        print(f"Send error to {user_id}: {e}")
        return 0

# ==============================
# FAST BROADCAST 🚀
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "send")
def send_broadcast(call):

    bot.answer_callback_query(call.id)

    global broadcast_mode

    # 👉 system check
    system = get_system()
    if not system.get("bots_active"):
        bot.send_message(call.message.chat.id, "🚫 Bots are CLOSED")
        return

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    bots = list(bots_collection.find())

    total_sent = 0
    bots_used = 0

    # 🚀 THREAD SPEED
    with ThreadPoolExecutor(max_workers=20) as executor:

        futures = []

        for b in bots:
            try:
                send_bot = telebot.TeleBot(b["token"])
                bots_used += 1

                users = list(users_collection.find())

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
                            kb
                        )
                    )

            except Exception as e:
                print("BOT ERROR:", e)

        for f in futures:
            total_sent += f.result()

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
📬 Sent: {total_sent}
"""
    )

# ==============================
# TOP BOTS 🏆
# ==============================
@bot.message_handler(func=lambda m: m.text == "🏆 Top Bots")
def top_bots(message):

    bots = list(bots_collection.find())

    if not bots:
        return bot.send_message(message.chat.id, "❌ No bots found")

    ranking = []

    for b in bots:
        users_count = users_collection.count_documents({"bot": b["username"]})
        downloads = downloads_collection.count_documents({"bot": b["username"]})

        score = users_count + downloads

        ranking.append({
            "username": b["username"],
            "score": score,
            "users": users_count,
            "downloads": downloads
        })

    ranking = sorted(ranking, key=lambda x: x["score"], reverse=True)[:10]

    text = "🏆 TOP BOTS\n\n"

    for i, r in enumerate(ranking, 1):
        text += f"{i}. @{r['username']}\n👤 {r['users']} | 📥 {r['downloads']}\n\n"

    bot.send_message(message.chat.id, text)


# ==============================
# TOP USERS 👑
# ==============================
@bot.message_handler(func=lambda m: m.text == "👑 Top Users")
def top_users(message):

    users = list(users_collection.find())

    if not users:
        return bot.send_message(message.chat.id, "❌ No users")

    ranking = []

    for u in users:
        downloads = downloads_collection.count_documents({"user_id": u["user_id"]})

        ranking.append({
            "id": u["user_id"],
            "downloads": downloads
        })

    ranking = sorted(ranking, key=lambda x: x["downloads"], reverse=True)[:10]

    text = "👑 TOP USERS\n\n"

    for i, r in enumerate(ranking, 1):
        text += f"{i}. <code>{r['id']}</code>\n📥 {r['downloads']}\n\n"

    bot.send_message(message.chat.id, text)


# ==============================
# TOP BOT USERS 👥
# ==============================
@bot.message_handler(func=lambda m: m.text == "👥 Top Bot Users")
def top_bot_users(message):

    bots = list(bots_collection.find())

    if not bots:
        return bot.send_message(message.chat.id, "❌ No bots")

    text = "👥 TOP BOT USERS\n\n"

    for b in bots[:10]:
        count = users_collection.count_documents({"bot": b["username"]})
        text += f"🤖 @{b['username']}\n👤 Users: {count}\n\n"

    bot.send_message(message.chat.id, text)


# ==============================
# TARGET BOT 🔍
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔍 See Target Bot")
def target_bot_start(message):
    msg = bot.send_message(message.chat.id, "Send bot username")
    bot.register_next_step_handler(msg, target_bot)

def target_bot(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:
        return bot.send_message(message.chat.id, "❌ Bot not found")

    users = users_collection.count_documents({"bot": username})
    downloads = downloads_collection.count_documents({"bot": username})

    bot.send_message(
        message.chat.id,
        f"""
🔍 BOT INFO

🤖 Username: @{username}
👤 Users: {users}
📥 Downloads: {downloads}
"""
    )


# ==============================
# ADD CHANNEL ➕
# ==============================
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel_start(message):
    msg = bot.send_message(message.chat.id, "Send Channel Username (with @)")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):

    username = message.text.strip()

    if not username.startswith("@"):
        return bot.send_message(message.chat.id, "❌ Must start with @")

    if channels_collection.find_one({"channel": username}):
        return bot.send_message(message.chat.id, "⚠️ Already added")

    channels_collection.insert_one({"channel": username})
    bot.send_message(message.chat.id, "✅ Channel added")


# ==============================
# SHOW CHANNELS 📡
# ==============================
@bot.message_handler(func=lambda m: m.text == "📡 Channels")
def show_channels(message):

    channels = list(channels_collection.find())

    if not channels:
        return bot.send_message(message.chat.id, "❌ No channels")

    text = "📡 CHANNELS LIST\n\n"

    for c in channels:
        text += f"{c['channel']}\n"

    bot.send_message(message.chat.id, text)


# ==============================
# CLOSE CHANNELS ❌
# ==============================
@bot.message_handler(func=lambda m: m.text == "❌ Close Channels")
def close_channels(message):

    channels_collection.delete_many({})
    bot.send_message(message.chat.id, "❌ All channels removed")


# ==============================
# VERIFY SYSTEM
# ==============================
def set_verify(status: bool):
    system_collection.update_one(
        {"_id": "verify"},
        {"$set": {"status": status}},
        upsert=True
    )

def get_verify():
    data = system_collection.find_one({"_id": "verify"})
    return data["status"] if data else True


# ==============================
# VERIFY ON 🟢
# ==============================
@bot.message_handler(func=lambda m: m.text == "🟢 Verify ON")
def verify_on(message):
    set_verify(True)
    bot.send_message(message.chat.id, "🟢 Verification Enabled")


# ==============================
# VERIFY OFF 🔴
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔴 Verify OFF")
def verify_off(message):
    set_verify(False)
    bot.send_message(message.chat.id, "🔴 Verification Disabled")

