import logging
import sys
from pathlib import Path
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters, ConversationHandler
from telegram import BotCommand, BotCommandScopeAllPrivateChats

from config.settings import Config
from database.models import MathProblemsDB
from database.init_db import DatabaseInitializer
from handlers.start import start, help_command
from handlers.problems import sections, random_problem, handle_random_answer
from handlers.search import search, handle_search
from handlers.test_mode import test_mode, handle_test_answer
from handlers.stats import stats, leaderboard
from handlers.callbacks import button_handler
from handlers.admin import admin_panel, show_user_stats_by_date, cancel_admin

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def initialize_database_if_needed():
    """Проверяет и инициализирует базу данных при необходимости"""
    db_path = Config.DB_PATH

    # Сначала создаем объект БД - он создаст пустые таблицы
    db = MathProblemsDB(db_path)

    # Проверяем, есть ли данные в базе
    sections = db.get_all_sections()
    if not sections:
        logger.info("База данных пуста, начинаем загрузку данных...")
        initializer = DatabaseInitializer(db_path=db_path)
        if initializer.initialize_database():
            logger.info("Данные успешно загружены в базу")
            return True
        else:
            logger.error("Не удалось загрузить данные в базу")
            return False

    logger.info(f"База данных уже содержит {len(sections)} разделов")
    return True


async def set_bot_commands(application):
    """Устанавливает меню команд для бота"""
    commands = [
        BotCommand("start", "🚀 Начать работу с ботом"),
        BotCommand("sections", "📂 Показать все разделы с задачами"),
        BotCommand("search", "🔍 Поиск задач по ключевому слову"),
        BotCommand("random", "🎲 Получить случайную задачу"),
        BotCommand("test", "📝 Режим проверки знаний"),
        BotCommand("stats", "📊 Моя статистика и прогресс"),
        BotCommand("leaderboard", "🏆 Таблица лидеров"),
        BotCommand("help", "ℹ️ Получить справку по использованию"),
        BotCommand("admin", "🔧 Админ-панель (только для администраторов)"),
    ]
    await application.bot.set_my_commands(
        commands,
        scope=BotCommandScopeAllPrivateChats()
    )
    logger.info("Меню команд бота установлено")


async def post_init(application):
    """Функция, выполняемая после инициализации бота"""
    await set_bot_commands(application)
    logger.info("Бот успешно инициализирован и готов к работе")


async def init_db_command(update, context):
    """Команда для принудительной переинициализации базы данных"""
    user = update.effective_user

    # Проверяем права администратора (опционально)
    if Config.ADMIN_ID and str(user.id) != Config.ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды")
        return

    await update.message.reply_text(
        "🔄 Начинаю переинициализацию базы данных...")

    initializer = DatabaseInitializer()
    if initializer.initialize_database():
        await update.message.reply_text(
            "✅ База данных успешно переинициализирована!")
    else:
        await update.message.reply_text(
            "❌ Ошибка при переинициализации базы данных")


async def cancel(update, context):
    """Отмена любого диалога"""
    await update.message.reply_text("Диалог отменен.")
    # Очищаем user_data
    context.user_data.clear()
    return ConversationHandler.END


async def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)

    if update and hasattr(update,
                          'effective_message') and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
        )


def main():
    # Проверяем и инициализируем базу данных
    if not initialize_database_if_needed():
        logger.error(
            "Не удалось инициализировать базу данных. Завершаем работу.")
        sys.exit(1)

    # Создание приложения
    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Установка функции post_init
    application.post_init = post_init

    # ОБРАТИТЕ ВНИМАНИЕ: Порядок добавления обработчиков ВАЖЕН!
    # Сначала добавляем специфичные обработчики, затем общие

    # 1. ConversationHandler для случайных задач
    random_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("random", random_problem),
            CallbackQueryHandler(random_problem, pattern="^random_problem$"),
        ],
        states={
            Config.WAITING_FOR_RANDOM_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_random_answer),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        name="random_conversation"
    )

    application.add_handler(random_conv_handler)

    # 2. ConversationHandler для тестового режима
    test_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("test", test_mode),
            CallbackQueryHandler(test_mode, pattern="^test_mode$"),
        ],
        states={
            Config.WAITING_FOR_TEST_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_test_answer),
                CommandHandler("cancel", cancel),
                CallbackQueryHandler(button_handler,
                                     pattern="^(test_next|test_stop|show_answer_)"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        name="test_conversation"
    )

    application.add_handler(test_conv_handler)

    # 3. ConversationHandler для поиска
    search_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("search", search),
            CallbackQueryHandler(search, pattern="^search$"),
        ],
        states={
            Config.WAITING_FOR_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        name="search_conversation"
    )

    application.add_handler(search_conv_handler)

    # 4. ConversationHandler для админ-панели
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_panel),
            CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
        ],
        states={
            Config.WAITING_FOR_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               show_user_stats_by_date),
                CommandHandler("cancel", cancel_admin),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        allow_reentry=True,
        name="admin_conversation"
    )

    application.add_handler(admin_conv_handler)

    # 5. Обработчики команд (которые не требуют состояний)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sections", sections))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("init_db", init_db_command))

    # 6. Обработчик всех callback запросов (должен быть ПОСЛЕДНИМ среди CallbackQueryHandler)
    application.add_handler(CallbackQueryHandler(button_handler))

    # 7. Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    print("=" * 50)
    print("🤖 Математический бот для 6 класса запущен!")
    print("=" * 50)
    print("📋 Доступные команды в меню:")
    print("   /start - 🚀 Начать работу с ботом")
    print("   /sections - 📂 Показать все разделы с задачами")
    print("   /search - 🔍 Поиск задач по ключевому слову")
    print("   /random - 🎲 Получить случайную задачу")
    print("   /test - 📝 Режим проверки знаний")
    print("   /stats - 📊 Моя статистика и прогресс")
    print("   /leaderboard - 🏆 Таблица лидеров")
    print("   /help - ℹ️ Получить справку по использованию")
    print("   /admin - 🔧 Админ-панель (только для администраторов)")
    print("=" * 50)
    print("Нажмите на кнопку 'Menu' в чате чтобы увидеть все команды!")

    application.run_polling()


if __name__ == "__main__":
    main()
