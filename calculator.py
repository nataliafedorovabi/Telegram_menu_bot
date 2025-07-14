import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEIGHT, HEIGHT, AGE, ACTIVITY, GOAL = range(5)

# Команда /start или Начать заново
async def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Ответь на пару вопросов, чтобы подобрать меню именно под тебя 😊",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("Введи свой вес (в кг):")
    return WEIGHT

# Обработка inline "Начать заново"
async def restart_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Начнем сначала! 😊 Введи свой вес (в кг):"
    )
    return WEIGHT

# Получение веса
async def get_weight(update: Update, context: CallbackContext):
    try:
        context.user_data['weight'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число (твой вес в кг):")
        return WEIGHT
    await update.message.reply_text("Введи свой рост (в см):")
    return HEIGHT

# Получение роста
async def get_height(update: Update, context: CallbackContext):
    try:
        context.user_data['height'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число (твой рост в см):")
        return HEIGHT
    await update.message.reply_text("Введи свой возраст:")
    return AGE

# Получение возраста
async def get_age(update: Update, context: CallbackContext):
    try:
        context.user_data['age'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число (твой возраст):")
        return AGE

    keyboard = [
        [InlineKeyboardButton("1.2 - Минимальная", callback_data="1.2")],
        [InlineKeyboardButton("1.3 - Низкая", callback_data="1.3")],
        [InlineKeyboardButton("1.38 - Средняя", callback_data="1.38")],
        [InlineKeyboardButton("1.43 - Выше среднего", callback_data="1.43")],
        [InlineKeyboardButton("1.55 - Высокая", callback_data="1.55")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери уровень физической активности:", reply_markup=reply_markup)
    return ACTIVITY

# Обработка активности
async def get_activity(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['activity'] = float(query.data)

    keyboard = [
        [
            InlineKeyboardButton("Похудеть", callback_data="Похудеть"),
            InlineKeyboardButton("Удерживать вес", callback_data="Удерживать вес")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Какова ваша цель?", reply_markup=reply_markup)
    return GOAL

# Обработка цели
async def get_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    goal = query.data
    weight = context.user_data['weight']
    height = context.user_data['height']
    age = context.user_data['age']
    activity = context.user_data['activity']

    base_cal = (655.1 + (9.563 * weight) + (2.35 * height) - (4.676 * age)) * activity
    if goal.lower() == "похудеть":
        base_cal *= 0.75

    calories = int(round(base_cal / 100) * 100)
    calories = max(1100, min(1900, calories))

    buy_url = f"https://orlowa.ru/calculator/{calories}"
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Купить", url=buy_url)]
    ])
    restart_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")]
    ])

    await query.edit_message_text(
        f"Тебе подходит {calories} ккал в день. Нажми кнопку ниже, чтобы скачать меню:",
        reply_markup=button
    )

    # Отправка 3 файлов из соответствующей папки
    folder_path = os.path.join("Telegram_menu_bot", "menus", str(calories))
    if os.path.isdir(folder_path):
        files = sorted(os.listdir(folder_path))[:3]
        for file_name in files:
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    await context.bot.send_document(chat_id=query.message.chat_id, document=f)
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Меню не найдено для вашей калорийности 😢")

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Если хочешь начать заново, нажми кнопку ниже:",
        reply_markup=restart_inline
    )
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Диалог завершен.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Запуск
def main():
    TOKEN = "1630388281:AAEm6i0PQOzDYWqE4Plpie5DmMuj4qWOgwk"  # ← Вставь сюда токен своего бота
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(restart_callback, pattern="^restart$")
        ],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            ACTIVITY: [CallbackQueryHandler(get_activity)],
            GOAL: [CallbackQueryHandler(get_goal)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 8443)),
        url_path=TOKEN,
        webhook_url=f"https://your-server.com/{TOKEN}"  # Заменить на свой адрес
    )

if __name__ == "__main__":
    main()
