from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta

from config.settings import Config
from database.models import MathProblemsDB

db = MathProblemsDB()


def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id in Config.ADMIN_IDS


async def admin_panel(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает админ-панель"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ У вас нет прав для доступа к админ-панели")
        return

    admin_text = """
🔧 **Админ-панель**

📊 **Статистика:**
• Просмотр статистики всех пользователей
• Детальная статистика по конкретному пользователю
• Статистика за конкретную дату

🗑️ **Управление данными:**
• Очистка статистики пользователей
• Удаление попыток за конкретную дату
• Удаление попыток по конкретным задачам

Выберите действие:
    """

    keyboard = [
        [InlineKeyboardButton("👥 Все пользователи",
                              callback_data="admin_all_users")],
        [InlineKeyboardButton("📊 Детальная статистика",
                              callback_data="admin_user_stats")],
        [InlineKeyboardButton("📅 Статистика за дату",
                              callback_data="admin_date_stats")],
        [InlineKeyboardButton("🗑️ Очистка статистики",
                              callback_data="admin_clear_stats")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(admin_text, reply_markup=reply_markup)


async def show_all_users(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список всех пользователей"""
    query = update.callback_query
    users = db.get_all_users_stats(limit=50)

    if not users:
        await query.edit_message_text("📭 В базе нет пользователей")
        return

    users_text = "👥 **Все пользователи**\n\n"

    for i, user in enumerate(users, 1):
        success_rate = (
                    user['correct_attempts'] / user['total_attempts'] * 100) if \
        user['total_attempts'] > 0 else 0
        display_name = user['first_name'] or user[
            'username'] or f"User {user['user_id']}"

        users_text += f"{i}. **{display_name}** (ID: {user['user_id']})\n"
        users_text += f"   📊 {user['correct_attempts']}/{user['total_attempts']} ({success_rate:.1f}%)\n"
        users_text += f"   🎯 Решено: {user['unique_solved']} задач\n"
        users_text += f"   🕐 Активен: {user['last_activity'][:16]}\n\n"

    keyboard = [
        [InlineKeyboardButton("📊 Детальная статистика",
                              callback_data="admin_user_stats")],
        [InlineKeyboardButton("🔙 Админ-панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(users_text, reply_markup=reply_markup)


async def select_user_for_stats(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает выбор пользователя для детальной статистики"""
    query = update.callback_query
    users = db.get_all_users_stats(limit=20)

    if not users:
        await query.edit_message_text("📭 В базе нет пользователей")
        return ConversationHandler.END

    keyboard = []
    for user in users:
        display_name = user['first_name'] or user[
            'username'] or f"User {user['user_id']}"
        keyboard.append([InlineKeyboardButton(
            f"👤 {display_name} (ID: {user['user_id']})",
            callback_data=f"admin_user_detail_{user['user_id']}"
        )])

    keyboard.append(
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "👤 Выберите пользователя для детальной статистики:",
        reply_markup=reply_markup)

    return Config.WAITING_FOR_USER_SELECTION


async def show_user_detailed_stats(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает детальную статистику пользователя"""
    query = update.callback_query
    user_id = int(query.data.split('_')[3])

    stats = db.get_user_detailed_stats(user_id)

    if not stats:
        await query.edit_message_text("❌ Статистика пользователя не найдена")
        return

    user_info = stats['user_info']

    stats_text = f"""
👤 **Детальная статистика пользователя**

**Основная информация:**
• ID: {user_id}
• Имя: {user_info['first_name'] or 'Не указано'}
• Username: @{user_info['username'] or 'Не указан'}
• Всего попыток: {user_info['total_attempts']}
• Правильных: {user_info['correct_attempts']}
• Уникальных решенных задач: {user_info['unique_solved']}
• Зарегистрирован: {user_info['created_at'][:16]}
• Последняя активность: {user_info['last_activity'][:16]}

**Активность за последние 7 дней:**
"""

    # Активность за последние 7 дней
    today = datetime.now().date()
    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        day_stats = next(
            (day for day in stats['daily_stats'] if day['date'] == date_str),
            None)
        if day_stats:
            stats_text += f"• {date_str}: {day_stats['total_attempts']} попыток ({day_stats['correct_attempts']} правильных)\n"
        else:
            stats_text += f"• {date_str}: Нет активности\n"

    # Самые популярные задачи
    if stats['problem_stats']:
        stats_text += "\n**Самые популярные задачи:**\n"
        for problem in stats['problem_stats'][:5]:
            stats_text += f"• Задача {problem['problem_number']}: {problem['total_attempts']} попыток\n"

    keyboard = [
        [InlineKeyboardButton("📅 Статистика за дату",
                              callback_data=f"admin_user_date_{user_id}")],
        [InlineKeyboardButton("🗑️ Очистка статистики",
                              callback_data=f"admin_clear_user_{user_id}")],
        [InlineKeyboardButton("🔙 К списку пользователей",
                              callback_data="admin_user_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(stats_text, reply_markup=reply_markup)


async def request_date_for_stats(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает дату для просмотра статистики"""
    query = update.callback_query
    user_id = int(query.data.split('_')[3])
    context.user_data['admin_selected_user'] = user_id

    await query.edit_message_text(
        "📅 Введите дату в формате ГГГГ-ММ-ДД (например, 2024-01-15):\n"
        "Или введите 'all' для просмотра всей статистики:"
    )

    return Config.WAITING_FOR_DATE


async def show_user_stats_by_date(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статистику пользователя за конкретную дату"""
    user_id = context.user_data.get('admin_selected_user')
    date_input = update.message.text.strip()

    # Проверяем, является ли это запросом статистики или очистки
    is_clear_operation = context.user_data.get('admin_clear_type') == 'date'

    if date_input.lower() == 'all' and not is_clear_operation:
        date = None
        date_display = "всё время"
    else:
        try:
            # Проверяем корректность даты
            datetime.strptime(date_input, '%Y-%m-%d')
            date = date_input
            date_display = date_input
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return Config.WAITING_FOR_DATE

    # Если это операция очистки, передаем управление соответствующей функции
    if is_clear_operation:
        return await confirm_clear_by_date(update, context)

    # Получаем статистику для отображения
    attempts = db.get_user_attempts_by_date(user_id, date)
    user_stats = db.get_user_detailed_stats(user_id)

    if not user_stats:
        await update.message.reply_text("❌ Пользователь не найден")
        return ConversationHandler.END

    user_info = user_stats['user_info']
    display_name = user_info['first_name'] or user_info[
        'username'] or f"User {user_id}"

    if not attempts:
        stats_text = f"📊 **Статистика пользователя {display_name}**\n\n"
        stats_text += f"За {date_display} нет попыток."
    else:
        total_attempts = len(attempts)
        correct_attempts = sum(
            1 for attempt in attempts if attempt['is_correct'])
        success_rate = (
                    correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

        stats_text = f"📊 **Статистика пользователя {display_name}**\n\n"
        stats_text += f"**За {date_display}:**\n"
        stats_text += f"• Всего попыток: {total_attempts}\n"
        stats_text += f"• Правильных: {correct_attempts}\n"
        stats_text += f"• Успеваемость: {success_rate:.1f}%\n\n"

        stats_text += "**Последние попытки:**\n"
        for attempt in attempts[:10]:
            status = "✅" if attempt['is_correct'] else "❌"
            stats_text += f"• {status} Задача {attempt['problem_number']}: {attempt['user_answer']} ({attempt['solved_at'][11:16]})\n"

    keyboard = [
        [InlineKeyboardButton("🔙 К статистике пользователя",
                              callback_data=f"admin_user_detail_{user_id}")],
        [InlineKeyboardButton("🔙 Админ-панель", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(stats_text, reply_markup=reply_markup)

    # Очищаем временные данные после завершения
    context.user_data.pop('admin_selected_user', None)
    return ConversationHandler.END


async def select_user_for_clearing(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает выбор пользователя для очистки статистики"""
    query = update.callback_query
    users = db.get_all_users_stats(limit=20)

    if not users:
        await query.edit_message_text("📭 В базе нет пользователей")
        return ConversationHandler.END

    keyboard = []
    for user in users:
        display_name = user['first_name'] or user[
            'username'] or f"User {user['user_id']}"
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {display_name} (ID: {user['user_id']})",
            callback_data=f"admin_clear_select_{user['user_id']}"
        )])

    keyboard.append(
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🗑️ Выберите пользователя для очистки статистики:",
        reply_markup=reply_markup)

    return Config.WAITING_FOR_USER_SELECTION


async def show_clear_options(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает опции очистки статистики"""
    query = update.callback_query
    user_id = int(query.data.split('_')[3])
    context.user_data['admin_clear_user'] = user_id

    user_stats = db.get_user_detailed_stats(user_id)
    if not user_stats:
        await query.edit_message_text("❌ Пользователь не найден")
        return

    user_info = user_stats['user_info']
    display_name = user_info['first_name'] or user_info[
        'username'] or f"User {user_id}"

    clear_text = f"""
🗑️ **Очистка статистики пользователя**

Пользователь: **{display_name}**
ID: {user_id}

📊 Текущая статистика:
• Всего попыток: {user_info['total_attempts']}
• Правильных: {user_info['correct_attempts']}
• Решено задач: {user_info['unique_solved']}

Выберите что очистить:
    """

    keyboard = [
        [InlineKeyboardButton("🧹 Всю статистику",
                              callback_data=f"admin_clear_all_{user_id}")],
        [InlineKeyboardButton("📅 За конкретную дату",
                              callback_data=f"admin_clear_date_{user_id}")],
        [InlineKeyboardButton("🔙 К выбору пользователя",
                              callback_data="admin_clear_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(clear_text, reply_markup=reply_markup)


async def confirm_clear_all(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает подтверждение очистки всей статистики"""
    query = update.callback_query
    user_id = int(query.data.split('_')[3])
    context.user_data['admin_clear_user'] = user_id
    context.user_data['admin_clear_type'] = 'all'

    user_stats = db.get_user_detailed_stats(user_id)
    user_info = user_stats['user_info']
    display_name = user_info['first_name'] or user_info[
        'username'] or f"User {user_id}"

    confirm_text = f"""
⚠️ **Подтверждение очистки**

Вы собираетесь удалить ВСЮ статистику пользователя:
**{display_name}** (ID: {user_id})

📊 Будет удалено:
• {user_info['total_attempts']} попыток
• {user_info['correct_attempts']} правильных ответов
• {user_info['unique_solved']} решенных задач

❌ **Это действие нельзя отменить!**

Подтверждаете удаление?
    """

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить всё",
                              callback_data="admin_confirm_clear")],
        [InlineKeyboardButton("❌ Отмена",
                              callback_data=f"admin_clear_select_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(confirm_text, reply_markup=reply_markup)


async def request_date_for_clearing(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает дату для очистки статистики"""
    query = update.callback_query
    user_id = int(query.data.split('_')[3])
    context.user_data['admin_clear_user'] = user_id
    context.user_data['admin_clear_type'] = 'date'

    await query.edit_message_text(
        "📅 Введите дату в формате ГГГГ-ММ-ДД для очистки:\n"
        "Например: 2024-01-15"
    )

    return Config.WAITING_FOR_DATE


async def confirm_clear_by_date(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждает очистку статистики за дату"""
    date_input = update.message.text.strip()
    user_id = context.user_data.get('admin_clear_user')

    try:
        # Проверяем корректность даты
        datetime.strptime(date_input, '%Y-%m-%d')
        date = date_input
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return Config.WAITING_FOR_DATE

    # Получаем количество попыток за эту дату
    attempts = db.get_user_attempts_by_date(user_id, date)
    user_stats = db.get_user_detailed_stats(user_id)
    user_info = user_stats['user_info']
    display_name = user_info['first_name'] or user_info[
        'username'] or f"User {user_id}"

    confirm_text = f"""
⚠️ **Подтверждение очистки**

Вы собираетесь удалить статистику пользователя:
**{display_name}** (ID: {user_id})

📅 За дату: {date}
📊 Будет удалено: {len(attempts)} попыток

❌ **Это действие нельзя отменить!**

Подтверждаете удаление?
    """

    context.user_data['admin_clear_date'] = date

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить",
                              callback_data="admin_confirm_clear")],
        [InlineKeyboardButton("❌ Отмена",
                              callback_data=f"admin_clear_select_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(confirm_text, reply_markup=reply_markup)
    return ConversationHandler.END


async def execute_clear(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет очистку статистики"""
    query = update.callback_query
    user_id = context.user_data.get('admin_clear_user')
    clear_type = context.user_data.get('admin_clear_type')
    date = context.user_data.get('admin_clear_date')

    user_stats = db.get_user_detailed_stats(user_id)
    user_info = user_stats['user_info']
    display_name = user_info['first_name'] or user_info[
        'username'] or f"User {user_id}"

    if clear_type == 'all':
        deleted_count = db.delete_user_attempts(user_id)
        result_text = f"✅ Вся статистика пользователя **{display_name}** удалена!\nУдалено записей: {deleted_count}"
    elif clear_type == 'date' and date:
        deleted_count = db.delete_user_attempts(user_id, date=date)
        result_text = f"✅ Статистика пользователя **{display_name}** за {date} удалена!\nУдалено записей: {deleted_count}"
    else:
        result_text = "❌ Ошибка при очистке статистики"

    keyboard = [
        [InlineKeyboardButton("🔙 Админ-панель", callback_data="admin_panel")],
        [InlineKeyboardButton("🗑️ Ещё очистка",
                              callback_data="admin_clear_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(result_text, reply_markup=reply_markup)

    # Очищаем временные данные
    context.user_data.pop('admin_clear_user', None)
    context.user_data.pop('admin_clear_type', None)
    context.user_data.pop('admin_clear_date', None)


async def cancel_admin(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет админ-действие"""
    await update.message.reply_text("❌ Действие отменено")
    return ConversationHandler.END
