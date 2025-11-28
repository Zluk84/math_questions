import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import Config
from database.models import MathProblemsDB

# Инициализация базы данных
db = MathProblemsDB(Config.DB_PATH)

# Импортируем функцию проверки ответов из problems.py
from handlers.problems import check_answer, normalize_answer


async def test_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает тестовый режим"""
    # Инициализируем статистику теста
    context.user_data['test_score'] = {
        'total': 0,
        'correct': 0,
        'problems_solved': 0
    }
    context.user_data['test_attempts'] = {}  # Счетчик попыток по задачам
    context.user_data['current_test_problem'] = None

    # Получаем случайную задачу для начала теста
    problem = db.get_random_problem()

    if not problem:
        error_text = "❌ Не удалось найти задачу для теста. База данных пуста."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return ConversationHandler.END

    await show_test_problem(update, context, problem)
    return Config.WAITING_FOR_TEST_ANSWER


async def show_test_problem(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            problem):
    """Показывает задачу в тестовом режиме"""
    problem_number, problem_text, correct_answer, section_name = problem

    # Сохраняем текущую задачу
    context.user_data['current_test_problem'] = problem
    context.user_data['current_problem_number'] = problem_number

    # Инициализируем счетчик попыток для этой задачи
    if problem_number not in context.user_data['test_attempts']:
        context.user_data['test_attempts'][problem_number] = 0

    attempts_count = context.user_data['test_attempts'][problem_number]
    max_attempts = 3
    remaining_attempts = max_attempts - attempts_count

    text = f"📝 **Тестовый режим**\n\n"
    text += f"**Раздел:** {section_name}\n"
    text += f"**Задача №{problem_number}:**\n{problem_text}\n\n"
    text += f"🔄 *Попыток осталось: {remaining_attempts}*"
    text += f"\n📊 *Решено задач: {context.user_data['test_score']['problems_solved']}*"

    keyboard = [
        [InlineKeyboardButton("🔚 Завершить тест", callback_data="test_stop")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text,
                                                      reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def handle_test_answer(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ пользователя в тестовом режиме"""
    user_answer = update.message.text.strip()
    problem = context.user_data.get('current_test_problem')

    if not problem:
        await update.message.reply_text("❌ Ошибка: задача не найдена.")
        return ConversationHandler.END

    problem_number, problem_text, correct_answer, section_name = problem
    user = update.effective_user

    # Увеличиваем счетчик попыток для этой задачи
    context.user_data['test_attempts'][problem_number] += 1
    attempts_count = context.user_data['test_attempts'][problem_number]
    max_attempts = 3

    # Проверяем ответ
    is_correct, message = check_answer(user_answer, correct_answer)

    # Сохраняем попытку в базу данных
    db_attempt_number = db.add_user_attempt(
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
        # Правильный ответ
        context.user_data['test_score']['total'] += 1
        context.user_data['test_score']['correct'] += 1
        context.user_data['test_score']['problems_solved'] += 1

        score = context.user_data['test_score']
        success_rate = (score['correct'] / score['total']) * 100 if score[
                                                                        'total'] > 0 else 0

        message_text = f"""
{message}

✅ **Задача решена!** (попытка {attempts_count})

📊 **Статистика теста:**
Решено задач: {score['problems_solved']}
Правильных ответов: {score['correct']} из {score['total']}
Успеваемость: {success_rate:.1f}%

Выберите действие:
        """

        keyboard = [
            [InlineKeyboardButton("⏭️ Следующая задача",
                                  callback_data="test_next")],
            [InlineKeyboardButton("🔚 Завершить тест",
                                  callback_data="test_stop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message_text,
                                        reply_markup=reply_markup)
        return Config.WAITING_FOR_TEST_ANSWER

    else:
        # Неправильный ответ
        remaining_attempts = max_attempts - attempts_count

        if remaining_attempts > 0:
            message_text = f"""
{message}

🔄 Попробуйте еще раз!
Осталось попыток: {remaining_attempts}

**Задача №{problem_number}:** {problem_text}

Введите новый ответ:
            """
            await update.message.reply_text(message_text)
            return Config.WAITING_FOR_TEST_ANSWER

        else:
            # Закончились попытки
            context.user_data['test_score']['total'] += 1

            score = context.user_data['test_score']
            success_rate = (score['correct'] / score['total']) * 100 if score[
                                                                            'total'] > 0 else 0

            message_text = f"""
{message}

❌ **Закончились попытки!**
Правильный ответ: {correct_answer}

📊 **Статистика теста:**
Решено задач: {score['problems_solved']}
Правильных ответов: {score['correct']} из {score['total']}
Успеваемость: {success_rate:.1f}%

Выберите действие:
            """

            keyboard = [
                [InlineKeyboardButton("⏭️ Следующая задача",
                                      callback_data="test_next")],
                [InlineKeyboardButton("🔚 Завершить тест",
                                      callback_data="test_stop")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(message_text,
                                            reply_markup=reply_markup)
            return Config.WAITING_FOR_TEST_ANSWER


async def handle_test_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает callback от кнопок в тестовом режиме"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "test_next":
        # Получаем следующую случайную задачу
        problem = db.get_random_problem()
        if problem:
            await show_test_problem(update, context, problem)
            return Config.WAITING_FOR_TEST_ANSWER
        else:
            await query.edit_message_text(
                "❌ Не удалось найти следующую задачу.")
            return ConversationHandler.END

    elif data == "test_stop":
        # Завершаем тест и показываем результаты
        score = context.user_data.get('test_score', {'total': 0, 'correct': 0,
                                                     'problems_solved': 0})
        total = score['total']
        correct = score['correct']
        problems_solved = score['problems_solved']

        success_rate = (correct / total * 100) if total > 0 else 0

        # Определяем оценку
        if success_rate >= 90:
            grade = "5️⃣ Отлично!"
        elif success_rate >= 75:
            grade = "4️⃣ Хорошо!"
        elif success_rate >= 60:
            grade = "3️⃣ Удовлетворительно"
        else:
            grade = "2️⃣ Нужно подтянуть знания"

        result_text = f"""
📊 **Результаты теста:**

✅ Правильных ответов: {correct} из {total}
📈 Успеваемость: {success_rate:.1f}%
🎯 Решено задач: {problems_solved}
📝 Оценка: {grade}

Для продолжения выберите действие:
        """

        keyboard = [
            [InlineKeyboardButton("📝 Новый тест", callback_data="test_mode")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(result_text, reply_markup=reply_markup)

        # Очищаем данные теста
        context.user_data.pop('test_score', None)
        context.user_data.pop('test_attempts', None)
        context.user_data.pop('current_test_problem', None)
        context.user_data.pop('current_problem_number', None)

        return ConversationHandler.END

    return Config.WAITING_FOR_TEST_ANSWER
