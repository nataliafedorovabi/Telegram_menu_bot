import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Этапы диалога
WEIGHT, HEIGHT, AGE, ACTIVITY, GOAL = range(5)

# Команда /start
async def start(update: Update, context: CallbackContext):
    logger.info(f"START: user_id={update.effective_user.id}")
    context.user_data.clear()
    keyboard = ReplyKeyboardMarkup([["Начать заново"]], resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Ответь на пару вопросов, чтобы подобрать меню именно под тебя 😊",
        reply_markup=keyboard
    )
    await update.message.reply_text("Введите ваш вес (в кг):")
    return WEIGHT

# Повторный старт при нажатии кнопки "Начать заново"
async def restart(update: Update, context: CallbackContext):
    logger.info(f"RESTART: user_id={update.effective_user.id}")
    context.user_data.clear()
    await update.message.reply_text(
        "Хорошо, начнем сначала! 😊",
        reply_markup=ReplyKeyboardMarkup([["Начать заново"]], resize_keyboard=True)
    )
    await update.message.reply_text("Введите ваш вес (в кг):")
    return WEIGHT

# Кнопка "Начать заново" в inline-режиме
async def restart_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    logger.info(f"RESTART (inline): user_id={query.from_user.id}")
    await query.answer()
    context.user_data.clear()
    keyboard = ReplyKeyboardMarkup([["Начать заново"]], resize_keyboard=True)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Привет! Ответь на пару вопросов, чтобы подобрать меню именно под тебя 😊",
        reply_markup=keyboard
    )
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Введите ваш вес (в кг):"
    )
    return WEIGHT

# Получение веса
async def get_weight(update: Update, context: CallbackContext):
    logger.info(f"WEIGHT: user_id={update.effective_user.id}, text={update.message.text}")
    try:
        context.user_data['weight'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш вес в кг):")
        return WEIGHT
    await update.message.reply_text("Введите ваш рост (в см):")
    return HEIGHT

# Получение роста
async def get_height(update: Update, context: CallbackContext):
    logger.info(f"HEIGHT: user_id={update.effective_user.id}, text={update.message.text}")
    try:
        context.user_data['height'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш рост в см):")
        return HEIGHT
    await update.message.reply_text("Введите ваш возраст:")
    return AGE

# Получение возраста
async def get_age(update: Update, context: CallbackContext):
    logger.info(f"AGE: user_id={update.effective_user.id}, text={update.message.text}")
    try:
        context.user_data['age'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш возраст):")
        return AGE

    # Удаляем клавиатуру
    await update.message.reply_text("Выберите уровень физической активности:", reply_markup=ReplyKeyboardRemove())

    keyboard = [
        [InlineKeyboardButton("1.2 - Минимальная", callback_data="1.2")],
        [InlineKeyboardButton("1.3 - Низкая", callback_data="1.3")],
        [InlineKeyboardButton("1.38 - Средняя", callback_data="1.38")],
        [InlineKeyboardButton("1.43 - Выше среднего", callback_data="1.43")],
        [InlineKeyboardButton("1.55 - Высокая", callback_data="1.55")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите уровень физической активности:", reply_markup=reply_markup)
    return ACTIVITY

# Уровень активности
async def get_activity(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['activity'] = float(query.data)
    logger.info(f"ACTIVITY: user_id={query.from_user.id}, data={query.data}")

    keyboard = [
        [
            InlineKeyboardButton("Похудеть", callback_data="Похудеть"),
            InlineKeyboardButton("Удерживать вес", callback_data="Удерживать вес")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Какова ваша цель?", reply_markup=reply_markup)
    return GOAL

# Цель
async def get_goal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    logger.info(f"GOAL: user_id={query.from_user.id}, data={query.data}")

    goal = query.data
    weight = context.user_data['weight']
    height = context.user_data['height']
    age = context.user_data['age']
    activity = context.user_data['activity']

    # Расчет калорий
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
        f"Вам подходит {calories} ккал в день. Нажмите кнопку ниже, чтобы подобрать меню:",
        reply_markup=button
    )

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Если хотите начать заново, нажмите кнопку ниже:",
        reply_markup=restart_inline
    )
    return ConversationHandler.END

# Завершение диалога
async def cancel(update: Update, context: CallbackContext):
    logger.info(f"CANCEL: user_id={update.effective_user.id}")
    await update.message.reply_text("Диалог завершен.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Основной запуск
def main():
    TOKEN = "1630388281:AAEm6i0PQOzDYWqE4Plpie5DmMuj4qWOgwk"  # 🔑 Вставь свой токен
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WEIGHT: [
                MessageHandler(filters.Regex(r"(?i)^начать\s+заново$"), restart),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)
            ],
            HEIGHT: [
                MessageHandler(filters.Regex(r"(?i)^начать\s+заново$"), restart),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)
            ],
            AGE: [
                MessageHandler(filters.Regex(r"(?i)^начать\s+заново$"), restart),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)
            ],
            ACTIVITY: [CallbackQueryHandler(get_activity)],
            GOAL: [
                CallbackQueryHandler(get_goal),
                CallbackQueryHandler(restart_callback, pattern="^restart$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(restart_callback, pattern="^restart$"))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 8443)),
        url_path=TOKEN,
        webhook_url=f"https://telegram-menu-bot-lqrj.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()
