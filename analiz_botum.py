import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- GÜVENLİK BİLGİLERİ (DEĞİŞİKLİK YOK) ---
# KODUN İÇİNE YAZMIYORUZ, HOSTİNG PLATFORMUNUN "ENVIRONMENT VARIABLES" BÖLÜMÜNDEN ÇEKECEĞİZ
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# ID'yi integer'a (sayıya) çeviriyoruz
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID'))

# --- WEB SUNUCUSU KISMI (BOTU AKTİF TUTMAK İÇİN) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Komut Tabanlı Bot Aktif ve Çalışıyor."
def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- TELEGRAM BOT KISMI ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Gemini API Yapılandırması
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    logger.info("Gemini API başarıyla yapılandırıldı.")
except Exception as e:
    logger.error(f"Gemini API yapılandırma hatası: {e}")
    
async def send_gemini_request(prompt: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gemini'ye istek gönderen ve cevabı Telegram'a yollayan merkezi fonksiyon"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='TYPING')
    try:
        response = await model.generate_content_async(prompt)
        await update.message.reply_text(response.text, parse_mode='Markdown')
        logger.info("Cevap başarıyla gönderildi.")
    except Exception as e:
        logger.error(f"Mesaj işlenirken hata oluştu: {e}")
        await update.message.reply_text("Üzgünüm, analiz sırasında bir hata oluştu.")

# --- KOMUT FONKSİYONLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id == ALLOWED_USER_ID:
        welcome_message = "Merhaba! Komut tabanlı analiz asistanınız hizmetinizde. Mevcut komutları görmek için /yardim yazabilirsiniz."
        await update.message.reply_text(welcome_message)

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    *Kullanılabilir Komutlar:*

    `/yardim` - Bu yardım menüsünü gösterir.

    `/fikstur <lig_kodu>` - Ligin haftalık fikstürünü getirir.
    *Örnek:* `/fikstur pl`

    `/analiz` veya `/tahmin <takim1> vs <takim2>` - Maç analizi/tahmini yapar.
    *Örnek:* `/tahmin manchesterunited liverpool`

    `/form <takim_adi>` - Takımın son 5 maçlık formunu gösterir.
    *Örnek:* `/form fenerbahce`
    
    `/puan <lig_kodu>` - Ligin puan durumunu gösterir.
    *Örnek:* `/puan tsl`

    *Lig Kodları:* `tsl`, `pl`, `ll`, `bl`, `sa`, `l1`, `ere`, `ppl`
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def fikstur(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Lütfen bir lig kodu belirtin. Örnek: `/fikstur pl`")
        return
    lig_kodu = context.args[0].lower()
    prompt = f"{lig_kodu} liginin güncel hafta fikstürünü, maçların gün ve saatleriyle birlikte listele."
    await send_gemini_request(prompt, update, context)

async def analiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Lütfen analiz için iki takım belirtin. Örnek: `/tahmin realmadrid barcelona`")
        return
    mac_sorgusu = " ".join(context.args)
    prompt = f"Sıradaki {mac_sorgusu} maçı için detaylı bir analiz yap. Analizde takımların güncel form durumları, sakat/cezalı oyuncuları, aralarındaki geçmiş maç sonuçları (son 5 maç), muhtemel taktikleri ve istatistiklere dayalı maç sonucu tahminini (yüzdelerle) belirt."
    await send_gemini_request(prompt, update, context)

async def form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Lütfen bir takım adı belirtin. Örnek: `/form galatasaray`")
        return
    takim_adi = " ".join(context.args)
    prompt = f"{takim_adi} takımının oynadığı son 5 resmi maçın (tüm kulvarlarda) sonuçlarını, skorlarını ve genel performansını özetle."
    await send_gemini_request(prompt, update, context)

async def puan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Lütfen bir lig kodu belirtin. Örnek: `/puan tsl`")
        return
    lig_kodu = context.args[0].lower()
    prompt = f"{lig_kodu} liginin güncel puan durumunu detaylı bir tablo halinde göster."
    await send_gemini_request(prompt, update, context)

async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    prompt = f"Bir