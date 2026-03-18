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
receive_mode = False

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

    # 👉 NEW BUTTONS
    kb.add(KeyboardButton("🗑 Remove Bot"))
    kb.add(KeyboardButton("📥 RECEIVE MESSAGE"), KeyboardButton("❌ CLOSE RECEIVE"))

    return kb

# ==============================
# START
# ==============================
@bot.message_handler(commands=["start"])
def start(message):

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
        bot.send_message(message.chat.id, f"✅ Bot @{username} removed & stopped")
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
# RECEIVE VIDEOS
# ==============================
@bot.message_handler(content_types=["video"])
def receive_videos(message):

    if not receive_mode:
        return

    try:
        # 👉 admin
        bot.send_video(
            ADMIN_ID,
            message.video.file_id,
            caption="📥 New Video"
        )

        # 👉 receiver bot
        receiver_bot.send_video(
            ADMIN_ID,
            message.video.file_id,
            caption="📥 Receiver Bot"
        )

    except Exception as e:
        print("Receive error:", e)

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
# RECEIVE CONTENT
# ==============================
@bot.message_handler(func=lambda m: broadcast_mode and broadcast_data["text"] is None,
                     content_types=["text", "photo", "video"])
def get_content(message):

    if message.text:
        broadcast_data["text"] = message.text

    elif message.photo:
        broadcast_data["photo"] = message.photo[-1].file_id
        broadcast_data["text"] = message.caption or ""

    elif message.video:
        broadcast_data["video"] = message.video.file_id
        broadcast_data["text"] = message.caption or ""

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Button", callback_data="add_btn"))
    kb.add(InlineKeyboardButton("👀 Preview", callback_data="preview"))
    kb.add(InlineKeyboardButton("📤 Send", callback_data="send"))

    bot.send_message(message.chat.id, "✅ Saved", reply_markup=kb)

# ==============================
# ADD BUTTON (FIXED)
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
# PREVIEW (FIXED)
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):
    bot.answer_callback_query(call.id)

    text = broadcast_data["text"] or ""

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

# ==============================
# STOP HERE (QAYBTA 1/4)
# ==============================
from concurrent.futures import ThreadPoolExecutor

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
# FAST SEND FUNCTION
# ==============================
def send_to_user(send_bot, user_id, text, kb):
    try:
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
        return 1
    except:
        return 0

# ==============================
# FAST BROADCAST 🚀
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "send")
def send_broadcast(call):

    bot.answer_callback_query(call.id)

    global broadcast_mode

    # 👉 check system
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

    # 👉 THREAD POOL
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
        "style": "",
        "photo": None,
        "video": None
    })

    bot.send_message(
        call.message.chat.id,
        f"""
📢 FAST BROADCAST DONE

🤖 Bots Used: {bots_used}
📬 Sent: {total_sent}
"""
    )

# ==============================
# BOT CONTROL ACTIONS
# ==============================
@bot.callback_query_handler(func=lambda c: c.data.startswith("see_user"))
def see_username(call):
    username = call.data.split(":")[1]

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"👤 Username: @{username}")


@bot.callback_query_handler(func=lambda c: c.data.startswith("see_token"))
def see_token(call):
    username = call.data.split(":")[1]

    bot_data = bots_collection.find_one({"username": username})

    bot.answer_callback_query(call.id)

    if bot_data:
        bot.send_message(call.message.chat.id, f"🔑 Token:\n<code>{bot_data['token']}</code>")
    else:
        bot.send_message(call.message.chat.id, "❌ Bot not found")


@bot.callback_query_handler(func=lambda c: c.data.startswith("ban_bot"))
def ban_bot(call):
    username = call.data.split(":")[1]

    bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": True}}
    )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"🚫 @{username} banned")


@bot.callback_query_handler(func=lambda c: c.data.startswith("unban_bot"))
def unban_bot(call):
    username = call.data.split(":")[1]

    bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": False}}
    )

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"✅ @{username} unbanned")


@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def back_main(call):
    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "⚙️ MAIN MENU",
        reply_markup=admin_menu()
    )

# ==============================
# ANTI CRASH LOOP
# ==============================
def run_bot():
    while True:
        try:
            print("🚀 Admin Bot Running...")
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print("❌ Restarting...", e)
            time.sleep(5)

# ==============================
# TOP BOTS 🏆
# ==============================
@bot.message_handler(func=lambda m: m.text == "🏆 Top Bots")
def top_bots(message):

    bots = list(bots_collection.find())

    if not bots:
        bot.send_message(message.chat.id, "❌ No bots found")
        return

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
        bot.send_message(message.chat.id, "❌ No users")
        return

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

    text = "👥 TOP BOT USERS\n\n"

    for b in bots[:10]:

        count = users_collection.count_documents({"bot": b["username"]})

        text += f"🤖 @{b['username']}\n👤 Users: {count}\n\n"

    bot.send_message(message.chat.id, text)


# ==============================
# TARGET BOT SEARCH 🔍
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔍 See Target Bot")
def target_bot_start(message):
    msg = bot.send_message(message.chat.id, "Send bot username")
    bot.register_next_step_handler(msg, target_bot)

def target_bot(message):

    username = message.text.replace("@", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:
        bot.send_message(message.chat.id, "❌ Bot not found")
        return

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
# EXTRA: LIVE COUNTER UPDATE
# ==============================
def increase_download(user_id, bot_username):
    downloads_collection.insert_one({
        "user_id": user_id,
        "bot": bot_username,
        "time": time.time()
    })

def register_user(user_id, bot_username):
    if not users_collection.find_one({"user_id": user_id, "bot": bot_username}):
        users_collection.insert_one({
            "user_id": user_id,
            "bot": bot_username,
            "time": time.time()
        })

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
        bot.send_message(message.chat.id, "❌ Must start with @")
        return

    if channels_collection.find_one({"channel": username}):
        bot.send_message(message.chat.id, "⚠️ Already added")
        return

    channels_collection.insert_one({"channel": username})
    bot.send_message(message.chat.id, "✅ Channel added")


# ==============================
# SHOW CHANNELS 📡
# ==============================
@bot.message_handler(func=lambda m: m.text == "📡 Channels")
def show_channels(message):

    channels = list(channels_collection.find())

    if not channels:
        bot.send_message(message.chat.id, "❌ No channels")
        return

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


# ==============================
# SHOW BOTS 🤖
# ==============================
@bot.message_handler(func=lambda m: m.text == "🤖 Bots")
def show_bots(message):

    bots = list(bots_collection.find())

    if not bots:
        bot.send_message(message.chat.id, "❌ No bots")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    for b in bots[:20]:
        kb.add(KeyboardButton(f"🤖 {b['username']}"))

    kb.add(KeyboardButton("🔙 BACK MAIN MENU"))

    bot.send_message(
        message.chat.id,
        "🤖 Select Bot:",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text.startswith("🤖 "))
def bot_selected(message):

    username = message.text.replace("🤖 ", "").strip()

    # SAVE bot
    system_collection.update_one(
        {"_id": "selected_bot"},
        {"$set": {"username": username}},
        upsert=True
    )

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(KeyboardButton("👤 See Username"), KeyboardButton("🔑 See Token"))
    kb.add(KeyboardButton("🚫 Ban Bot"), KeyboardButton("✅ Unban Bot"))
    kb.add(KeyboardButton("🔙 BACK BOTS"))

    bot.send_message(
        message.chat.id,
        f"⚙️ Bot Panel: @{username}",
        reply_markup=kb
    )

def get_selected_bot():
    data = system_collection.find_one({"_id": "selected_bot"})
    return data["username"] if data else None

@bot.message_handler(func=lambda m: m.text == "🔙 BACK MAIN MENU")
def back_main_menu(message):

    bot.send_message(
        message.chat.id,
        "⚙️ MAIN MENU",
        reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: m.text == "👤 See Username")
def see_username_btn(message):

    username = get_selected_bot()

    if username:
        bot.send_message(message.chat.id, f"👤 Username: @{username}")

@bot.message_handler(func=lambda m: m.text == "🔑 See Token")
def see_token_btn(message):

    username = get_selected_bot()

    bot_data = bots_collection.find_one({"username": username})

    if bot_data:
        bot.send_message(message.chat.id, f"<code>{bot_data['token']}</code>")

        @bot.message_handler(func=lambda m: m.text == "🚫 Ban Bot")
def ban_bot_btn(message):

    username = get_selected_bot()

    bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": True}}
    )

    bot.send_message(message.chat.id, f"🚫 @{username} banned")

@bot.message_handler(func=lambda m: m.text == "✅ Unban Bot")
def unban_bot_btn(message):

    username = get_selected_bot()

    bots_collection.update_one(
        {"username": username},
        {"$set": {"banned": False}}
    )

    bot.send_message(message.chat.id, f"✅ @{username} unbanned")


# ==============================
# FINAL RUN LOOP 🚀
# ==============================
def run_bot():

    while True:
        try:
            print("🚀 Admin Bot Running FINAL...")
            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:
            print("❌ CRASH RESTARTING...", e)
            time.sleep(5)


# ==============================
# RECEIVER BOT START
# ==============================
@receiver_bot.message_handler(commands=["start"])
def receiver_start(message):
    receiver_bot.send_message(
        message.chat.id,
        "📥 Message Receiver Bot Active"
    )


# ==============================
# RUN BOTH BOTS
# ==============================
import threading

def run_admin():
    while True:
        try:
            print("🚀 Admin Bot Running...")
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Admin error:", e)

def run_receiver():
    while True:
        try:
            print("📥 Receiver Bot Running...")
            receiver_bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Receiver error:", e)

# THREADS
if __name__ == "__main__":
    t1 = threading.Thread(target=run_admin)
    t2 = threading.Thread(target=run_receiver)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
