import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MathProblemsDB:
    def __init__(self, db_path='math_problems.db'):
        self.db_path = db_path
        self.create_tables()
        self.init_user_stats_table()
        self.init_user_attempts_table()
        self.update_database_schema()

    def create_tables(self):
        """Создает основные таблицы для задач и разделов"""
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
        logger.info("Основные таблицы созданы успешно")

    def init_user_stats_table(self):
        """Инициализирует таблицу статистики пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                total_attempts INTEGER DEFAULT 0,
                correct_attempts INTEGER DEFAULT 0,
                unique_solved_problems INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def init_user_attempts_table(self):
        """Инициализирует таблицу всех попыток пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                problem_number INTEGER,
                user_answer TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN,
                attempt_number INTEGER DEFAULT 1,
                solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
            )
        ''')
        # Создаем индексы для быстрого поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_attempts 
            ON user_attempts (user_id, problem_number, solved_at)
        ''')
        conn.commit()
        conn.close()

    def update_database_schema(self):
        """Обновляет схему базы данных, добавляя недостающие колонки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем существование колонок в user_stats
        cursor.execute("PRAGMA table_info(user_stats)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'unique_solved_problems' not in columns:
            cursor.execute(
                'ALTER TABLE user_stats ADD COLUMN unique_solved_problems INTEGER DEFAULT 0')
            logger.info(
                "Добавлена колонка unique_solved_problems в user_stats")

        conn.commit()
        conn.close()

    def update_user_stats(self, user_id, username, first_name, last_name,
                          is_correct=False, problem_number=None):
        """Обновляет статистику пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Проверяем существование пользователя
        cursor.execute('SELECT * FROM user_stats WHERE user_id = ?',
                       (user_id,))
        user_exists = cursor.fetchone()

        if user_exists:
            # Обновляем существующего пользователя
            if is_correct:
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_attempts = total_attempts + 1,
                        correct_attempts = correct_attempts + 1,
                        last_activity = CURRENT_TIMESTAMP,
                        username = ?, first_name = ?, last_name = ?
                    WHERE user_id = ?
                ''', (username, first_name, last_name, user_id))

                # Обновляем счетчик уникальных решенных задач
                if problem_number:
                    cursor.execute('''
                        SELECT COUNT(DISTINCT problem_number) 
                        FROM user_attempts 
                        WHERE user_id = ? AND is_correct = 1
                    ''', (user_id,))
                    unique_solved = cursor.fetchone()[0] or 0

                    cursor.execute('''
                        UPDATE user_stats 
                        SET unique_solved_problems = ?
                        WHERE user_id = ?
                    ''', (unique_solved, user_id))
            else:
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_attempts = total_attempts + 1,
                        last_activity = CURRENT_TIMESTAMP,
                        username = ?, first_name = ?, last_name = ?
                    WHERE user_id = ?
                ''', (username, first_name, last_name, user_id))
        else:
            # Добавляем нового пользователя
            if is_correct:
                cursor.execute('''
                    INSERT INTO user_stats 
                    (user_id, username, first_name, last_name, total_attempts, correct_attempts, unique_solved_problems, last_activity)
                    VALUES (?, ?, ?, ?, 1, 1, 1, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name))
            else:
                cursor.execute('''
                    INSERT INTO user_stats 
                    (user_id, username, first_name, last_name, total_attempts, correct_attempts, unique_solved_problems, last_activity)
                    VALUES (?, ?, ?, ?, 1, 0, 0, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name))

        conn.commit()
        conn.close()

    def add_user_attempt(self, user_id, problem_number, user_answer,
                         correct_answer, is_correct, attempt_number=1):
        """Добавляет запись о попытке решения задачи пользователем"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Получаем номер попытки для этой задачи
        cursor.execute('''
            SELECT COUNT(*) FROM user_attempts 
            WHERE user_id = ? AND problem_number = ?
        ''', (user_id, problem_number))

        current_attempt = cursor.fetchone()[0] + 1

        # Добавляем новую запись о попытке
        cursor.execute('''
            INSERT INTO user_attempts (user_id, problem_number, user_answer, correct_answer, is_correct, attempt_number)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, problem_number, user_answer, correct_answer, is_correct,
              current_attempt))

        conn.commit()
        conn.close()

        return current_attempt

    def get_user_attempts_for_problem(self, user_id, problem_number):
        """Получает все попытки пользователя для конкретной задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_answer, correct_answer, is_correct, attempt_number, solved_at 
            FROM user_attempts 
            WHERE user_id = ? AND problem_number = ?
            ORDER BY attempt_number
        ''', (user_id, problem_number))

        attempts = cursor.fetchall()
        conn.close()

        return [{
            'user_answer': attempt[0],
            'correct_answer': attempt[1],
            'is_correct': bool(attempt[2]),
            'attempt_number': attempt[3],
            'solved_at': attempt[4]
        } for attempt in attempts]

    def get_last_user_attempt(self, user_id, problem_number):
        """Получает последнюю попытку пользователя для задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_answer, correct_answer, is_correct, attempt_number, solved_at 
            FROM user_attempts 
            WHERE user_id = ? AND problem_number = ?
            ORDER BY attempt_number DESC 
            LIMIT 1
        ''', (user_id, problem_number))

        attempt = cursor.fetchone()
        conn.close()

        if attempt:
            return {
                'user_answer': attempt[0],
                'correct_answer': attempt[1],
                'is_correct': bool(attempt[2]),
                'attempt_number': attempt[3],
                'solved_at': attempt[4]
            }
        return None

    def is_problem_solved_by_user(self, user_id, problem_number):
        """Проверяет, решал ли пользователь уже эту задачу правильно"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM user_attempts 
            WHERE user_id = ? AND problem_number = ? AND is_correct = 1
        ''', (user_id, problem_number))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_user_attempts_count(self, user_id, problem_number):
        """Получает количество попыток пользователя для задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM user_attempts 
            WHERE user_id = ? AND problem_number = ?
        ''', (user_id, problem_number))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_user_recent_attempts(self, user_id, limit=10):
        """Получает последние попытки пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ua.problem_number, ua.user_answer, ua.correct_answer, 
                   ua.is_correct, ua.attempt_number, ua.solved_at, p.problem_text
            FROM user_attempts ua
            LEFT JOIN problems p ON ua.problem_number = p.problem_number
            WHERE ua.user_id = ?
            ORDER BY ua.solved_at DESC
            LIMIT ?
        ''', (user_id, limit))

        attempts = cursor.fetchall()
        conn.close()

        return [{
            'problem_number': attempt[0],
            'user_answer': attempt[1],
            'correct_answer': attempt[2],
            'is_correct': bool(attempt[3]),
            'attempt_number': attempt[4],
            'solved_at': attempt[5],
            'problem_text': attempt[6] or f"Задача {attempt[0]}"
        } for attempt in attempts]

    def get_user_all_attempts(self, user_id):
        """Получает все попытки пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT problem_number, user_answer, correct_answer, is_correct, 
                   attempt_number, solved_at
            FROM user_attempts 
            WHERE user_id = ?
            ORDER BY solved_at DESC
        ''', (user_id,))

        attempts = cursor.fetchall()
        conn.close()

        return [{
            'problem_number': attempt[0],
            'user_answer': attempt[1],
            'correct_answer': attempt[2],
            'is_correct': bool(attempt[3]),
            'attempt_number': attempt[4],
            'solved_at': attempt[5]
        } for attempt in attempts]

    def get_user_stats(self, user_id):
        """Получает статистику пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Основная статистика
        cursor.execute('''
            SELECT total_attempts, correct_attempts, unique_solved_problems, last_activity 
            FROM user_stats WHERE user_id = ?
        ''', (user_id,))
        stats = cursor.fetchone()

        if not stats:
            conn.close()
            return None

        total_attempts, correct_attempts, unique_solved, last_activity = stats

        # Дополнительная статистика из попыток
        cursor.execute('''
            SELECT COUNT(DISTINCT problem_number) 
            FROM user_attempts 
            WHERE user_id = ?
        ''', (user_id,))
        total_problems_attempted = cursor.fetchone()[0] or 0

        # Среднее количество попыток на задачу
        cursor.execute('''
            SELECT problem_number, COUNT(*) 
            FROM user_attempts 
            WHERE user_id = ? 
            GROUP BY problem_number
        ''', (user_id,))
        attempts_per_problem = cursor.fetchall()

        avg_attempts = 0
        if attempts_per_problem:
            avg_attempts = sum(
                count for _, count in attempts_per_problem) / len(
                attempts_per_problem)

        # Статистика по дням
        cursor.execute('''
            SELECT DATE(solved_at), COUNT(*) 
            FROM user_attempts 
            WHERE user_id = ? 
            GROUP BY DATE(solved_at)
            ORDER BY DATE(solved_at) DESC
            LIMIT 7
        ''', (user_id,))
        last_7_days = cursor.fetchall()

        conn.close()

        success_rate = (
                    correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        unique_success_rate = (
                    unique_solved / total_problems_attempted * 100) if total_problems_attempted > 0 else 0

        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'success_rate': round(success_rate, 1),
            'unique_solved_problems': unique_solved,
            'total_problems_attempted': total_problems_attempted,
            'unique_success_rate': round(unique_success_rate, 1),
            'avg_attempts_per_problem': round(avg_attempts, 1),
            'last_7_days_activity': last_7_days,
            'last_activity': last_activity
        }

    def get_user_problem_statistics(self, user_id, problem_number):
        """Получает статистику пользователя по конкретной задаче"""
        attempts = self.get_user_attempts_for_problem(user_id, problem_number)

        if not attempts:
            return None

        total_attempts = len(attempts)
        correct_attempts = sum(
            1 for attempt in attempts if attempt['is_correct'])
        first_correct_attempt = next(
            (attempt for attempt in attempts if attempt['is_correct']), None)

        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'is_solved': correct_attempts > 0,
            'first_correct_attempt': first_correct_attempt,
            'all_attempts': attempts
        }

    def get_leaderboard(self, limit=10):
        """Получает таблицу лидеров"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, first_name, total_attempts, correct_attempts, unique_solved_problems 
            FROM user_stats 
            WHERE total_attempts >= 5 
            ORDER BY unique_solved_problems DESC, correct_attempts DESC, total_attempts ASC 
            LIMIT ?
        ''', (limit,))
        leaders = cursor.fetchall()
        conn.close()

        return [{
            'username': leader[0],
            'first_name': leader[1],
            'total_attempts': leader[2],
            'correct_attempts': leader[3],
            'unique_solved': leader[4]
        } for leader in leaders]

    # Остальные методы остаются без изменений
    def get_all_sections(self):
        """Получить все разделы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sections ORDER BY id')
        sections = cursor.fetchall()
        conn.close()
        return sections

    def get_problems_by_section(self, section_id):
        """Получить все задачи из определенного раздела"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.problem_number, p.problem_text, p.answer 
            FROM problems p 
            WHERE p.section_id = ? 
            ORDER BY p.problem_number
        ''', (section_id,))
        problems = cursor.fetchall()
        conn.close()
        return problems

    def get_problem_by_number(self, problem_number):
        """Найти задачу по номеру"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.problem_number, p.problem_text, p.answer, s.name 
            FROM problems p 
            JOIN sections s ON p.section_id = s.id 
            WHERE p.problem_number = ?
        ''', (problem_number,))
        problem = cursor.fetchone()
        conn.close()
        return problem

    def search_problems(self, keyword):
        """Поиск задач по ключевому слову"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.problem_number, p.problem_text, p.answer, s.name 
            FROM problems p 
            JOIN sections s ON p.section_id = s.id 
            WHERE p.problem_text LIKE ? OR p.answer LIKE ?
            ORDER BY p.problem_number
        ''', (f'%{keyword}%', f'%{keyword}%'))
        problems = cursor.fetchall()
        conn.close()
        return problems

    def get_random_problem(self):
        """Получить случайную задачу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.problem_number, p.problem_text, p.answer, s.name 
            FROM problems p 
            JOIN sections s ON p.section_id = s.id 
            ORDER BY RANDOM() 
            LIMIT 1
        ''')
        problem = cursor.fetchone()
        conn.close()
        return problem

    def get_random_unsolved_problem(self, user_id):
        """Получить случайную нерешенную задачу для пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.problem_number, p.problem_text, p.answer, s.name 
            FROM problems p 
            JOIN sections s ON p.section_id = s.id 
            WHERE p.problem_number NOT IN (
                SELECT problem_number FROM user_attempts WHERE user_id = ? AND is_correct = 1
            )
            ORDER BY RANDOM() 
            LIMIT 1
        ''', (user_id,))
        problem = cursor.fetchone()
        conn.close()
        return problem

    # ... существующие методы остаются без изменений до этого места ...

    # ДОБАВЛЕННЫЕ МЕТОДЫ ДЛЯ АДМИНИСТРАТОРА

    def get_all_users_stats(self, limit=100):
        """Получает статистику всех пользователей (для админа)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, 
                   total_attempts, correct_attempts, unique_solved_problems,
                   last_activity, created_at
            FROM user_stats 
            ORDER BY last_activity DESC
            LIMIT ?
        ''', (limit,))
        users = cursor.fetchall()
        conn.close()

        return [{
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'total_attempts': user[4],
            'correct_attempts': user[5],
            'unique_solved': user[6],
            'last_activity': user[7],
            'created_at': user[8]
        } for user in users]

    def get_user_attempts_by_date(self, user_id, date=None):
        """Получает попытки пользователя за конкретную дату"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if date:
            cursor.execute('''
                SELECT problem_number, user_answer, correct_answer, is_correct, 
                       attempt_number, solved_at
                FROM user_attempts 
                WHERE user_id = ? AND DATE(solved_at) = ?
                ORDER BY solved_at DESC
            ''', (user_id, date))
        else:
            cursor.execute('''
                SELECT problem_number, user_answer, correct_answer, is_correct, 
                       attempt_number, solved_at
                FROM user_attempts 
                WHERE user_id = ?
                ORDER BY solved_at DESC
            ''', (user_id,))

        attempts = cursor.fetchall()
        conn.close()

        return [{
            'problem_number': attempt[0],
            'user_answer': attempt[1],
            'correct_answer': attempt[2],
            'is_correct': bool(attempt[3]),
            'attempt_number': attempt[4],
            'solved_at': attempt[5]
        } for attempt in attempts]

    def get_user_daily_activity(self, user_id, days=7):
        """Получает ежедневную активность пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DATE(solved_at), COUNT(*), SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
            FROM user_attempts 
            WHERE user_id = ? AND solved_at >= DATE('now', ?)
            GROUP BY DATE(solved_at)
            ORDER BY DATE(solved_at) DESC
        ''', (user_id, f'-{days} days'))

        activity = cursor.fetchall()
        conn.close()

        return [{
            'date': day[0],
            'total_attempts': day[1],
            'correct_attempts': day[2]
        } for day in activity]

    def delete_user_attempts(self, user_id, problem_number=None, date=None):
        """Удаляет попытки пользователя (для админа)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if problem_number and date:
                # Удалить попытки по конкретной задаче за конкретную дату
                cursor.execute('''
                    DELETE FROM user_attempts 
                    WHERE user_id = ? AND problem_number = ? AND DATE(solved_at) = ?
                ''', (user_id, problem_number, date))
            elif problem_number:
                # Удалить все попытки по конкретной задаче
                cursor.execute('''
                    DELETE FROM user_attempts 
                    WHERE user_id = ? AND problem_number = ?
                ''', (user_id, problem_number))
            elif date:
                # Удалить все попытки за конкретную дату
                cursor.execute('''
                    DELETE FROM user_attempts 
                    WHERE user_id = ? AND DATE(solved_at) = ?
                ''', (user_id, date))
            else:
                # Удалить все попытки пользователя
                cursor.execute('DELETE FROM user_attempts WHERE user_id = ?',
                               (user_id,))
                cursor.execute('DELETE FROM user_stats WHERE user_id = ?',
                               (user_id,))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            return deleted_count

        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Ошибка при удалении попыток: {e}")
            return 0

    def get_user_detailed_stats(self, user_id):
        """Получает детальную статистику пользователя (для админа)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Основная статистика
        cursor.execute('''
            SELECT username, first_name, last_name, total_attempts, 
                   correct_attempts, unique_solved_problems, last_activity, created_at
            FROM user_stats WHERE user_id = ?
        ''', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            conn.close()
            return None

        # Статистика по дням
        cursor.execute('''
            SELECT DATE(solved_at), COUNT(*), SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
            FROM user_attempts 
            WHERE user_id = ?
            GROUP BY DATE(solved_at)
            ORDER BY DATE(solved_at) DESC
            LIMIT 30
        ''', (user_id,))
        daily_stats = cursor.fetchall()

        # Статистика по задачам
        cursor.execute('''
            SELECT problem_number, 
                   COUNT(*) as total_attempts,
                   SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_attempts,
                   MIN(solved_at) as first_attempt,
                   MAX(solved_at) as last_attempt
            FROM user_attempts 
            WHERE user_id = ?
            GROUP BY problem_number
            ORDER BY total_attempts DESC
            LIMIT 20
        ''', (user_id,))
        problem_stats = cursor.fetchall()

        conn.close()

        return {
            'user_info': {
                'username': user_data[0],
                'first_name': user_data[1],
                'last_name': user_data[2],
                'total_attempts': user_data[3],
                'correct_attempts': user_data[4],
                'unique_solved': user_data[5],
                'last_activity': user_data[6],
                'created_at': user_data[7]
            },
            'daily_stats': [{
                'date': day[0],
                'total_attempts': day[1],
                'correct_attempts': day[2]
            } for day in daily_stats],
            'problem_stats': [{
                'problem_number': problem[0],
                'total_attempts': problem[1],
                'correct_attempts': problem[2],
                'first_attempt': problem[3],
                'last_attempt': problem[4]
            } for problem in problem_stats]
        }
