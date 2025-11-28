import sqlite3
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    def __init__(self, db_path='math_problems.db', data_file_path=None):
        self.db_path = db_path
        self.data_file_path = data_file_path or self.find_data_file()

    def find_data_file(self):
        """Находит файл с данными задач"""
        possible_paths = [
            'Выговская В.В. - Сборник практических задач по математике. 6 класс - 2012.txt',
            '../Выговская В.В. - Сборник практических задач по математике. 6 класс - 2012.txt',
            'data/Выговская В.В. - Сборник практических задач по математике. 6 класс - 2012.txt'
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path
        return None

    def create_tables(self):
        """Создает таблицы в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица разделов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT
            )
        ''')

        # Таблица задач
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                problem_number INTEGER NOT NULL,
                problem_text TEXT NOT NULL,
                answer TEXT NOT NULL,
                difficulty_level VARCHAR(20) DEFAULT 'средняя',
                FOREIGN KEY (section_id) REFERENCES sections(id),
                UNIQUE(section_id, problem_number)
            )
        ''')

        # Создаем индексы для быстрого поиска
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_problem_number ON problems(problem_number)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_section_id ON problems(section_id)')

        conn.commit()
        conn.close()
        logger.info("Таблицы созданы успешно")

    def parse_problems_file(self):
        """Парсит файл с задачами и возвращает структурированные данные"""
        if not self.data_file_path or not Path(self.data_file_path).exists():
            logger.error(f"Файл с задачами не найден: {self.data_file_path}")
            return None

        with open(self.data_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Разделяем на разделы
        sections = []
        current_section = None
        problems = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Ищем начало раздела
            if line.startswith('РАЗДЕЛ'):
                if current_section and problems:
                    sections.append({
                        'name': current_section,
                        'problems': problems.copy()
                    })
                    problems = []

                # Извлекаем название раздела
                section_match = re.match(r'РАЗДЕЛ\s+\d+:\s*(.+)', line)
                if section_match:
                    current_section = section_match.group(1).strip()
                else:
                    current_section = line.replace('РАЗДЕЛ', '').replace(':',
                                                                         '').strip()

                i += 1
                continue

            # Ищем задачи
            if line.startswith('ЗАДАЧА:'):
                problem_data = {'problem_text': '', 'answer': ''}

                # Извлекаем номер задачи
                problem_match = re.match(r'ЗАДАЧА:\s*(\d+)\s*\|\s*(.+)', line)
                if problem_match:
                    problem_number = int(problem_match.group(1))
                    problem_text_start = problem_match.group(2)
                    problem_data['number'] = problem_number
                    problem_data['problem_text'] = problem_text_start
                else:
                    # Альтернативный формат
                    problem_match = re.match(r'ЗАДАЧА:\s*(\d+)\s*', line)
                    if problem_match:
                        problem_data['number'] = int(problem_match.group(1))
                        i += 1
                        if i < len(lines):
                            problem_data['problem_text'] = lines[i].strip()
                    else:
                        i += 1
                        continue

                # Ищем ответ
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('ОТВЕТ:'):
                        answer_match = re.match(r'ОТВЕТ:\s*(.+)', next_line)
                        if answer_match:
                            problem_data['answer'] = answer_match.group(
                                1).strip()
                        break
                    elif next_line.startswith(
                            'ЗАДАЧА:') or next_line.startswith(
                            'РАЗДЕЛ') or not next_line:
                        break
                    else:
                        if not problem_data['problem_text']:
                            problem_data['problem_text'] = next_line
                        else:
                            problem_data['problem_text'] += ' ' + next_line
                    i += 1

                # Очищаем и форматируем текст задачи
                if problem_data['problem_text'] and problem_data['answer']:
                    problem_data['problem_text'] = self.clean_problem_text(
                        problem_data['problem_text'])
                    problem_data['answer'] = self.clean_answer(
                        problem_data['answer'])
                    problems.append(problem_data)

            i += 1

        # Добавляем последний раздел
        if current_section and problems:
            sections.append({
                'name': current_section,
                'problems': problems.copy()
            })

        logger.info(f"Найдено разделов: {len(sections)}")
        total_problems = sum(len(section['problems']) for section in sections)
        logger.info(f"Всего задач: {total_problems}")

        return sections

    def clean_problem_text(self, text):
        """Очищает и форматирует текст задачи"""
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()

        # Убираем маркеры типа "|" в начале строки
        text = re.sub(r'^\|\s*', '', text)

        # Обеспечиваем правильную пунктуацию
        if not text.endswith(('.', '!', '?')):
            text += '.'

        return text

    def clean_answer(self, answer):
        """Очищает и форматирует ответ"""
        # Убираем лишние пробелы
        answer = re.sub(r'\s+', ' ', answer).strip()

        # Убираем маркеры типа "|" в начале строки
        answer = re.sub(r'^\|\s*', '', answer)

        # Нормализуем десятичные дроби (запятая -> точка)
        answer = re.sub(r'(\d),(\d)', r'\1.\2', answer)

        return answer

    def determine_difficulty(self, problem_text, problem_number):
        """Определяет сложность задачи на основе ее содержания и номера"""
        easy_keywords = ['скорость', 'расстояние', 'время', 'процент', 'доля',
                         'часть']
        hard_keywords = ['система', 'уравнение', 'пропорция', 'производная',
                         'интеграл', 'комбинаторика']

        text_lower = problem_text.lower()

        # Первые 50 задач обычно проще
        if problem_number <= 50:
            base_level = 'легкая'
        elif problem_number <= 150:
            base_level = 'средняя'
        else:
            base_level = 'сложная'

        # Корректируем на основе ключевых слов
        if any(keyword in text_lower for keyword in hard_keywords):
            return 'сложная'
        elif any(keyword in text_lower for keyword in easy_keywords):
            return 'легкая'
        else:
            return base_level

    def insert_data(self, sections_data):
        """Вставляет данные в базу данных"""
        if not sections_data:
            logger.error("Нет данных для вставки")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Очищаем существующие данные
            cursor.execute('DELETE FROM problems')
            cursor.execute('DELETE FROM sections')

            # Вставляем разделы и задачи
            for section_idx, section in enumerate(sections_data, 1):
                # Вставляем раздел
                cursor.execute(
                    'INSERT INTO sections (id, name) VALUES (?, ?)',
                    (section_idx, section['name'])
                )

                # Вставляем задачи раздела
                for problem in section['problems']:
                    difficulty = self.determine_difficulty(
                        problem['problem_text'],
                        problem['number']
                    )

                    cursor.execute('''
                        INSERT INTO problems (section_id, problem_number, problem_text, answer, difficulty_level)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        section_idx,
                        problem['number'],
                        problem['problem_text'],
                        problem['answer'],
                        difficulty
                    ))

            conn.commit()
            logger.info("Данные успешно загружены в базу данных")
            return True

        except Exception as e:
            logger.error(f"Ошибка при вставке данных: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def verify_data(self):
        """Проверяет целостность данных в базе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем разделы
        cursor.execute('SELECT COUNT(*) FROM sections')
        section_count = cursor.fetchone()[0]

        # Проверяем задачи
        cursor.execute('SELECT COUNT(*) FROM problems')
        problem_count = cursor.fetchone()[0]

        # Проверяем распределение по разделам
        cursor.execute('''
            SELECT s.name, COUNT(p.id) 
            FROM sections s 
            LEFT JOIN problems p ON s.id = p.section_id 
            GROUP BY s.id, s.name
        ''')
        distribution = cursor.fetchall()

        conn.close()

        logger.info(f"Разделов в базе: {section_count}")
        logger.info(f"Задач в базе: {problem_count}")
        logger.info("Распределение задач по разделам:")
        for section_name, count in distribution:
            logger.info(f"  {section_name}: {count} задач")

        return section_count > 0 and problem_count > 0

    def initialize_database(self):
        """Основной метод инициализации базы данных"""
        logger.info("Начинаем инициализацию базы данных...")

        # Создаем таблицы
        self.create_tables()

        # Парсим файл с задачами
        sections_data = self.parse_problems_file()
        if not sections_data:
            logger.error("Не удалось распарсить файл с задачами")
            return False

        # Вставляем данные
        success = self.insert_data(sections_data)
        if not success:
            logger.error("Не удалось вставить данные в базу")
            return False

        # Проверяем целостность
        if self.verify_data():
            logger.info("База данных успешно инициализирована!")
            return True
        else:
            logger.error("Проверка целостности данных не пройдена")
            return False


def main():
    """Точка входа для ручной инициализации базы данных"""
    import sys

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Определяем путь к файлу с данными, если передан как аргумент
    data_file = sys.argv[1] if len(sys.argv) > 1 else None

    initializer = DatabaseInitializer(data_file_path=data_file)

    if initializer.initialize_database():
        print("✅ База данных успешно создана и заполнена!")
        print(f"📁 Файл базы данных: {initializer.db_path}")
    else:
        print("❌ Ошибка при создании базы данных")
        sys.exit(1)


if __name__ == "__main__":
    main()
