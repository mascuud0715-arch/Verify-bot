import telebot
import os
import random
import json

TOKEN = os.getenv("VERIFY_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

codes = {}

@bot.message_handler(commands=['start'])
def start(msg):

    code = random.randint(10000,99999)

    codes[msg.from_user.id] = code

    bot.send_message(
        msg.chat.id,
        f"🔐 Your Verify Code:\n\n{code}\n\nKu celi botkii ku waydiiyay verify."
    )

bot.infinity_polling()
