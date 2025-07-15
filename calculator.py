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
    folder_path = f"menus/{calories}"
    if os.path.exists(folder_path):
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Вам подходит {calories} ккал в день. Отправляю пробное меню на 7 дней:"
        )
        files_sent = 0
        for filename in os.listdir(folder_path):
            if files_sent >= 3:
                break
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=open(file_path, "rb")
                    )
                    files_sent += 1
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла {file_path}: {e}")
    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Извините, меню для данной калорийности пока недоступно."
        )

    # Перенос блока "Купить" после файлов
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Меню на 30 дней можно купить нажав на кнопку ниже:",
        reply_markup=button
    )

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Если хотите начать заново, нажмите кнопку ниже:",
        reply_markup=restart_inline
    )
    return ConversationHandler.END
