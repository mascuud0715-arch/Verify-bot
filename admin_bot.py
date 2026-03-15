import telebot
import os
import json

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

def load_bots():
    try:
        with open("bots.json") as f:
            return json.load(f)
    except:
        return []

@bot.message_handler(commands=["start"])
def admin(message):

    if message.from_user.id != ADMIN_ID:
        return

    bots = load_bots()

    bot.send_message(
        message.chat.id,
        f"🤖 Total Bots: {len(bots)}"
    )

bot.infinity_polling()
