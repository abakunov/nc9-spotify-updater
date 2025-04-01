FROM python:3.9

WORKDIR /app

# Сначала копируем только requirements.txt для лучшего кэширования
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Копируем остальные файлы
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "test.py"]