import telebot
import json
import threading
import time

running = {}

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []

def start_bot(token):

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start(msg):
        bot.send_message(msg.chat.id,"Bot Working ✅")

    print("Started bot:",token)

    bot.infinity_polling()

def run_thread(token):

    if token in running:
        return

    t = threading.Thread(target=start_bot,args=(token,))
    t.start()

    running[token] = True

while True:

    bots = load_bots()

    for b in bots:

        token = b["token"]

        run_thread(token)

    time.sleep(15)
