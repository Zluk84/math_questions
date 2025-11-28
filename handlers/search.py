from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.models import MathProblemsDB
from config.settings import Config

db = MathProblemsDB()


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🔍 Введите ключевое слово для поиска задач:\n"
        "Например: скорость, площадь, процент и т.д."
    )
    return Config.WAITING_FOR_SEARCH


async def handle_search(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    keyword = update.message.text
    results = db.search_problems(keyword)

    if not results:
        await update.message.reply_text(
            f"❌ По запросу '{keyword}' ничего не найдено")
    else:
        # Показываем первые 5 результатов
        message_text = f"🔍 Найдено задач: {len(results)}\n\n"
        for i, problem in enumerate(results[:5], 1):
            message_text += f"{i}. Задача {problem[0]}: {problem[1][:50]}...\n"

        if len(results) > 5:
            message_text += f"\n... и еще {len(results) - 5} задач"

        keyboard = []
        for problem in results[:10]:  # Ограничиваем 10 кнопками
            keyboard.append([InlineKeyboardButton(
                f"📝 Задача {problem[0]}",
                callback_data=f"problem_{problem[0]}"
            )])

        keyboard.append(
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text,
                                        reply_markup=reply_markup)

    return ConversationHandler.END


async def search_from_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.edit_message_text(
        "🔍 Введите ключевое слово для поиска задач:\n"
        "Например: скорость, площадь, процент и т.д."
    )
