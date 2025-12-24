import os
import logging
from flask import Flask
import threading
from telegram.ext import Application

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8495725535:AAFEfTgqtnB1F5Qn5vdreDd6Z6JpTBDaHKg')

flask_app = Flask(__name__)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

@flask_app.route('/')
def home():
    return "✅ بات تلگرام روی Render در حال اجراست!"

def run_bot():
    print("🤖 شروع بات تلگرام...")
    telegram_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)
