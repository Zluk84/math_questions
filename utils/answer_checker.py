import re


def normalize_answer(answer):
    """
    Нормализует ответ для сравнения:
    - Приводит к нижнему регистру
    - Убирает все знаки препинания
    - Заменяет запятые на точки для чисел
    - Убирает единицы измерения
    - Сортирует множественные ответы
    """
    if not answer:
        return ""

    # Приводим к нижнему регистру и убираем пробелы
    normalized = answer.strip().lower()

    # Убираем все знаки препинания кроме точек, запятых и дефисов (для отрицательных чисел)
    normalized = re.sub(r'[^\w\s.,-]', '', normalized)

    # Заменяем запятые на точки для десятичных дробей
    normalized = normalized.replace(',', '.')

    # Убираем единицы измерения (км/ч, кг, м и т.д.)
    units = ['км/ч', 'км', 'м', 'см', 'мм', 'кг', 'г', 'т', 'ц', 'га', 'м²',
             'см²', 'мм²', 'л', 'ч', 'мин', 'с', 'руб', '°']
    for unit in units:
        normalized = normalized.replace(unit, '')

    # Если ответ содержит несколько чисел через точку с запятой или другие разделители
    if ';' in normalized or ' и ' in normalized or ',' in normalized:
        # Заменяем разные разделители на стандартный
        normalized = re.sub(r'[,\sи]+', ';', normalized)
        # Разбиваем на части, сортируем и объединяем обратно
        parts = normalized.split(';')
        parts = [part.strip() for part in parts if part.strip()]

        # Пытаемся отсортировать как числа, если возможно
        try:
            # Сортируем как числа
            parts_sorted = sorted([float(part) for part in parts])
            normalized = ';'.join(str(part) for part in parts_sorted)
        except (ValueError, TypeError):
            # Если не числа, сортируем как строки
            parts.sort()
            normalized = ';'.join(parts)

    # Убираем лишние пробелы и нормализуем пробелы вокруг разделителей
    normalized = re.sub(r'\s+', ' ', normalized.strip())
    normalized = re.sub(r'\s*;\s*', ';', normalized)

    return normalized


def check_answer(user_answer, correct_answer):
    """
    Проверяет правильность ответа пользователя с учетом:
    - Разных форматов десятичных дробей (точка/запятая)
    - Отсутствия учета знаков препинания
    - Разного порядка в множественных ответах
    - Единиц измерения
    - Небольших погрешностей для чисел

    Args:
        user_answer (str): Ответ пользователя
        correct_answer (str): Правильный ответ из базы

    Returns:
        tuple: (bool, str) - (правильно/неправильно, сообщение)
    """
    if not user_answer or not correct_answer:
        return False, "❌ Ответ не может быть пустым"

    # Нормализуем оба ответа
    user_norm = normalize_answer(user_answer)
    correct_norm = normalize_answer(correct_answer)

    # Если ответы полностью совпадают после нормализации
    if user_norm == correct_norm:
        return True, "✅ Правильно! Отличная работа!"

    # Проверяем числовые ответы (одиночные числа)
    try:
        # Пытаемся преобразовать в числа
        user_num = float(user_norm)
        correct_num = float(correct_norm)

        # Допускаем погрешность 0.1% для вещественных чисел
        tolerance = abs(correct_num) * 0.001
        if abs(user_num - correct_num) <= tolerance:
            return True, "✅ Правильно! Отличная работа!"

    except (ValueError, TypeError):
        pass

    # Проверяем множественные числовые ответы (через разделители)
    if ';' in user_norm and ';' in correct_norm:
        try:
            user_parts = [float(x.strip()) for x in user_norm.split(';')]
            correct_parts = [float(x.strip()) for x in correct_norm.split(';')]

            # Сортируем оба списка для сравнения без учета порядка
            user_parts_sorted = sorted(user_parts)
            correct_parts_sorted = sorted(correct_parts)

            # Проверяем совпадение с учетом погрешности
            if len(user_parts_sorted) == len(correct_parts_sorted):
                all_match = True
                for u, c in zip(user_parts_sorted, correct_parts_sorted):
                    tolerance = abs(c) * 0.001
                    if abs(u - c) > tolerance:
                        all_match = False
                        break

                if all_match:
                    return True, "✅ Правильно! Отличная работа!"

        except (ValueError, TypeError):
            pass

    # Проверяем дробные ответы в разных формаats
    if '/' in user_norm or '/' in correct_norm:
        try:
            # Пытаемся преобразовать дроби в десятичные числа
            def fraction_to_float(frac_str):
                if '/' in frac_str:
                    num, denom = frac_str.split('/')
                    return float(num) / float(denom)
                else:
                    return float(frac_str)

            user_frac = fraction_to_float(user_norm)
            correct_frac = fraction_to_float(correct_norm)

            tolerance = abs(correct_frac) * 0.001
            if abs(user_frac - correct_frac) <= tolerance:
                return True, "✅ Правильно! Отличная работа!"

        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # Проверяем ответы с процентами
    if '%' in user_answer or '%' in correct_answer:
        try:
            # Извлекаем числа из строк с процентами
            user_percent = float(re.sub(r'[^\d.]', '', user_answer))
            correct_percent = float(re.sub(r'[^\d.]', '', correct_answer))

            tolerance = abs(correct_percent) * 0.001
            if abs(user_percent - correct_percent) <= tolerance:
                return True, "✅ Правильно! Отличная работа!"

        except (ValueError, TypeError):
            pass

    # Проверяем текстовые ответы (игнорируя регистр и знаки препинания)
    user_text = re.sub(r'[^\w\s]', '', user_answer.lower()).strip()
    correct_text = re.sub(r'[^\w\s]', '', correct_answer.lower()).strip()

    if user_text == correct_text:
        return True, "✅ Правильно! Отличная работа!"

    # Проверяем частичное совпадение для текстовых ответов
    words_user = set(user_text.split())
    words_correct = set(correct_text.split())

    if words_user and words_correct and words_user == words_correct:
        return True, "✅ Правильно! Отличная работа!"

    return False, f"❌ Неправильно. Попробуйте еще раз!"
