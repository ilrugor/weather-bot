# 🤖 Telegram Weather Bot

Телеграм-бот, який показує погоду, зберігає історію в PostgreSQL, використовує Redis кеш і будує графіки.

---

## 🚀 Можливості

- 🌦 Отримання погоди через OpenWeather API  
- ⚡ Кешування запитів через Redis  
- 📊 Збереження історії погоди в PostgreSQL  
- 📈 Побудова графіків температур (matplotlib)  
- 📋 Статистика середньої температури  
- 🎲 Інтерактивне меню з кнопками  
- 🧠 ООП архітектура

---

## 🛠 Технології

- Python 3.10+
- python-telegram-bot
- PostgreSQL
- Redis
- pandas
- matplotlib
- requests
- psycopg2

---

## ⚙️ Встановлення

### 1. Клонувати репозиторій
```bash
git clone https://github.com/your-username/telegram-weather-bot.git
cd telegram-weather-bot
2. Встановити залежності
pip install -r requirements.txt
3. Налаштувати .env

Створи файл .env:

BOT_TOKEN=your_telegram_bot_token
WEATHER_API=your_openweather_api_key

DB_NAME=weather_bot
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
4. Запустити Redis
redis-server
5. Запустити бота
python tg_bot.py
📌 Команди бота
/start — головне меню
/weather Київ — погода
/stats Київ — середня температура
/plot Київ — графік
📊 Приклад роботи
Бот отримує погоду
Зберігає її в PostgreSQL
Кешує результат у Redis
Будує графік змін температури
🧠 Архітектура

Проєкт розділений на:

WeatherService — робота з API + Redis
Database — робота з PostgreSQL
TelegramBot — логіка бота
🔥 Автор

Учбовий проєкт з інтеграцією:

API
Баз даних
Кешування
Візуалізації
