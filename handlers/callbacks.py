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

    logger.info(f"Обрабатывается callback data: {data}")

    try:
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

        elif data in ["random_problem", "random"]:
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

        elif data == "main_menu":
            from handlers.start import start
            await start(update, context)

        else:
            logger.warning(f"Неизвестный callback data: {data}")
            # Вместо ошибки показываем сообщение и возвращаем в главное меню
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню",
                                      callback_data="main_menu")],
                [InlineKeyboardButton("📂 Все разделы",
                                      callback_data="sections")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Неизвестная команда. Возврат в главное меню.",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке callback data {data}: {e}")
        # В случае ошибки показываем сообщение об ошибке
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню",
                                  callback_data="main_menu")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=reply_markup
        )
