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
        "Привет! Ответьте на пару вопросов, чтобы подобрать меню именно под вас 😊",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("Введите ваш вес (в кг):")
    return WEIGHT

# Обработка inline "Начать заново"
async def restart_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Начнем сначала! 😊 Введите ваш вес (в кг):"
    )
    return WEIGHT

# Получение веса
async def get_weight(update: Update, context: CallbackContext):
    try:
        context.user_data['weight'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш вес в кг):")
        return WEIGHT
    await update.message.reply_text("Введите ваш рост (в см):")
    return HEIGHT

# Получение роста
async def get_height(update: Update, context: CallbackContext):
    try:
        context.user_data['height'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш рост в см):")
        return HEIGHT
    await update.message.reply_text("Введите ваш возраст:")
    return AGE

# Получение возраста
async def get_age(update: Update, context: CallbackContext):
    try:
        context.user_data['age'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (ваш возраст):")
        return AGE

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

    # ДОБАВЛЕНО: Отправка файлов из соответствующей папки
    # ДОБАВЛЕНО: Отправка файлов из соответствующей папки
folder_path = f"menus/{calories}"
if os.path.exists(folder_path):
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Вам подходит {calories} ккал в день. Отправляю пробное меню на 7 дней:"
    )
    files_sent = 0
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            try:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=open(file_path, "rb")
                )
                files_sent += 1
                if files_sent >= 3:
                    break
            except Exception as e:
                logger.error(f"Ошибка при отправке файла {file_path}: {e}")
else:
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Извините, меню для данной калорийности пока недоступно."
    )

# ДОБАВЛЕНО: Отправка других одиночных файлов из папки menus/
menus_folder = "menus"
other_files_sent = 0
for item in os.listdir(menus_folder):
    file_path = os.path.join(menus_folder, item)
    if os.path.isfile(file_path):
        try:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=open(file_path, "rb")
            )
            other_files_sent += 1
            if other_files_sent >= 3:
                break
        except Exception as e:
            logger.error(f"Ошибка при отправке файла {file_path}: {e}")

# ДОБАВЛЕНО: Кнопка Купить
await context.bot.send_message(
    chat_id=query.message.chat_id,
    text="Меню на 30 дней можно купить нажав на кнопку ниже:",
    reply_markup=button
)

# Перенос кнопки "Начать заново"
await context.bot.send_message(
    chat_id=query.message.chat_id,
    text="Если хотите начать заново, нажмите кнопку ниже:",
    reply_markup=restart_inline
)

    return ConversationHandler.END
