import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = os.getenv('ADMIN_ID')

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле")

    # Состояния для ConversationHandler
    WAITING_FOR_SEARCH, WAITING_FOR_TEST_ANSWER, WAITING_FOR_CHECK_ANSWER = range(
        3)

    # Состояния для админ-панели
    WAITING_FOR_DATE, WAITING_FOR_USER_SELECTION, WAITING_FOR_CONFIRMATION = range(
        3, 6)
    # Состояния ConversationHandler

    WAITING_FOR_RANDOM_ANSWER = 7  # Новое состояние для случайных задач

    # Настройки базы данных
    DB_PATH = 'math_problems.db'

    # Список администраторов (можно добавить несколько через запятую)
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in
                 ADMIN_ID.split(',')] if ADMIN_ID else []
