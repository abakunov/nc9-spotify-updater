# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip --default-timeout=100 \ 
    && pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Запускаем скрипт
CMD ["python", "test.py"] 