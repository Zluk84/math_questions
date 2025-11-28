from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config.settings import Config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

🤖 Я - умный бот с сборником математических задач для 6 класса.

📚 **Что я умею:**
• Предлагать задачи из разных разделов математики
• Проверять ваши ответы с учетом разных форматов
• Вести статистику вашего прогресса
• Сохранять историю всех попыток
• Создавать индивидуальные тесты

🎯 **Как пользоваться:**
• Используйте кнопку **«Menu»** 📱 для быстрого доступа ко всем командам
• Или выбирайте действия через интерактивные кнопки ниже
• Все команды также можно вводить вручную

📖 **Основные разделы:**
• Движение по воде
• Совместная работа  
• Делимость чисел
• Дроби и проценты
• Отношения и пропорции
• И многое другое!

Выберите действие ниже или используйте меню команд 👇
    """

    keyboard = [
        [InlineKeyboardButton("📂 Разделы задач", callback_data="sections")],
        [InlineKeyboardButton("🔍 Поиск задач", callback_data="search")],
        [InlineKeyboardButton("🎲 Случайная задача", callback_data="random")],
        [InlineKeyboardButton("📝 Проверка знаний", callback_data="test_mode")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("📋 История попыток",
                              callback_data="attempts_history")],
        [InlineKeyboardButton("🏆 Таблица лидеров",
                              callback_data="leaderboard")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup,
                                    parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📖 **Руководство по использованию бота**

🤖 **О боте:**
Этот бот содержит сборник математических задач для 6 класса. Все задачи разделены по темам и сложности.

🎯 **Основные команды (доступны через Menu):**

`/start` - 🚀 Начать работу с ботом
`/sections` - 📂 Показать все разделы с задачами  
`/search` - 🔍 Поиск задач по ключевому слову
`/random` - 🎲 Получить случайную задачу
`/test` - 📝 Режим проверки знаний
`/stats` - 📊 Моя статистика и прогресс
`/leaderboard` - 🏆 Таблица лидеров
`/help` - ℹ️ Эта справка

🔍 **Как работать с задачами:**

1. **Выберите раздел** - просмотрите все доступные задачи
2. **Используйте поиск** - найдите задачи по ключевым словам
3. **Решайте случайные задачи** - для разнообразия
4. **Проходите тесты** - проверьте свои знания

📊 **Система оценивания:**
- ✅ Сохраняются все ваши попытки
- 📈 Весь прогресс отслеживается
- 🎯 Дается 3 попытки на решение каждой задачи
- 🏆 Соревнуйтесь с другими в таблице лидеров

💡 **Советы:**
- Используйте кнопку **«Menu»** для быстрой навигации
- Регулярно проверяйте свою статистику
- Не бойтесь ошибаться - каждая попытка учит чему-то новому!

**Готовы начать?** Выберите действие ниже 👇
    """

    keyboard = [
        [InlineKeyboardButton("📂 Начать решать", callback_data="sections")],
        [InlineKeyboardButton("🎲 Случайная задача", callback_data="random")],
        [InlineKeyboardButton("📝 Тестирование", callback_data="test_mode")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(help_text, reply_markup=reply_markup,
                                    parse_mode=ParseMode.MARKDOWN)


async def start_from_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start из callback"""
    query = update.callback_query
    user = query.from_user
    welcome_text = f"""
👋 С возвращением, {user.first_name}!

🤖 Главное меню математического бота.

🎯 **Быстрый доступ:**
• Используйте кнопку **«Menu»** для всех команд
• Или выбирайте действия ниже

Выберите раздел или действие 👇
    """

    keyboard = [
        [InlineKeyboardButton("📂 Разделы задач", callback_data="sections")],
        [InlineKeyboardButton("🔍 Поиск задач", callback_data="search")],
        [InlineKeyboardButton("🎲 Случайная задача", callback_data="random")],
        [InlineKeyboardButton("📝 Проверка знаний", callback_data="test_mode")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("📋 История попыток",
                              callback_data="attempts_history")],
        [InlineKeyboardButton("🏆 Таблица лидеров",
                              callback_data="leaderboard")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(welcome_text, reply_markup=reply_markup,
                                  parse_mode=ParseMode.MARKDOWN)
