# Foodgram - приложения для публикации рецептов

Приложениие было разработано в рамках прохождения курса Python-разработчик. Основная его цель закрепление наввыков работы с DjangoRestFramework, API, контеризации приложения через Docker и настройка CI/CD
Стек: Python 3.9.10, Django, DjangoRestFramework, Djoser, Docker, GitHub Actions. Для работы приложения необходимо установить Docker. Работа приложения настроена на СУБД PostgreSQL

# Инструкция по развертываю:
1. Клонировать репозиторий
2. В папке /backend развернуть виртуальное окружение:

   команда для Windows:
   ```
   python -m venv venv
   ```
   команда для Linux:
   ```
   python3 -m venv venv
   ```
4. Активировать виртуальное окружение:

   команда для Windows:
   ```
   source venv/Scripts/activate
   ```
   команда для Linux:
   ```
   source venv/bin/activate
   ```
5. Установить зависимости из файла requirements.txt:
   ```
   pip install -r requirements.txt
   ```
6. Создать в корне проекта файл .env который должен содержать настройки для работы с СУБД и следующие константы для настроек Django: SECRET_KEY, DEBUG, ALLOWED_HOSTS
7. Ативировать докер
8. Запустить работу приложения в контейнерах командой находясь в корне проекта:
   ```
   docker compose -f docker-compose.yml up
   ```
9. При первом звпуске выполнить миграции:
    ```
    docker compose -f docker-compose.production.yml exec backend python manage.py migrate
    ```
