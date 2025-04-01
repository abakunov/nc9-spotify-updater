# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \ 
    && pip install --no-cache-dir -r requirements.txt


# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Запускаем скрипт
CMD ["python", "test.py"] 