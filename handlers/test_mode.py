from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.models import MathProblemsDB
from utils.answer_checker import check_answer
from config.settings import Config

db = MathProblemsDB()


async def test_mode(update: Update,
                    context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает режим проверки знаний"""
    user = update.effective_user if hasattr(update,
                                            'effective_user') else update.callback_query.from_user
    # Пытаемся найти нерешенную задачу
    problem = db.get_random_unsolved_problem(user.id)

    if not problem:
        # Если все задачи решены, берем любую случайную
        problem = db.get_random_problem()
        if problem:
            message_prefix = "🎉 Вы решили все задачи! Вот случайная задача для повторения:\n\n"
        else:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Не удалось найти задачу для теста")
            else:
                await update.message.reply_text(
                    "❌ Не удалось найти задачу для теста")
            return
    else:
        message_prefix = ""

    if problem:
        context.user_data['current_problem'] = problem
        context.user_data['test_score'] = context.user_data.get('test_score',
                                                                {'correct': 0,
                                                                 'total': 0})
        context.user_data[
            'test_attempts'] = 0  # Сбрасываем счетчик попыток для теста

        problem_number, problem_text, answer, section_name = problem

        # Получаем количество предыдущих попыток
        user_attempts_count = db.get_user_attempts_count(user.id,
                                                         problem_number)

        message_text = f"""
{message_prefix}📝 **Режим проверки знаний**

Задача {problem_number}:
{problem_text}

📚 Раздел: {section_name}
"""

        if user_attempts_count > 0:
            message_text += f"\n🔄 Предыдущих попыток: {user_attempts_count}"

        message_text += "\n\n✏️ Введите ваш ответ:"

        keyboard = [
            [InlineKeyboardButton("🔍 Показать ответ",
                                  callback_data=f"show_answer_{problem_number}")],
            [InlineKeyboardButton("⏭️ Следующая задача",
                                  callback_data="test_next")],
            [InlineKeyboardButton("🔚 Завершить тест",
                                  callback_data="test_stop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text,
                                                          reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text,
                                            reply_markup=reply_markup)

        return Config.WAITING_FOR_TEST_ANSWER
    else:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Не удалось найти задачу для теста")
        else:
            await update.message.reply_text(
                "❌ Не удалось найти задачу для теста")
        return ConversationHandler.END


async def handle_test_answer(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ответ пользователя в режиме теста"""
    user_answer = update.message.text
    problem = context.user_data.get('current_problem')

    if problem:
        user = update.effective_user
        problem_number, problem_text, correct_answer, section_name = problem

        # Увеличиваем счетчик попыток в контексте
        context.user_data['test_attempts'] = context.user_data.get(
            'test_attempts', 0) + 1
        test_attempts = context.user_data['test_attempts']

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
            # Правильный ответ
            context.user_data['test_score']['total'] += 1
            context.user_data['test_score']['correct'] += 1

            score = context.user_data['test_score']
            success_rate = (score['correct'] / score['total']) * 100 if score[
                                                                            'total'] > 0 else 0

            message_text = f"""
{message}

📊 **Статистика:**
✅ Правильно: {score['correct']} из {score['total']}
📈 Успеваемость: {success_rate:.1f}%

🎯 Задача решена с {attempt_number} попытки!

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
            remaining_attempts = 3 - test_attempts

            if remaining_attempts > 0:
                message_text = f"""
{message}

🔄 Осталось попыток в этом тесте: {remaining_attempts}
📝 Всего попыток для этой задачи: {attempt_number}

Попробуйте еще раз:
                """
                await update.message.reply_text(message_text)
                return Config.WAITING_FOR_TEST_ANSWER
            else:
                # Закончились попытки в тесте
                message_text = f"""
{message}

❌ Закончились попытки в тесте. Правильный ответ: {correct_answer}

📊 Переходим к следующей задаче:
                """

                context.user_data['test_score']['total'] += 1
                score = context.user_data['test_score']
                success_rate = (score['correct'] / score['total']) * 100 if \
                score['total'] > 0 else 0

                message_text += f"\n📊 Статистика: {score['correct']} из {score['total']} ({success_rate:.1f}%)"

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
        await update.message.reply_text("❌ Ошибка: задача не найдена")
        return ConversationHandler.END  # Завершаем ConversationHandler если задачи нет


async def check_mode(update: Update,
                     context: ContextTypes.DEFAULT_TYPE) -> int:
    """Включает режим проверки для конкретной задачи"""
    query = update.callback_query
    problem_number = int(query.data.split('_')[2])
    problem_data = db.get_problem_by_number(problem_number)

    if problem_data:
        user = query.from_user

        # Получаем количество предыдущих попыток
        user_attempts_count = db.get_user_attempts_count(user.id,
                                                         problem_number)

        if user_attempts_count >= 3:
            # Получаем последнюю попытку
            last_attempt = db.get_last_user_attempt(user.id, problem_number)
            if last_attempt and last_attempt['is_correct']:
                await query.edit_message_text(
                    "✅ Вы уже решили эту задачу правильно!")
            else:
                await query.edit_message_text(
                    "❌ Вы использовали все 3 попытки для этой задачи.")
            return ConversationHandler.END

        context.user_data['current_check_problem'] = problem_data
        context.user_data['check_attempts'] = user_attempts_count

        problem_number, problem_text, answer, section_name = problem_data

        message_text = f"""
📝 **Проверка ответа**

Задача {problem_number}:
{problem_text}

🔄 Попыток использовано: {user_attempts_count}/3

✏️ Введите ваш ответ для проверки:
        """

        await query.edit_message_text(message_text)
        return Config.WAITING_FOR_CHECK_ANSWER
    else:
        await query.edit_message_text("❌ Задача не найдена")
        return ConversationHandler.END


async def handle_check_answer(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает проверку ответа для конкретной задачи"""
    user_answer = update.message.text
    problem = context.user_data.get('current_check_problem')

    if problem:
        user = update.effective_user
        problem_number, problem_text, correct_answer, section_name = problem

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
            # Правильный ответ
            message_text = f"""
📝 **Задача {problem_number}**

{problem_text}

{message}

✅ Решено с {attempt_number} попытки!
            """

            keyboard = [
                [InlineKeyboardButton("🔍 Показать ответ",
                                      callback_data=f"answer_{problem_number}")],
                [InlineKeyboardButton("📋 История попыток",
                                      callback_data=f"problem_history_{problem_number}")],
                [InlineKeyboardButton("🔙 К разделам",
                                      callback_data="sections")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(message_text,
                                            reply_markup=reply_markup)
            return ConversationHandler.END

        else:
            # Неправильный ответ
            remaining_attempts = 3 - attempt_number

            if remaining_attempts > 0:
                message_text = f"""
{message}

🔄 Осталось попыток: {remaining_attempts}
📝 Всего попыток: {attempt_number}

Попробуйте еще раз:
                """
                await update.message.reply_text(message_text)
                return Config.WAITING_FOR_CHECK_ANSWER
            else:
                # Закончились попытки
                message_text = f"""
{message}

❌ Закончились попытки. Правильный ответ: {correct_answer}

📊 Всего попыток для этой задачи: {attempt_number}
                """

                keyboard = [
                    [InlineKeyboardButton("🔍 Показать ответ",
                                          callback_data=f"answer_{problem_number}")],
                    [InlineKeyboardButton("📋 История попыток",
                                          callback_data=f"problem_history_{problem_number}")],
                    [InlineKeyboardButton("🔙 К разделам",
                                          callback_data="sections")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(message_text,
                                                reply_markup=reply_markup)
                return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Ошибка: задача не найдена")
        return ConversationHandler.END


async def show_problem_history(update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю попыток для конкретной задачи"""
    query = update.callback_query

    # Получаем номер задачи из callback data
    try:
        problem_number = int(query.data.split('_')[2])  # problem_history_123
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка в формате номера задачи")
        return

    user = query.from_user
    attempts = db.get_user_attempts_for_problem(user.id, problem_number)
    problem_data = db.get_problem_by_number(problem_number)

    if not problem_data:
        await query.edit_message_text("❌ Задача не найдена")
        return

    problem_number, problem_text, correct_answer, section_name = problem_data

    if attempts:
        history_text = f"""
📋 **История попыток - Задача {problem_number}**

{problem_text}

✅ **Правильный ответ:** {correct_answer}

**Ваши попытки:**
"""

        for i, attempt in enumerate(attempts, 1):
            status = "✅" if attempt['is_correct'] else "❌"
            history_text += f"""
{i}. {status} Попытка {attempt['attempt_number']}:
   Ваш ответ: `{attempt['user_answer']}`
   Время: {attempt['solved_at'][:16]}
"""

        # Статистика по задаче
        total_attempts = len(attempts)
        correct_attempts = sum(
            1 for attempt in attempts if attempt['is_correct'])
        success_rate = (
                    correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

        history_text += f"""
📊 **Статистика по задаче:**
📝 Всего попыток: {total_attempts}
✅ Правильных: {correct_attempts}
📈 Успеваемость: {success_rate:.1f}%
"""

    else:
        history_text = f"""
📋 **Задача {problem_number}**

{problem_text}

📝 У вас пока нет попыток для этой задачи.
"""

    keyboard = []

    # Проверяем, можно ли еще решать задачу
    user_attempts_count = db.get_user_attempts_count(user.id, problem_number)
    is_solved = db.is_problem_solved_by_user(user.id, problem_number)

    if not is_solved and user_attempts_count < 3:
        keyboard.append([InlineKeyboardButton("📝 Проверить ответ",
                                              callback_data=f"check_mode_{problem_number}")])

    keyboard.append([InlineKeyboardButton("🔍 Показать ответ",
                                          callback_data=f"answer_{problem_number}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад к задаче",
                                          callback_data=f"problem_{problem_number}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(history_text, reply_markup=reply_markup)
