import logging
import os
import threading
import asyncio
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise ValueError("Токен не найден!")

# ID менеджера
MANAGER_ID = 781584566

# Простой HTTP-сервер для Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 HTTP-сервер запущен на порту {port}")
    server.serve_forever()

# Данные продуктов
PRODUCTS = {
    '1': {
        'id': '1',
        'name_ru': '4000 просмотров — 50 gram coin',
        'name_en': '4000 views — 50 gram coin',
        'emoji': '📊'
    },
    '2': {
        'id': '2',
        'name_ru': '8000 просмотров — 90 gram coin',
        'name_en': '8000 views — 90 gram coin',
        'emoji': '📈'
    },
    '3': {
        'id': '3',
        'name_ru': '12000 просмотров — 130 gram coin',
        'name_en': '12000 views — 130 gram coin',
        'emoji': '📊'
    },
    '4': {
        'id': '4',
        'name_ru': '16000 просмотров — 160 gram coin',
        'name_en': '16000 views — 160 gram coin',
        'emoji': '📈'
    },
    '5': {
        'id': '5',
        'name_ru': '20000 просмотров — 200 gram coin',
        'name_en': '20000 views — 200 gram coin',
        'emoji': '⭐'
    }
}

# Хранилище для данных пользователей
user_data = {}
user_languages = {}

# TON адрес для оплаты
TON_ADDRESS = "UQDKekrnvm_kJyBAYypJXxmjYG6fxsHkUs7owH0_XyTY5HsR"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌍 Выберите язык / Choose language:",
        reply_markup=reply_markup
    )

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split('_')[1]
    user_languages[user_id] = lang
    await show_main_menu(query, lang)

async def show_main_menu(query, lang):
    if lang == 'ru':
        text = "🛍️ *Выберите услугу:*"
    else:
        text = "🛍️ *Select a service:*"
    
    keyboard = []
    for product_id, product in PRODUCTS.items():
        if lang == 'ru':
            label = f"{product['emoji']} {product['name_ru']}"
        else:
            label = f"{product['emoji']} {product['name_en']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"product_{product_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    product_id = query.data.split('_')[1]
    
    user_data[user_id] = {'product_id': product_id}
    
    if lang == 'ru':
        text = (
            "⚠️ *ПРЕДУПРЕЖДЕНИЕ:*\n\n"
            "Запрещается:\n"
            "• Вредоносные ссылки\n"
            "• Сайты с порнографией и видео 18+\n"
            "• Сайты, продающие наркотики, оружие или другие запретные материалы\n\n"
            "Каждая ссылка будет проверена вручную модераторами.\n"
            "Нарушающие правила ссылки не будут показаны в приложении.\n"
            "Оплата не будет возвращена.\n\n"
            "Вы согласны с условием?"
        )
    else:
        text = (
            "⚠️ *WARNING:*\n\n"
            "Prohibited:\n"
            "• Malicious links\n"
            "• Sites with pornography and 18+ video\n"
            "• Sites selling drugs, weapons or other prohibited materials\n\n"
            "Each link will be manually checked by moderators.\n"
            "Violating links will not be shown in the app.\n"
            "Payment will not be refunded.\n\n"
            "Do you agree to the terms?"
        )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да / Yes", callback_data=f"agree_{product_id}"),
            InlineKeyboardButton("❌ Нет / No", callback_data="disagree")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def agree_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    product_id = query.data.split('_')[1]
    product = PRODUCTS[product_id]
    
    if lang == 'ru':
        text = (
            f"💳 *Оплата*\n\n"
            f"Товар: {product['name_ru']}\n\n"
            f"Переведите оплату на TON адрес:\n"
            f"`{TON_ADDRESS}`\n\n"
            f"📌 *После оплаты:*\n"
            f"1️⃣ Нажмите кнопку '✅ Оплатил'\n"
            f"2️⃣ Пришлите ссылку на транзакцию (TON)\n"
            f"3️⃣ Пришлите ссылку для продвижения"
        )
    else:
        text = (
            f"💳 *Payment*\n\n"
            f"Product: {product['name_en']}\n\n"
            f"Send payment to TON address:\n"
            f"`{TON_ADDRESS}`\n\n"
            f"📌 *After payment:*\n"
            f"1️⃣ Press '✅ Paid'\n"
            f"2️⃣ Send transaction link (TON)\n"
            f"3️⃣ Send promotion link"
        )
    
    keyboard = [
        [InlineKeyboardButton("✅ Оплатил / Paid", callback_data="paid")],
        [InlineKeyboardButton("⬅️ Назад / Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_data[user_id]['step'] = 'waiting_payment'
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def disagree_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    if lang == 'ru':
        text = "❌ Диалог завершен. Если передумаете - нажмите /start"
    else:
        text = "❌ Dialog ended. If you change your mind - press /start"
    
    keyboard = [[InlineKeyboardButton("🔄 Начать / Start", callback_data="restart")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def paid_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    if lang == 'ru':
        text = (
            "📎 *Отправьте ссылку на транзакцию TON*\n\n"
            "Пример: https://tonscan.org/tx/...\n"
            "Или ссылку из кошелька TON\n\n"
            "ℹ️ Бот проверит, что ссылка ведет на сеть TON"
        )
    else:
        text = (
            "📎 *Send TON transaction link*\n\n"
            "Example: https://tonscan.org/tx/...\n"
            "Or link from TON wallet\n\n"
            "ℹ️ Bot will check that the link is on TON network"
        )
    
    user_data[user_id]['step'] = 'waiting_transaction'
    
    await query.edit_message_text(
        text=text,
        parse_mode='Markdown'
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    lang = user_languages.get(user_id, 'ru')
    
    if user_id not in user_data:
        await update.message.reply_text("Нажмите /start чтобы начать")
        return
    
    step = user_data[user_id].get('step')
    
    if step == 'waiting_transaction':
        if is_ton_link(text):
            user_data[user_id]['transaction_link'] = text
            user_data[user_id]['step'] = 'waiting_promotion'
            
            if lang == 'ru':
                await update.message.reply_text(
                    "✅ Ссылка на транзакцию принята!\n\n"
                    "📎 *Теперь отправьте ссылку для продвижения:*\n"
                    "Пример: https://t.me/your_channel/123\n"
                    "Или ссылку на сайт/видео"
                )
            else:
                await update.message.reply_text(
                    "✅ Transaction link accepted!\n\n"
                    "📎 *Now send promotion link:*\n"
                    "Example: https://t.me/your_channel/123\n"
                    "Or website/video link"
                )
        else:
            if lang == 'ru':
                await update.message.reply_text(
                    "❌ Это не похоже на ссылку TON.\n"
                    "Пожалуйста, отправьте ссылку на транзакцию в сети TON.\n"
                    "Пример: https://tonscan.org/tx/..."
                )
            else:
                await update.message.reply_text(
                    "❌ This doesn't look like a TON link.\n"
                    "Please send a TON network transaction link.\n"
                    "Example: https://tonscan.org/tx/..."
                )
    
    elif step == 'waiting_promotion':
        user_data[user_id]['promotion_link'] = text
        user_data[user_id]['step'] = 'completed'
        
        await send_notification_to_manager(context, user_id)
        
        if lang == 'ru':
            await update.message.reply_text(
                "✅ *Заявка отправлена на модерацию!*\n\n"
                "📋 Ваше продвижение будет опубликовано в течение 1-7 рабочих дней.\n\n"
                "Спасибо, что выбрали нас! 🙏"
            )
        else:
            await update.message.reply_text(
                "✅ *Application sent for moderation!*\n\n"
                "📋 Your promotion will be published within 1-7 business days.\n\n"
                "Thank you for choosing us! 🙏"
            )
        
        del user_data[user_id]

async def send_notification_to_manager(context, user_id):
    try:
        product_id = user_data[user_id].get('product_id')
        product = PRODUCTS.get(product_id, {})
        transaction_link = user_data[user_id].get('transaction_link', 'Не указана')
        promotion_link = user_data[user_id].get('promotion_link', 'Не указана')
        
        user = await context.bot.get_chat(user_id)
        username = user.username or "Нет username"
        full_name = user.full_name or "Неизвестно"
        
        message = (
            f"🆕 *НОВЫЙ ЗАКАЗ!*\n\n"
            f"👤 Пользователь: {full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📛 Username: @{username}\n"
            f"📦 Услуга: {product.get('name_ru', 'Неизвестно')}\n\n"
            f"🔗 Ссылка на транзакцию:\n{transaction_link}\n\n"
            f"🔗 Ссылка для продвижения:\n{promotion_link}\n\n"
            f"📅 Дата: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await context.bot.send_message(
            chat_id=MANAGER_ID,
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления менеджеру: {e}")

def is_ton_link(text: str) -> bool:
    ton_domains = [
        'tonscan.org',
        'tonviewer.com',
        'tonapi.io',
        'ton.org',
        'ton.cx',
        'ton.sh',
        'ton.dog',
        'ton.run',
        'ton.place'
    ]
    
    text_lower = text.lower()
    for domain in ton_domains:
        if domain in text_lower:
            return True
    
    if text_lower.startswith('http') and ('t.me/ton' in text_lower or 'ton' in text_lower):
        return True
    
    return False

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    if user_id in user_data:
        del user_data[user_id]
    
    await show_main_menu(query, lang)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await start(update, context)

def run_bot():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(product_selected, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(agree_terms, pattern="^agree_"))
    application.add_handler(CallbackQueryHandler(disagree_terms, pattern="^disagree$"))
    application.add_handler(CallbackQueryHandler(paid_button, pattern="^paid$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запускаем HTTP-сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Даем время серверу запуститься
    time.sleep(2)
    
    # Запускаем бота
    run_bot()