import logging
import os
import asyncio
import re
import time
import threading
from flask import Flask
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

# ID группы для заказов и поддержки
SUPPORT_GROUP_ID = -1003577549054

# Flask приложение
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

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

# Хранилище для поддержки
support_sessions = {}

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
        text = "🛍️ Выберите услугу:"
    else:
        text = "🛍️ Select a service:"
    
    keyboard = []
    for product_id, product in PRODUCTS.items():
        if lang == 'ru':
            label = f"{product['emoji']} {product['name_ru']}"
        else:
            label = f"{product['emoji']} {product['name_en']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"product_{product_id}")])
    
    # Добавляем кнопку "Связаться с поддержкой"
    if lang == 'ru':
        keyboard.append([InlineKeyboardButton("🆘 Связаться с поддержкой", callback_data="support")])
    else:
        keyboard.append([InlineKeyboardButton("🆘 Contact support", callback_data="support")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
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
            "⚠️ ПРЕДУПРЕЖДЕНИЕ:\n\n"
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
            "⚠️ WARNING:\n\n"
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
        reply_markup=reply_markup
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
            f"💳 Оплата\n\n"
            f"Товар: {product['name_ru']}\n\n"
            f"Переведите оплату на TON адрес:\n{TON_ADDRESS}\n\n"
            f"📌 После оплаты:\n"
            f"1️⃣ Нажмите кнопку '✅ Оплатил'\n"
            f"2️⃣ Пришлите ссылку на транзакцию (TON)\n"
            f"3️⃣ Пришлите ссылку для продвижения"
        )
    else:
        text = (
            f"💳 Payment\n\n"
            f"Product: {product['name_en']}\n\n"
            f"Send payment to TON address:\n{TON_ADDRESS}\n\n"
            f"📌 After payment:\n"
            f"1️⃣ Press '✅ Paid'\n"
            f"2️⃣ Send transaction link (TON)\n"
            f"3️⃣ Send promotion link"
        )
    
    keyboard = [
        [InlineKeyboardButton("✅ Оплатил / Paid", callback_data="paid")],
        [InlineKeyboardButton("⬅️ Назад / Back", callback_data="back_to_menu")],
        [InlineKeyboardButton("🆘 Помощь / Help", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_data[user_id]['step'] = 'waiting_payment'
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
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
        reply_markup=reply_markup
    )

async def paid_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    if lang == 'ru':
        text = (
            "📎 Отправьте ссылку на транзакцию TON\n\n"
            "Пример: https://tonscan.org/tx/...\n"
            "Или ссылку из кошелька TON\n\n"
            "Бот проверит, что ссылка ведет на сеть TON"
        )
    else:
        text = (
            "📎 Send TON transaction link\n\n"
            "Example: https://tonscan.org/tx/...\n"
            "Or link from TON wallet\n\n"
            "Bot will check that the link is on TON network"
        )
    
    user_data[user_id]['step'] = 'waiting_transaction'
    
    await query.edit_message_text(
        text=text
    )

async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 'Связаться с поддержкой'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    # Активируем сессию поддержки
    support_sessions[user_id] = True
    
    if lang == 'ru':
        text = (
            "🆘 Поддержка\n\n"
            "Вы можете задать любой вопрос в этом чате.\n"
            "Наш оператор свяжется с вами в ближайшее время.\n\n"
            "📌 Напишите ваше сообщение ниже.\n"
            "Для завершения диалога нажмите 'Завершить чат'."
        )
        keyboard = [[InlineKeyboardButton("❌ Завершить чат", callback_data="end_support")]]
    else:
        text = (
            "🆘 Support\n\n"
            "You can ask any question in this chat.\n"
            "Our operator will contact you shortly.\n\n"
            "📌 Write your message below.\n"
            "To end the conversation, press 'End chat'."
        )
        keyboard = [[InlineKeyboardButton("❌ End chat", callback_data="end_support")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )
    
    # Отправляем уведомление в группу поддержки (БЕЗ Markdown)
    user = await context.bot.get_chat(user_id)
    username = user.username or "Нет username"
    full_name = user.full_name or "Неизвестно"
    
    await context.bot.send_message(
        chat_id=SUPPORT_GROUP_ID,
        text=(
            f"🆕 НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ!\n\n"
            f"👤 Пользователь: {full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📛 Username: @{username}\n\n"
            f"💬 Напишите ответ на это сообщение, чтобы ответить пользователю.\n"
            f"Ваш ответ будет отправлен анонимно от имени бота."
        )
    )

async def end_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение сессии поддержки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = user_languages.get(user_id, 'ru')
    
    # Деактивируем сессию поддержки
    if user_id in support_sessions:
        del support_sessions[user_id]
    
    if lang == 'ru':
        text = "✅ Чат с поддержкой завершен. Если понадобится помощь - нажмите 'Связаться с поддержкой' в меню."
    else:
        text = "✅ Support chat ended. If you need help - press 'Contact support' in the menu."
    
    keyboard = [[InlineKeyboardButton("⬅️ В меню / Back to menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    lang = user_languages.get(user_id, 'ru')
    
    logging.info(f"📩 Получено сообщение от {user_id}: {text[:100]}")
    
    # Проверяем, не является ли это ответом оператора (из группы поддержки)
    if update.message.chat_id == SUPPORT_GROUP_ID:
        # Это сообщение из группы поддержки
        await handle_operator_reply(update, context)
        return
    
    # Проверяем, активна ли сессия поддержки
    if user_id in support_sessions and support_sessions[user_id]:
        # Пользователь в режиме поддержки - пересылаем оператору
        await forward_to_support(update, context)
        return
    
    # Обычный процесс заказа
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
                    "📎 Теперь отправьте ссылку для продвижения:\n"
                    "Пример: https://t.me/your_channel/123\n"
                    "Или ссылку на сайт/видео"
                )
            else:
                await update.message.reply_text(
                    "✅ Transaction link accepted!\n\n"
                    "📎 Now send promotion link:\n"
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
        
        logging.info(f"📦 Заказ от {user_id}: {user_data[user_id]}")
        
        # Отправляем уведомление в группу
        await send_notification_to_manager(context, user_id)
        
        # Формируем сообщение для пользователя
        if lang == 'ru':
            success_msg = (
                "✅ Заявка отправлена на модерацию!\n\n"
                "📋 Ваше продвижение будет опубликовано в течение 1-7 рабочих дней.\n\n"
                "Спасибо, что выбрали нас! 🙏"
            )
            # Проверяем, является ли ссылка на Telegram канал/группу
            if 't.me' in text or 'telegram' in text.lower():
                success_msg += (
                    "\n\n📌 Важное дополнение:\n"
                    "Если вы указали Telegram-канал или группу, добавьте бота @Marg_not_coin_bot "
                    "в свой канал/группу и сделайте его администратором (убрав все галочки). "
                    "Это необходимо для проверки выполнения задания."
                )
        else:
            success_msg = (
                "✅ Application sent for moderation!\n\n"
                "📋 Your promotion will be published within 1-7 business days.\n\n"
                "Thank you for choosing us! 🙏"
            )
            if 't.me' in text or 'telegram' in text.lower():
                success_msg += (
                    "\n\n📌 Important addition:\n"
                    "If you specified a Telegram channel or group, add bot @Marg_not_coin_bot "
                    "to your channel/group and make it an administrator (uncheck all checkboxes). "
                    "This is necessary to verify task completion."
                )
        
        await update.message.reply_text(success_msg)
        
        del user_data[user_id]

async def forward_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка сообщения от пользователя в группу поддержки"""
    user_id = update.effective_user.id
    text = update.message.text
    user = await context.bot.get_chat(user_id)
    username = user.username or "Нет username"
    full_name = user.full_name or "Неизвестно"
    
    # Отправляем сообщение в группу поддержки (БЕЗ Markdown)
    await context.bot.send_message(
        chat_id=SUPPORT_GROUP_ID,
        text=(
            f"💬 Сообщение от пользователя:\n\n"
            f"👤 {full_name} (@{username})\n"
            f"🆔 ID: {user_id}\n\n"
            f"📝 {text}\n\n"
            f"---\n"
            f"Чтобы ответить, просто напишите ответ на это сообщение\n"
            f"в этой группе. Бот перешлет его пользователю."
        )
    )
    
    # Подтверждение пользователю
    lang = user_languages.get(user_id, 'ru')
    if lang == 'ru':
        await update.message.reply_text("✅ Сообщение отправлено оператору. Ожидайте ответа.")
    else:
        await update.message.reply_text("✅ Message sent to operator. Please wait for response.")

async def handle_operator_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа оператора из группы поддержки"""
    # Проверяем, что это ответ на сообщение (reply)
    if not update.message.reply_to_message:
        return
    
    # Проверяем, что сообщение, на которое отвечают, отправлено ботом
    if update.message.reply_to_message.from_user.id != context.bot.id:
        return
    
    # Извлекаем ID пользователя из текста сообщения
    reply_text = update.message.reply_to_message.text or ""
    
    # Ищем ID пользователя в тексте
    import re
    match = re.search(r"🆔 ID: (\d+)", reply_text)
    if not match:
        await update.message.reply_text("❌ Не удалось определить пользователя. Сообщение должно содержать ID.")
        return
    
    user_id = int(match.group(1))
    operator_response = update.message.text
    
    # Отправляем ответ пользователю (БЕЗ Markdown)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💬 Оператор:\n\n{operator_response}"
        )
        
        # Подтверждение оператору
        await update.message.reply_text(f"✅ Ответ отправлен пользователю (ID: {user_id})")
        
        # Логируем
        logging.info(f"📨 Оператор ответил пользователю {user_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отправки: {e}")

async def send_notification_to_manager(context, user_id):
    """Отправка уведомления о заказе в группу"""
    try:
        logging.info(f"📨 Начинаем отправку уведомления в группу {SUPPORT_GROUP_ID}")
        
        product_id = user_data[user_id].get('product_id')
        product = PRODUCTS.get(product_id, {})
        transaction_link = user_data[user_id].get('transaction_link', 'Не указана')
        promotion_link = user_data[user_id].get('promotion_link', 'Не указана')
        
        # Получаем информацию о пользователе
        user = await context.bot.get_chat(user_id)
        username = user.username or "Нет username"
        full_name = user.full_name or "Неизвестно"
        
        # Сообщение (простой текст, без Markdown)
        message = (
            f"🆕 НОВЫЙ ЗАКАЗ!\n\n"
            f"👤 Пользователь: {full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📛 Username: @{username}\n"
            f"📦 Услуга: {product.get('name_ru', 'Неизвестно')}\n\n"
            f"🔗 Ссылка на транзакцию:\n{transaction_link}\n\n"
            f"🔗 Ссылка для продвижения:\n{promotion_link}\n\n"
            f"📅 Дата: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        # Отправляем в группу
        await context.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            text=message
        )
        
        logging.info(f"✅ Уведомление успешно отправлено в группу {SUPPORT_GROUP_ID}")
        
    except Exception as e:
        logging.error(f"❌ ОШИБКА отправки уведомления в группу: {e}")

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
    if user_id in support_sessions:
        del support_sessions[user_id]
    
    await start(update, context)

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(product_selected, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(agree_terms, pattern="^agree_"))
    application.add_handler(CallbackQueryHandler(disagree_terms, pattern="^disagree$"))
    application.add_handler(CallbackQueryHandler(paid_button, pattern="^paid$"))
    application.add_handler(CallbackQueryHandler(support_button, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(end_support, pattern="^end_support$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    
    # Обработчик текстовых сообщений (для всех чатов)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Веб-сервер запущен на порту {os.environ.get('PORT', 5000)}")
    
    # Даем время Flask запуститься
    time.sleep(2)
    
    # Запускаем бота
    main()