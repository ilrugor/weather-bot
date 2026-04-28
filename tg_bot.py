import os
import asyncio
import requests
import redis
import psycopg2
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        self.cur = self.conn.cursor()

    def save_weather(self, city, temp):
        try:
            self.cur.execute(
                "INSERT INTO weather (city, temp) VALUES (%s, %s)",
                (city, temp)
            )
            self.conn.commit()
        except Exception as e:
            print("DB save error:", e)

    def get_avg_temp(self, city):
        try:
            self.cur.execute(
                "SELECT AVG(temp) FROM weather WHERE LOWER(city)=LOWER(%s)",
                (city,)
            )
            result = self.cur.fetchone()[0]
            return result
        except Exception as e:
            print("DB avg error:", e)
            return None

    def get_last_records(self, city):
        try:
            self.cur.execute(
                """
                SELECT temp, created_at
                FROM weather
                WHERE LOWER(city)=LOWER(%s)
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (city,)
            )
            return self.cur.fetchall()
        except Exception as e:
            print("DB records error:", e)
            return []


class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

    def get_weather(self, city: str):
        cache_key = f"weather:{city.lower()}"

        try:
            cached = self.redis.get(cache_key)
            if cached:
                return cached, True, None
        except Exception as e:
            print("Redis error:", e)

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",
                "lang": "ua"
            }

            r = requests.get(url, params=params, timeout=10)

            if r.status_code == 404:
                return "❌ Місто не знайдено", False, None

            if r.status_code != 200:
                return "⚠️ Проблема з сервером погоди", False, None

            data = r.json()

        except requests.exceptions.Timeout:
            return "⏳ Сервер не відповідає", False, None
        except requests.exceptions.ConnectionError:
            return "🌐 Немає інтернету", False, None
        except Exception as e:
            print("API error:", e)
            return "⚠️ Помилка API", False, None

        try:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            result = f"🌦 Погода в {city}:\n🌡 Температура: {temp}°C\n📝 Опис: {desc}"
        except Exception as e:
            print("Parse error:", e)
            return "⚠️ Помилка обробки даних", False, None

        try:
            self.redis.setex(cache_key, 300, result)
        except Exception as e:
            print("Redis save error:", e)

        return result, False, temp


class TelegramBot:
    def __init__(self, token, weather_service, db):
        self.token = token
        self.weather_service = weather_service
        self.db = db

        self.menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌦 Погода", callback_data="weather")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
             InlineKeyboardButton("📈 Графік", callback_data="plot")],
            [InlineKeyboardButton("🎲 Dice", callback_data="dice")]
        ])

        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("menu", self.menu_command))
        self.app.add_handler(CommandHandler("weather", self.weather))
        self.app.add_handler(CommandHandler("stats", self.stats))
        self.app.add_handler(CommandHandler("plot", self.plot))
        self.app.add_handler(CallbackQueryHandler(self.on_click))
        self.app.add_error_handler(self.on_error)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 Привіт!\n\n"
            "Команди:\n"
            "/weather Київ\n"
            "/stats Київ\n"
            "/plot Київ\n\n"
            "Або використовуй меню 👇",
            reply_markup=self.menu
        )

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📋 Меню:", reply_markup=self.menu)

    async def on_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()

        if q.data == "dice":
            msg = await q.message.reply_dice(emoji="🎲")
            if msg.dice.value == 6:
                await q.message.reply_text("🔥 Максимум!")
            return

        if q.data == "weather":
            await q.message.reply_text("Напиши:\n/weather Київ")
            return

        if q.data == "stats":
            await q.message.reply_text("Напиши:\n/stats Київ")
            return

        if q.data == "plot":
            await q.message.reply_text("Напиши:\n/plot Київ")
            return

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Напиши:\n/weather Київ")
            return

        city = " ".join(context.args)
        result, from_cache, temp = self.weather_service.get_weather(city)

        if from_cache:
            result += "\n⚡ (з кешу)"
        else:
            if temp is not None:
                self.db.save_weather(city, temp)

        await update.message.reply_text(result)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Напиши:\n/stats Київ")
            return

        city = " ".join(context.args)

        avg_temp = self.db.get_avg_temp(city)

        if avg_temp is not None:
            await update.message.reply_text(
                f"📊 Середня температура в {city}: {round(avg_temp, 2)}°C"
            )
        else:
            await update.message.reply_text("Немає даних")

    async def plot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Напиши:\n/plot Київ")
            return

        city = " ".join(context.args)

        records = self.db.get_last_records(city)

        if not records:
            await update.message.reply_text("Немає даних для графіка")
            return

        temps = [r[0] for r in records][::-1]
        times = [r[1] for r in records][::-1]

        plt.figure()
        plt.plot(times, temps, marker='o')
        plt.xticks(rotation=45)
        plt.xlabel("Час")
        plt.ylabel("Температура °C")
        plt.title(f"Погода в {city}")
        plt.tight_layout()

        file_name = "plot.png"
        plt.savefig(file_name)
        plt.close()

        await update.message.reply_photo(photo=open(file_name, "rb"))

    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        print("ERROR:", repr(context.error))

    def run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        print("Bot running...")
        self.app.run_polling(close_loop=False)


def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEATHER_API = os.getenv("WEATHER_API")

    if not TOKEN:
        raise RuntimeError("BOT_TOKEN missing")
    if not WEATHER_API:
        raise RuntimeError("WEATHER_API missing")

    db = Database()
    weather_service = WeatherService(WEATHER_API)

    bot = TelegramBot(TOKEN, weather_service, db)
    bot.run()


if __name__ == "__main__":
    main()