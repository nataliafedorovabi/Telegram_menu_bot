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
