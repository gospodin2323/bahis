import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- GÜVENLİK BİLGİLERİNİ BU BÖLÜMDEN ALACAĞIZ ---
# ARTIK KODUN İÇİNE YAZMIYORUZ, HOSTİNG PLATFORMUNUN "SECRETS" VEYA "ENVIRONMENT VARIABLES" BÖLÜMÜNDEN ÇEKECEĞİZ
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# ID'yi integer'a (sayıya) çeviriyoruz
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID'))

# --- WEB SUNUCUSU KISMI (BOTU AKTİF TUTMAK İÇİN) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Aktif ve Çalışıyor."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- TELEGRAM BOT KISMI ---

# Olası hataları görmek için loglamayı aktif et
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Gemini API'sini yapılandır
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    logger.info("Gemini API başarıyla yapılandırıldı.")
except Exception as e:
    logger.error(f"Gemini API yapılandırma hatası: {e}")

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id == ALLOWED_USER_ID:
        welcome_message = "Merhaba! 7/24 aktif kişisel analiz asistanınız hizmetinizde. Komutunuzu bekliyorum."
        await update.message.reply_text(welcome_message)
    else:
        logger.warning(f"İzin verilmeyen kullanıcı denemesi: ID {user_id}")
        await update.message.reply_text("Üzgünüm, bu bot sadece sahibime özel olarak hizmet vermektedir.")

# Gelen mesajları işleyen fonksiyon
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id != ALLOWED_USER_ID:
        return

    user_text = update.message.text
    logger.info(f"Kullanıcıdan mesaj alındı: {user_text}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='TYPING')

    try:
        response = await model.generate_content_async(user_text)
        await update.message.reply_text(response.text, parse_mode='Markdown')
        logger.info("Cevap başarıyla gönderildi.")
    except Exception as e:
        logger.error(f"Mesaj işlenirken hata oluştu: {e}")
        await update.message.reply_text("Üzgünüm, analiz sırasında bir hata oluştu.")

def main() -> None:
    # Flask sunucusunu ayrı bir thread'de (iş parçacığı) başlat
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Telegram botunu kur ve başlat
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot başlatılıyor...")
    application.run_polling()

if __name__ == '__main__':
    main()