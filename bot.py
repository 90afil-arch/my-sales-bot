import logging
import os
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота (будет браться из переменной окружения)
TOKEN = os.environ.get('TOKEN', '8945217291:AAF4yJxvu-CrFL1xP0WBa3Y8J1TOQLyH5iE')

# Данные продуктов
PRODUCTS = {
    '1': {
        'id': '1',
        'name_ru': '4000 ₽ — 50 г',
        'name_en': '4000 ₽ — 50 g',
        'price': '4000 ₽',
        'weight': '50 г',
        'price_ru': '4000 ₽',
        'price_en': '4000 ₽',
        'old_price_ru': None,
        'old_price_en': None,
        'emoji': '👤'
    },
    '2': {
        'id': '2',
        'name_ru': '8000 ₽ — 100 г',
        'name_en': '8000 ₽ — 100 g',
        'price': '8000 ₽',
        'weight': '100 г',
        'price_ru': '8000 ₽',
        'price_en': '8000 ₽',
        'old_price_ru': '100 ₽',
        'old_price_en': '100 ₽',
        'emoji': '👤'
    },
    '3': {
        'id': '3',
        'name_ru': '12000 ₽ — 150 г',
        'name_en': '12000 ₽ — 150 g',
        'price': '12000 ₽',
        'weight': '150 г',
        'price_ru': '12000 ₽',
        'price_en': '12000 ₽',
        'old_price_ru': '150 ₽',
        'old_price_en': '150 ₽',
        'emoji': '👤'
    },
    '4': {
        'id': '4',
        'name_ru': '16000 ₽ — 200 г',
        'name_en': '16000 ₽ — 200 g',
        'price': '16000 ₽',
        'weight': '200 г',
        'price_ru': '16000 ₽',
        'price_en': '16000 ₽',
        'old_price_ru': '170 ₽',
        'old_price_en': '170 ₽',
        'emoji': '👤'
    }
}

# Хранилище для языков пользователей
user_languages = {}

# Flask-приложение для Render
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "I'm alive!", 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)

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
        text = "🛍️ *Добро пожаловать в наш магазин!*\n\nВыберите товар:"
    else:
        text = "🛍️ *Welcome to our store!*\n\nSelect a product:"
    
    keyboard = []
    for product_id, product in PRODUCTS.items():
        if lang == 'ru':
            label = f"{product['emoji']} {product['name_ru']}"
            if product['old_price_ru']:
                label += f"\n❌ {product['old_price_ru']} → {product['price_ru']}"
        else:
            label = f"{product['emoji']} {product['name_en']}"
            if product['old_price_en']:
                label += f"\n❌ {product['old_price_en']} → {product['price_en']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"product_{product_id}")])
    
    if lang == 'ru':
        keyboard.append([InlineKeyboardButton("📞 Связаться с менеджером", callback_data="contact")])
    else:
        keyboard.append([InlineKeyboardButton("📞 Contact manager", callback_data="contact")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def product_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    product_id = query.data.split('_')[1]
    product = PRODUCTS[product_id]
    
    if lang == 'ru':
        text = f"📦 *{product['name_ru']}*\n\n💰 Цена: {product['price_ru']}\n⚖️ Вес: {product['weight']}\n"
        if product['old_price_ru']:
            text += f"❌ Старая цена: {product['old_price_ru']}\n"
        text += "\nДля заказа нажмите кнопку ниже 👇"
    else:
        text = f"📦 *{product['name_en']}*\n\n💰 Price: {product['price_en']}\n⚖️ Weight: {product['weight']}\n"
        if product['old_price_en']:
            text += f"❌ Old price: {product['old_price_en']}\n"
        text += "\nTo order, click the button below 👇"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Заказать / Order", callback_data=f"order_{product_id}")],
        [InlineKeyboardButton("⬅️ Назад / Back", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    product_id = query.data.split('_')[1]
    product = PRODUCTS[product_id]
    
    if lang == 'ru':
        text = f"✅ *Заказ оформлен!*\n\nТовар: {product['name_ru']}\nЦена: {product['price_ru']}\n\n📞 Менеджер свяжется с вами!"
    else:
        text = f"✅ *Order placed!*\n\nProduct: {product['name_en']}\nPrice: {product['price_en']}\n\n📞 Manager will contact you!"
    
    keyboard = [[InlineKeyboardButton("⬅️ В меню / Back to menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    if lang == 'ru':
        text = "📞 *Связь с менеджером*\n\nНаш менеджер ответит на все вопросы:\n✉️ @your_manager"
    else:
        text = "📞 *Contact manager*\n\nOur manager will answer all questions:\n✉️ @your_manager"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад / Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    await show_main_menu(query, lang)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(product_details, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(order, pattern="^order_"))
    application.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    
    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()