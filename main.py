import telebot
import json
import os

TOKEN = os.getenv("MAIN_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []

def save_bots(data):
    with open("bots.json","w") as f:
        json.dump(data,f)

user_state = {}

@bot.message_handler(commands=["start"])
def start(message):

    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Add Bot","My Bots")

    bot.send_message(
        message.chat.id,
        "Welcome to Verify System",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text=="Add Bot")
def addbot(message):

    user_state[message.from_user.id] = "token"

    bot.send_message(
        message.chat.id,
        "Send Bot API Token"
    )

@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def get_token(message):

    token = message.text

    bots = load_bots()

    bots.append({
        "owner":message.from_user.id,
        "token":token
    })

    save_bots(bots)

    del user_state[message.from_user.id]

    bot.send_message(
        message.chat.id,
        "✅ Bot Added Successfully"
    )

@bot.message_handler(func=lambda m: m.text=="My Bots")
def mybots(message):

    bots = load_bots()

    text=""

    for b in bots:
        if b["owner"]==message.from_user.id:
            text += b["token"]+"\n"

    if text=="":
        text="No bots"

    bot.send_message(message.chat.id,text)

bot.infinity_polling()
