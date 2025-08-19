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

# Глобальный обработчик ошибок
async def error_handler(update: object, context: CallbackContext):
	logger.exception("Exception while handling an update: %s", context.error)

# Команда /start или Начать заново
async def start(update: Update, context: CallbackContext):
	context.user_data.clear()
	logger.info("/start: user_id=%s chat_id=%s", getattr(update.effective_user, "id", None), getattr(update.effective_chat, "id", None))
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
	logger.info("restart_callback: chat_id=%s", getattr(query.message.chat, "id", None))
	context.user_data.clear()
	await context.bot.send_message(
		chat_id=query.message.chat.id,
		text="Начнем сначала! 😊 Введите ваш вес (в кг):"
	)
	return WEIGHT

# Получение веса
async def get_weight(update: Update, context: CallbackContext):
	logger.info("get_weight: got text='%s' from chat_id=%s", getattr(update.message, "text", None), getattr(update.effective_chat, "id", None))
	try:
		# Разрешим числа с запятой/пробелами
		text = update.message.text.replace(",", ".").strip()
		weight_val = float(text)
		context.user_data['weight'] = int(round(weight_val))
	except Exception:
		await update.message.reply_text("Пожалуйста, введите число (ваш вес в кг):")
		return WEIGHT
	await update.message.reply_text("Введите ваш рост (в см):")
	return HEIGHT

# Получение роста
async def get_height(update: Update, context: CallbackContext):
	logger.info("get_height: got text='%s'", getattr(update.message, "text", None))
	try:
		text = update.message.text.replace(",", ".").strip()
		height_val = float(text)
		context.user_data['height'] = int(round(height_val))
	except Exception:
		await update.message.reply_text("Пожалуйста, введите число (ваш рост в см):")
		return HEIGHT
	await update.message.reply_text("Введите ваш возраст:")
	return AGE

# Получение возраста
async def get_age(update: Update, context: CallbackContext):
	logger.info("get_age: got text='%s'", getattr(update.message, "text", None))
	try:
		text = update.message.text.replace(",", ".").strip()
		age_val = float(text)
		context.user_data['age'] = int(round(age_val))
	except Exception:
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
	logger.info("get_activity: data=%s", query.data)
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
	logger.info("get_goal: data=%s", query.data)

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
	logger.info("calculated calories=%s", calories)

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
		chat_id=query.message.chat.id,
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
						chat_id=query.message.chat.id,
						document=open(file_path, "rb")
					)
					files_sent += 1
				except Exception as e:
					logger.error(f"Ошибка при отправке файла {file_path}: {e}")
	else:
		await context.bot.send_message(
			chat_id=query.message.chat.id,
			text="Извините, меню для данной калорийности пока недоступно."
		)
	menus_folder = "menus"
	other_files_sent = 0
	if os.path.exists(menus_folder):
		for item in os.listdir(menus_folder):
			file_path = os.path.join(menus_folder, item)
			if os.path.isfile(file_path):
				try:
					await context.bot.send_document(
						chat_id=query.message.chat.id,
						document=open(file_path, "rb")
					)
					other_files_sent += 1
					if other_files_sent >= 3:
						break
				except Exception as e:
					logger.error(f"Ошибка при отправке файла {file_path}: {e}")
	else:
		logger.warning("Папка 'menus' не найдена")
			
	await context.bot.send_message(
		chat_id=query.message.chat.id,
		text="Меню на 30 дней можно купить нажав на кнопку ниже:",
		reply_markup=button
	)
	
	await context.bot.send_message(
		chat_id=query.message.chat.id,
		text="Если хотите начать заново, нажмите кнопку ниже:",
		reply_markup=restart_inline
	)
	return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: CallbackContext):
	logger.info("cancel called")
	await update.message.reply_text("Диалог завершен.", reply_markup=ReplyKeyboardRemove())
	return ConversationHandler.END

# Запуск
def main():
	TOKEN = os.environ.get("TELEGRAM_TOKEN")
	if not TOKEN:
		logger.error("TELEGRAM_TOKEN environment variable not set!")
		return
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
		fallbacks=[
		CommandHandler("cancel", cancel),
		CommandHandler("start", start)  # добавлено, чтобы /start работал в любом состоянии
	],
	)

	app.add_handler(conv_handler)
	app.add_error_handler(error_handler)

	webhook_base_url = os.environ.get("WEBHOOK_BASE_URL")
	if webhook_base_url:
		webhook_url = webhook_base_url.rstrip("/") + f"/{TOKEN}"
		logger.info(f"Setting webhook to {webhook_url}")
		app.run_webhook(
			listen="0.0.0.0",
			port=int(os.environ.get('PORT', 8443)),
			url_path=TOKEN,
			webhook_url=webhook_url,
			allowed_updates=Update.ALL_TYPES,
		)
	else:
		logger.warning("WEBHOOK_BASE_URL is not set. Falling back to run_polling().")
		app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
	main()
