import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import Config
from database.models import MathProblemsDB

# Инициализация базы данных
db = MathProblemsDB(Config.DB_PATH)


def extract_number_from_text(text):
    """Извлекает числовое значение из текста, игнорируя размерности и наименования"""
    if not text:
        return None

    # Приводим к строке и убираем лишние пробелы
    text = str(text).strip().lower()

    # Убираем все пробелы
    text = text.replace(' ', '')

    # Список русских слов, которые могут обозначать предметы/единицы измерения
    dimension_words = [
        'рыб', 'рыба', 'рыбу', 'рыбой', 'рыбе',
        'яблок', 'яблока', 'яблоко', 'яблук', 'яблуко',
        'груш', 'груша', 'грушу', 'грушей', 'груше',
        'книг', 'книга', 'книгу', 'книгой', 'книге',
        'тетрад', 'тетрадь', 'тетради', 'тетрадью',
        'ручк', 'ручка', 'ручки', 'ручкой',
        'карандаш', 'карандаша', 'карандашу', 'карандашем', 'карандаше',
        'ученик', 'ученика', 'ученику', 'учеником', 'ученике',
        'учениц', 'ученицы', 'ученице', 'ученицей',
        'человек', 'человека', 'человеку', 'человеком', 'человеке',
        'людей', 'людям', 'людьми',
        'дом', 'дома', 'дому', 'домом', 'доме',
        'квартир', 'квартира', 'квартиру', 'квартирой', 'квартире',
        'машин', 'машина', 'машину', 'машиной', 'машине',
        'автомобил', 'автомобиля', 'автомобилю', 'автомобилем', 'автомобиле',
        'день', 'дня', 'дню', 'днем', 'дне',
        'час', 'часа', 'часу', 'часом', 'часе',
        'минут', 'минута', 'минуту', 'минутой', 'минуте',
        'рубл', 'рубль', 'рубля', 'рублю', 'рублем', 'рубле',
        'копе', 'копейка', 'копейки', 'копейку', 'копейкой',
        'метр', 'метра', 'метру', 'метром', 'метре',
        'сантиметр', 'сантиметра', 'сантиметру', 'сантиметром', 'сантиметре',
        'килограмм', 'килограмма', 'килограмму', 'килограммом', 'килограмме',
        'грамм', 'грамма', 'грамму', 'граммом', 'грамме',
        'литр', 'литра', 'литру', 'литром', 'литре',
        'штук', 'штука', 'штуку', 'штукой',
        'раз', 'раза', 'разу', 'разом',
        'год', 'года', 'году', 'годом', 'годе',
        'лет', 'годы', 'годам', 'годами'
    ]

    # Удаляем распространенные размерности и наименования
    for word in dimension_words:
        text = re.sub(r'\b' + word + r'\b', '', text)

    # Удаляем оставшиеся не-цифровые символы, кроме точек, запятых, дробей и математических знаков
    # Сохраняем цифры, точки, запятые, дроби, плюсы, минусы
    text = re.sub(r'[^\d\.,\/\+\-]', '', text)

    # Заменяем запятые на точки в десятичных числах
    text = text.replace(',', '.')

    # Нормализуем дроби: заменяем разные виды слешей на обычный /
    text = text.replace('÷', '/')
    text = text.replace('\\', '/')

    return text.strip()


def normalize_answer(answer):
    """Нормализует ответ для сравнения: извлекает числовое значение, игнорируя размерности"""
    if not answer:
        return ""

    # Извлекаем числовое значение
    normalized = extract_number_from_text(answer)

    # Если после извлечения ничего не осталось, возвращаем оригинал (нормализованный)
    if not normalized:
        # Применяем базовую нормализацию
        normalized = str(answer).strip().lower()
        normalized = normalized.replace(' ', '')
        normalized = normalized.replace(',', '.')
        normalized = normalized.replace('÷', '/')
        normalized = normalized.replace('\\', '/')
        # Убираем знаки препинания в конце
        if normalized.endswith(('.', '!', '?')):
            normalized = normalized[:-1]

    # Для дробей вида a b/c преобразуем в a+b/c
    if re.match(r'^\d+\.?\d*\s*\d+\.?\d*/\d+\.?\d*$', normalized):
        normalized = normalized.replace(' ', '+')

    return normalized


def check_answer(user_answer, correct_answer):
    """Проверяет ответ пользователя с нормализацией, игнорируя размерности"""
    user_norm = normalize_answer(user_answer)
    correct_norm = normalize_answer(correct_answer)

    print(f"DEBUG: user_answer='{user_answer}' -> normalized='{user_norm}'")
    print(
        f"DEBUG: correct_answer='{correct_answer}' -> normalized='{correct_norm}'")

    # Сначала сравниваем как есть
    if user_norm == correct_norm:
        return True, "✅ Правильно! Отличная работа!"

    try:
        # Пробуем сравнить как числа (для десятичных дробей)
        user_num = float(user_norm)
        correct_num = float(correct_norm)

        if abs(user_num - correct_num) < 0.001:  # Учитываем погрешность округления
            return True, "✅ Правильно! Отличная работа!"

    except (ValueError, TypeError):
        pass

    # Пробуем сравнить как дроби
    try:
        if '/' in user_norm and '/' in correct_norm:
            # Вычисляем числовое значение дробей
            def eval_fraction(frac):
                if '+' in frac:
                    # Смешанные дроби a+b/c
                    parts = frac.split('+')
                    whole = float(parts[0])
                    fraction_parts = parts[1].split('/')
                    return whole + float(fraction_parts[0]) / float(
                        fraction_parts[1])
                else:
                    # Простые дроби a/b
                    parts = frac.split('/')
                    return float(parts[0]) / float(parts[1])

            user_value = eval_fraction(user_norm)
            correct_value = eval_fraction(correct_norm)

            if abs(user_value - correct_value) < 0.001:
                return True, "✅ Правильно! Отличная работа!"

    except (ValueError, TypeError, ZeroDivisionError, IndexError):
        pass

    # Специальная обработка для случаев, когда в правильном ответе есть слова
    # Например: "на 21 рыбу" должно принимать "21"
    try:
        # Пробуем извлечь числа из обоих ответов
        user_numbers = re.findall(r'\d+\.?\d*', user_answer)
        correct_numbers = re.findall(r'\d+\.?\d*', correct_answer)

        if user_numbers and correct_numbers:
            # Берем первое найденное число из каждого ответа
            user_num = float(user_numbers[0])
            correct_num = float(correct_numbers[0])

            if abs(user_num - correct_num) < 0.001:
                return True, "✅ Правильно! Отличная работа!"
    except (ValueError, TypeError, IndexError):
        pass

    return False, f"❌ Неправильно. Ваш ответ: {user_answer}"


async def sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все разделы с задачами"""
    sections_data = db.get_all_sections()

    if not sections_data:
        error_text = "❌ Разделы с задачами не найдены."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
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

    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
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

    # Получаем название раздела
    section_name = "Неизвестный раздел"
    if problems:
        _, _, _, section_name_from_problem = problems[0]
        section_name = section_name_from_problem
    else:
        sections_data = db.get_all_sections()
        for section in sections_data:
            if section[0] == section_id:
                section_name = section[1]
                break

    if not problems:
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к разделам",
                                  callback_data="sections")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            f"❌ В разделе '{section_name}' нет задач.",
            reply_markup=reply_markup
        )
        return

    keyboard = []
    for problem in problems:
        problem_number, problem_text, correct_answer, _ = problem

        # 🔧 ИСПРАВЛЕНИЕ: приведение типов
        problem_text = str(problem_text)

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

    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
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
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к разделам",
                                  callback_data="sections")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "❌ Задача не найдена.",
            reply_markup=reply_markup
        )
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
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text,
                                                  reply_markup=reply_markup)


async def random_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает случайную задачу"""
    problem = db.get_random_problem()

    if not problem:
        error_text = "❌ Не удалось найти задачу. База данных пуста."
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню",
                                  callback_data="main_menu")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(error_text,
                                                          reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_text,
                                            reply_markup=reply_markup)
        return Config.WAITING_FOR_RANDOM_ANSWER

    problem_number, problem_text, correct_answer, section_name = problem

    # Сохраняем информацию о задаче в context для проверки ответа
    context.user_data['current_problem'] = problem
    context.user_data['problem_type'] = 'random'
    context.user_data['attempts_count'] = 0  # Счетчик попыток для этой задачи
    context.user_data['max_attempts'] = 3  # Максимальное количество попыток

    text = f"🎲 **Случайная задача**\n\n"
    text += f"**Раздел:** {section_name}\n"
    text += f"**Задача №{problem_number}:**\n{problem_text}\n\n"
    text += "💡 *Введите ваш ответ:*"
    text += f"\n\n🔄 *Попыток осталось: {context.user_data['max_attempts']}*"

    keyboard = [
        [InlineKeyboardButton("🔍 Показать ответ",
                              callback_data=f"show_answer_{problem_number}")],
        [InlineKeyboardButton("🎲 Другая случайная задача",
                              callback_data="random_problem")],
        [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
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
        keyboard = [
            [InlineKeyboardButton("🎲 Новая случайная задача",
                                  callback_data="random_problem")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ Ошибка: задача не найдена. Попробуйте получить новую задачу.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Увеличиваем счетчик попыток
    context.user_data['attempts_count'] = context.user_data.get(
        'attempts_count', 0) + 1
    attempts_count = context.user_data['attempts_count']
    max_attempts = context.user_data.get('max_attempts', 3)

    problem_number, problem_text, correct_answer, section_name = problem
    user = update.effective_user

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
        message_text = f"""
{message}

🎉 **Поздравляем!** Вы решили задачу с {attempts_count} попытки!

**Раздел:** {section_name}
**Задача №{problem_number}**

Выберите действие:
        """

        keyboard = [
            [InlineKeyboardButton("🎲 Новая случайная задача",
                                  callback_data="random_problem")],
            [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text,
                                        reply_markup=reply_markup)

        # Если ответ правильный, завершаем состояние
        context.user_data.pop('current_problem', None)
        context.user_data.pop('problem_type', None)
        context.user_data.pop('attempts_count', None)
        context.user_data.pop('max_attempts', None)
        return ConversationHandler.END

    else:
        remaining_attempts = max_attempts - attempts_count

        if remaining_attempts > 0:
            message_text = f"""
{message}

🔄 Попробуйте еще раз! 
Осталось попыток: {remaining_attempts}
Всего попыток для этой задачи: {db_attempt_number}

**Раздел:** {section_name}
**Задача №{problem_number}:** {problem_text}

Введите новый ответ:
            """

            keyboard = [
                [InlineKeyboardButton("🔍 Показать ответ",
                                      callback_data=f"show_answer_{problem_number}")],
                [InlineKeyboardButton("🎲 Другая случайная задача",
                                      callback_data="random_problem")],
                [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message_text,
                                            reply_markup=reply_markup)

            # Если остались попытки, остаемся в состоянии ожидания ответа
            return Config.WAITING_FOR_RANDOM_ANSWER

        else:
            # Закончились попытки
            message_text = f"""
{message}

❌ **Закончились попытки!** 
Максимальное количество попыток: {max_attempts}

**Правильный ответ:** {correct_answer}

**Раздел:** {section_name}
**Задача №{problem_number}**

Выберите действие:
            """

            keyboard = [
                [InlineKeyboardButton("🎲 Новая случайная задача",
                                      callback_data="random_problem")],
                [InlineKeyboardButton("📂 Все разделы", callback_data="sections")],
                [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message_text,
                                            reply_markup=reply_markup)

            # Завершаем состояние после исчерпания попыток
            context.user_data.pop('current_problem', None)
            context.user_data.pop('problem_type', None)
            context.user_data.pop('attempts_count', None)
            context.user_data.pop('max_attempts', None)
            return ConversationHandler.END
