import json
import time
import telebot

running = {}

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return {}

while True:

    bots = load_bots()

    for token,data in bots.items():

        if token not in running:

            try:

                bot = telebot.TeleBot(token)

                @bot.message_handler(commands=['start'])
                def start(msg):

                    bot.send_message(
                        msg.chat.id,
                        "Welcome to verify system"
                    )

                import threading

                t = threading.Thread(
                    target=bot.infinity_polling
                )

                t.start()

                running[token] = True

                print("Bot started",data["username"])

            except:

                pass

    time.sleep(10)
