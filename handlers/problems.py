import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import Config
from database.models import MathProblemsDB

# Инициализация базы данных
db = MathProblemsDB(Config.DB_PATH)


def check_answer(user_answer, correct_answer):
    """Проверяет ответ пользователя"""
    try:
        # Пробуем сравнить как числа
        user_num = float(user_answer.replace(',', '.'))
        correct_num = float(correct_answer.replace(',', '.'))

        if abs(user_num - correct_num) < 0.001:  # Учитываем погрешность округления
            return True, "✅ Правильно! Отличная работа!"
        else:
            return False, f"❌ Неправильно. Ваш ответ: {user_answer}"

    except (ValueError, TypeError):
        # Если не числа, сравниваем как строки
        if str(user_answer).strip().lower() == str(
                correct_answer).strip().lower():
            return True, "✅ Правильно! Отличная работа!"
        else:
            return False, f"❌ Неправильно. Ваш ответ: {user_answer}"


async def sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все разделы с задачами"""
    sections_data = db.get_all_sections()

    if not sections_data:
        await update.message.reply_text("❌ Разделы с задачами не найдены.")
        return

    keyboard = []
    for section in sections_data:
        section_id, section_name, problem_count = section
        button_text = f"{section_name} ({problem_count} задач)"
        keyboard.append([InlineKeyboardButton(button_text,
                                              callback_data=f"section_{section_id}")])

    # Добавляем кнопки для других функций
    keyboard.append([
        InlineKeyboardButton("🎲 Случайная задача",
                             callback_data="random_problem"),
        InlineKeyboardButton("🔍 Поиск задач", callback_data="search")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📂 **Выберите раздел:**\n\n"
    for section in sections_data:
        section_id, section_name, problem_count = section
        text += f"• {section_name} - {problem_count} задач\n"

    if update.callback_query:
        await update.callback_query.edit_message_text(text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def show_section_problems(update: Update,
                                context: ContextTypes.DEFAULT_TYPE,
                                section_id: int):
    """Показывает задачи в выбранном разделе"""
    problems = db.get_problems_by_section(section_id)
    section_name = db.get_section_name(section_id)

    if not problems:
        await update.callback_query.edit_message_text(
            "❌ В этом разделе нет задач.")
        return

    keyboard = []
    for problem in problems:
        problem_number, problem_text, correct_answer, _ = problem
        # Обрезаем длинный текст задачи для кнопки
        button_text = f"Задача {problem_number}"
        if len(problem_text) > 30:
            button_text = f"Задача {problem_number}: {problem_text[:30]}..."
        keyboard.append([InlineKeyboardButton(button_text,
                                              callback_data=f"problem_{problem_number}")])

    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton("🔙 Назад к разделам", callback_data="sections"),
        InlineKeyboardButton("🎲 Случайная задача",
                             callback_data="random_problem")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"📂 **Раздел: {section_name}**\n\n"
    text += f"**Доступно задач: {len(problems)}**\n\n"
    text += "Выберите задачу:"

    await update.callback_query.edit_message_text(text,
                                                  reply_markup=reply_markup)


async def show_problem(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       problem_number: str):
    """Показывает конкретную задачу"""
    problem = db.get_problem_by_number(problem_number)

    if not problem:
        await update.callback_query.edit_message_text("❌ Задача не найдена.")
        return

    problem_number, problem_text, correct_answer, section_name = problem

    text = f"📚 **Задача №{problem_number}**\n\n"
    text += f"**Раздел:** {section_name}\n"
    text += f"**Задача:** {problem_text}\n\n"
    text += "💡 *Нажмите 'Показать ответ' чтобы увидеть решение*"

    keyboard = [
        [InlineKeyboardButton("🔍 Показать ответ",
                              callback_data=f"show_answer_{problem_number}")],
        [
            InlineKeyboardButton("📂 К разделам", callback_data="sections"),
            InlineKeyboardButton("🎲 Случайная задача",
                                 callback_data="random_problem")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text,
                                                  reply_markup=reply_markup)


async def random_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает случайную задачу"""
    problem = db.get_random_problem()

    if not problem:
        error_text = "❌ Не удалось найти задачу. База данных пуста."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return Config.WAITING_FOR_RANDOM_ANSWER

    problem_number, problem_text, correct_answer, section_name = problem

    # Сохраняем информацию о задаче в context для проверки ответа
    context.user_data['current_problem'] = problem
    context.user_data['problem_type'] = 'random'

    text = f"🎲 **Случайная задача**\n\n"
    text += f"**Раздел:** {section_name}\n"
    text += f"**Задача №{problem_number}:**\n{problem_text}\n\n"
    text += "💡 *Введите ваш ответ:*"

    keyboard = [
        [InlineKeyboardButton("🔍 Показать ответ",
                              callback_data=f"show_answer_{problem_number}")],
        [InlineKeyboardButton("🎲 Другая случайная задача",
                              callback_data="random_problem")],
        [InlineKeyboardButton("📂 Все разделы", callback_data="sections")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

    return Config.WAITING_FOR_RANDOM_ANSWER


async def handle_random_answer(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ пользователя на случайную задачу"""
    user_answer = update.message.text.strip()
    problem = context.user_data.get('current_problem')

    if not problem:
        await update.message.reply_text(
            "❌ Ошибка: задача не найдена. Попробуйте получить новую задачу.")
        return ConversationHandler.END

    problem_number, problem_text, correct_answer, section_name = problem
    user = update.effective_user

    # Проверяем ответ
    is_correct, message = check_answer(user_answer, correct_answer)

    # Сохраняем попытку в базу данных
    attempt_number = db.add_user_attempt(
        user.id,
        problem_number,
        user_answer,
        correct_answer,
        is_correct
    )

    # Обновляем статистику пользователя
    db.update_user_stats(
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        is_correct,
        problem_number
    )

    if is_correct:
        message_text = f"""
{message}

🎉 **Поздравляем!** Вы решили задачу с {attempt_number} попытки!

**Раздел:** {section_name}
**Задача №{problem_number}**

Выберите действие:
        """

        keyboard = [
            [InlineKeyboardButton("🎲 Новая случайная задача",
                                  callback_data="random_problem")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text,
                                        reply_markup=reply_markup)

        # Если ответ правильный, завершаем состояние
        context.user_data.pop('current_problem', None)
        context.user_data.pop('problem_type', None)
        return ConversationHandler.END

    else:
        message_text = f"""
{message}

🔄 Попробуйте еще раз! Всего попыток для этой задачи: {attempt_number}

**Раздел:** {section_name}
**Задача №{problem_number}:** {problem_text}

Введите новый ответ:
        """

        keyboard = [
            [InlineKeyboardButton("🔍 Показать ответ",
                                  callback_data=f"show_answer_{problem_number}")],
            [InlineKeyboardButton("🎲 Другая случайная задача",
                                  callback_data="random_problem")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text,
                                        reply_markup=reply_markup)

        # Если ответ неправильный, остаемся в состоянии ожидания ответа
        return Config.WAITING_FOR_RANDOM_ANSWER
