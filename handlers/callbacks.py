from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import Config
from database.models import MathProblemsDB

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = MathProblemsDB(Config.DB_PATH)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все callback запросы от кнопок"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Импортируем здесь, чтобы избежать циклических импортов
    if data == "sections":
        from handlers.problems import sections
        await sections(update, context)

    elif data.startswith("section_"):
        from handlers.problems import show_section_problems
        section_id = int(data.replace("section_", ""))
        await show_section_problems(update, context, section_id)

    elif data.startswith("problem_"):
        from handlers.problems import show_problem
        problem_number = data.replace("problem_", "")
        await show_problem(update, context, problem_number)

    elif data == "random_problem":
        from handlers.problems import random_problem
        await random_problem(update, context)

    elif data.startswith("show_answer_"):
        problem_number = data.replace("show_answer_", "")
        problem = db.get_problem_by_number(problem_number)

        if problem:
            problem_number, problem_text, correct_answer, section_name = problem
            answer_text = f"🔍 **Ответ к задаче №{problem_number}:**\n\n**Правильный ответ:** {correct_answer}\n\n"
            answer_text += f"**Задача:** {problem_text}"

            keyboard = [
                [InlineKeyboardButton("🎲 Случайная задача",
                                      callback_data="random_problem")],
                [InlineKeyboardButton("📂 Все разделы",
                                      callback_data="sections")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(answer_text,
                                          reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Задача не найдена")

    elif data == "search":
        from handlers.search import search
        await search(update, context)

    elif data == "test_mode":
        from handlers.test_mode import test_mode
        await test_mode(update, context)

    elif data in ["test_next", "test_stop"]:
        from handlers.test_mode import handle_test_callback
        await handle_test_callback(update, context)

    elif data == "stats":
        from handlers.stats import stats
        await stats(update, context)

    elif data == "leaderboard":
        from handlers.stats import leaderboard
        await leaderboard(update, context)

    elif data == "admin_panel":
        from handlers.admin import admin_panel
        await admin_panel(update, context)

    elif data.startswith("admin_"):
        from handlers.admin import handle_admin_callback
        await handle_admin_callback(update, context)

    else:
        logger.warning(f"Неизвестный callback data: {data}")
        await query.edit_message_text("❌ Неизвестная команда")


async def sections_from_callback(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    sections_list = db.get_all_sections()

    if not sections_list:
        await query.edit_message_text("❌ Разделы не найдены в базе данных")
        return

    keyboard = []
    for section in sections_list:
        keyboard.append([InlineKeyboardButton(
            f"📖 {section[1]}",
            callback_data=f"section_{section[0]}"
        )])

    keyboard.append(
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📚 Выберите раздел:",
                                  reply_markup=reply_markup)


async def help_from_callback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    help_text = """
📖 **Справка по использованию**

🎯 **Быстрый старт:**
1. Нажмите кнопку **«Menu»** в чате
2. Выберите нужную команду
3. Следуйте инструкциям бота

📱 **Основные команды из Menu:**
• `/sections` - Все разделы задач
• `/search` - Поиск по ключевым словам  
• `/random` - Случайная задача
• `/test` - Проверка знаний
• `/stats` - Ваша статистика
• `/leaderboard` - Рейтинг игроков

💡 **Советы:**
- Используйте Menu для быстрой навигации
- Каждая команда имеет описание
- Не нужно запоминать команды - они всегда под рукой!

**Выберите действие ниже или используйте Menu** 👇
    """

    keyboard = [
        [InlineKeyboardButton("📂 Разделы", callback_data="sections")],
        [InlineKeyboardButton("🎲 Случайная задача", callback_data="random")],
        [InlineKeyboardButton("📝 Тестирование", callback_data="test_mode")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(help_text, reply_markup=reply_markup,
                                  parse_mode=ParseMode.MARKDOWN)
