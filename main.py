# ================= MY BOTS =================

@bot.message_handler(func=lambda m: m.text == "🤖 My Bots")
def my_bots(message):

    try:

        bots = bots_collection.find({
            "owner": message.from_user.id,
            "active": True
        })

        text = "🤖 Your Bots\n\n"

        found = False

        for b in bots:

            username = b.get("username")

            if username:

                text += f"@{username}\n"
                found = True

        if not found:

            text = "❌ You don't have any bots yet"

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("My bots error:", e)


# ================= REMOVE BOT =================

@bot.message_handler(func=lambda m: m.text == "❌ Remove Bot")
def remove_bot(message):

    msg = bot.send_message(
        message.chat.id,
        "Send bot username to remove\nExample:\n@mybot"
    )

    bot.register_next_step_handler(
        msg,
        remove_bot_process
    )


def remove_bot_process(message):

    username = message.text.replace("@", "").strip()

    try:

        bot_data = bots_collection.find_one({"username": username})

        if not bot_data:

            bot.send_message(
                message.chat.id,
                "❌ Bot not found"
            )
            return

        if bot_data["owner"] != message.from_user.id:

            bot.send_message(
                message.chat.id,
                "❌ You are not owner of this bot"
            )
            return

        bots_collection.delete_one(
            {"username": username}
        )

        bot.send_message(
            message.chat.id,
            f"✅ @{username} removed from system"
        )

        print("Bot removed:", username)

    except Exception as e:

        print("Remove bot error:", e)


# ================= ADMIN STATS =================

@bot.message_handler(commands=["stats"])
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        total_users = users_collection.count_documents({})
        total_bots = bots_collection.count_documents({})

        text = f"""
📊 System Statistics

👤 Users: {total_users}
🤖 Bots: {total_bots}
"""

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as e:

        print("Stats error:", e)


# ================= VERIFY API =================

@app.route("/verify")
def verify():

    user_id = request.args.get("user_id")

    if not user_id:

        return jsonify({"status": "error"})

    try:

        active_channels = channels_collection.count_documents(
            {"active": True}
        )

        if active_channels == 0:

            return jsonify({"status": "joined"})


        not_joined = check_channels(user_id)

        if not not_joined:

            return jsonify({"status": "joined"})

        else:

            return jsonify({
                "status": "not_joined",
                "channels": not_joined
            })

    except Exception as e:

        print("Verify API error:", e)

        return jsonify({"status": "error"})


# ================= RUN MAIN BOT =================

def run_bot():

    while True:

        try:

            print("🤖 Main Verify Bot Running...")

            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )

        except Exception as e:

            print("Bot crashed:", e)

            time.sleep(5)


# ================= START RUNNER =================

def start_runner():

    try:

        import running

        print("🚀 Starting Multi Bot Runner")

        threading.Thread(
            target=running.start_runner,
            daemon=True
        ).start()

    except Exception as e:

        print("Runner start error:", e)


# ================= MAIN =================

if __name__ == "__main__":

    # start downloader bots runner
    start_runner()

    # start main bot
    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    # start web api
    port = int(os.environ.get("PORT", 5000))

    print("🌐 Web API Running on port", port)

    app.run(
        host="0.0.0.0",
        port=port
    )
