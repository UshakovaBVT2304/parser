# Используйте официальный образ Python как базовый образ
FROM python:3.8-slim

# Установите рабочий каталог в контейнере
WORKDIR /app

# Скопируйте файлы из текущей директории в рабочую директорию в контейнере
COPY . /app

# Установите зависимости из файла requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Команда, которая будет выполнена при запуске контейнера
CMD ["python", "main.py"]
