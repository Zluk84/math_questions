from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.models import MathProblemsDB

db = MathProblemsDB()


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику пользователя"""
    user = update.effective_user
    user_stats = db.get_user_stats(user.id)

    if user_stats:
        stats_text = f"""
📊 **Статистика пользователя {user.first_name}**

📝 Всего попыток: {user_stats['total_attempts']}
✅ Правильных ответов: {user_stats['correct_attempts']}
📈 Общая успеваемость: {user_stats['success_rate']}%

🎯 Уникальных решенных задач: {user_stats['unique_solved_problems']}
🔍 Всего задач attempted: {user_stats['total_problems_attempted']}
📊 Успеваемость по задачам: {user_stats['unique_success_rate']}%

🎯 Среднее количество попыток на задачу: {user_stats['avg_attempts_per_problem']}

🕐 Последняя активность: {user_stats['last_activity'][:16]}
        """

        # Добавляем активность за последние 7 дней
        if user_stats['last_7_days_activity']:
            stats_text += "\n📅 Активность за последние 7 дней:\n"
            for date, count in user_stats['last_7_days_activity'][
                               :5]:  # Показываем последние 5 дней
                stats_text += f"   {date}: {count} попыток\n"

    else:
        stats_text = f"""
📊 **Статистика пользователя {user.first_name}**

У вас пока нет решенных задач.
Начните решать задачи, чтобы увидеть свою статистику!
        """

    keyboard = [
        [InlineKeyboardButton("📋 История попыток",
                              callback_data="attempts_history")],
        [InlineKeyboardButton("🎯 Начать решать", callback_data="random")],
        [InlineKeyboardButton("🏆 Таблица лидеров",
                              callback_data="leaderboard")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(stats_text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(stats_text, reply_markup=reply_markup)


# ... остальные функции stats.py без изменений ...


async def attempts_history(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю попыток пользователя"""
    user = update.effective_user
    recent_attempts = db.get_user_recent_attempts(user.id, limit=10)

    if recent_attempts:
        history_text = f"""
📋 **Последние попытки пользователя {user.first_name}**

"""
        for i, attempt in enumerate(recent_attempts, 1):
            status = "✅" if attempt['is_correct'] else "❌"
            problem_text_short = attempt['problem_text'][:50] + "..." if len(
                attempt['problem_text']) > 50 else attempt['problem_text']

            history_text += f"""
{i}. {status} **Задача {attempt['problem_number']}**
   Ваш ответ: `{attempt['user_answer']}`
   Правильный: `{attempt['correct_answer']}`
   Попытка: {attempt['attempt_number']} • {attempt['solved_at'][:16]}
"""

        if len(recent_attempts) == 10:
            history_text += "\n📖 Показаны последние 10 попыток"

    else:
        history_text = "📋 У вас пока нет попыток решений."

    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data="stats")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(history_text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(history_text,
                                        reply_markup=reply_markup)


async def leaderboard(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает таблицу лидеров"""
    leaders = db.get_leaderboard(10)

    if leaders:
        leaderboard_text = "🏆 **Таблица лидеров**\n\n"
        for i, leader in enumerate(leaders, 1):
            success_rate = (leader['correct_attempts'] / leader[
                'total_attempts'] * 100) if leader['total_attempts'] > 0 else 0
            display_name = leader['first_name'] or leader[
                'username'] or "Аноним"
            leaderboard_text += f"{i}. {display_name} - {leader['unique_solved']} реш. ({success_rate:.1f}%)\n"
    else:
        leaderboard_text = "🏆 **Таблица лидеров**\n\nПока нет данных для отображения."

    keyboard = [
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("📋 Мои попытки",
                              callback_data="attempts_history")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(leaderboard_text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(leaderboard_text,
                                        reply_markup=reply_markup)
