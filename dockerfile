FROM python:3.11-slim

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Переменные окружения (будут задаваться извне)
ENV BOT_TOKEN=""
ENV ADMIN_ID=""
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "main.py"]
