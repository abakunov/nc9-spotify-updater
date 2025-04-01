FROM python:3.9

WORKDIR /app

# Сначала копируем только requirements.txt для лучшего кэширования
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
       --retries 5 \
       --timeout 100 \
       -i https://pypi.tuna.tsinghua.edu.cn/simple \
       --trusted-host pypi.tuna.tsinghua.edu.cn \
       -r requirements.txt

# Копируем остальные файлы
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "test.py"]