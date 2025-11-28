from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import MathProblemsDB
from config.settings import Config

# Инициализация базы данных
db = MathProblemsDB(Config.DB_PATH)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start и показывает главное меню"""
    user = update.effective_user

    welcome_text = f"""
👋 Привет, {user.first_name}!

🤖 Я - математический бот для 6 класса. 
Я помогу тебе решать задачи и улучшать свои навыки!

📚 **Что я умею:**
• 📂 Показывать задачи по разделам
• 🎲 Выдавать случайные задачи  
• 🔍 Искать задачи по ключевым словам
• 📝 Проверять знания в тестовом режиме
• 📊 Вести статистику твоих успехов

Выбери действие из меню ниже:
    """

    # Создаем клавиатуру главного меню
    keyboard = [
        [InlineKeyboardButton("📂 Разделы с задачами",
                              callback_data="sections")],
        [
            InlineKeyboardButton("🎲 Случайная задача",
                                 callback_data="random_problem"),
            InlineKeyboardButton("🔍 Поиск задач", callback_data="search")
        ],
        [
            InlineKeyboardButton("📝 Тестовый режим",
                                 callback_data="test_mode"),
            InlineKeyboardButton("📊 Моя статистика", callback_data="stats")
        ],
        [InlineKeyboardButton("🏆 Таблица лидеров",
                              callback_data="leaderboard")],
    ]

    # Добавляем кнопку админ-панели только для администратора
    if Config.ADMIN_ID and str(user.id) == Config.ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🔧 Админ-панель",
                                              callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Проверяем, откуда пришел запрос - из сообщения или callback
    if update.message:
        await update.message.reply_text(welcome_text,
                                        reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text,
                                                      reply_markup=reply_markup)
    else:
        # Если ни то, ни другое, отправляем новое сообщение
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                reply_markup=reply_markup
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /help и показывает справку"""
    help_text = """
📖 **Справка по использованию бота:**

**Основные команды:**
• /start - Главное меню
• /sections - Все разделы с задачами
• /random - Случайная задача
• /search - Поиск задач
• /test - Тестовый режим
• /stats - Ваша статистика
• /leaderboard - Таблица лидеров
• /help - Эта справка

**Как работать с ботом:**
1. Выберите раздел или получите случайную задачу
2. Введите ваш ответ в чат
3. Бот проверит ответ и покажет результат
4. Следите за своей статистикой в разделе "Моя статистика"

**Тестовый режим:**
• Решайте задачи последовательно
• Получайте оценку ваших знаний
• Можно завершить тест в любой момент

📊 **Статистика:**
Бот ведет учет всех ваших попыток и рассчитывает успеваемость.

Если возникли проблемы, используйте команду /start для возврата в главное меню.
    """

    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton("📂 Все разделы", callback_data="sections")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(help_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(help_text,
                                                      reply_markup=reply_markup)
    else:
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                reply_markup=reply_markup
            )
