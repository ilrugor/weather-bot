import os
import asyncio
import requests
import redis
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()


class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.redis = redis.Redis(host="localhost", port=6379, decode_responses=True)

    def get_weather(self, city: str):
        cache_key = f"weather:{city.lower()}"

        try:
            cached = self.redis.get(cache_key)
            if cached:
                return cached, True
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
                return "❌ Місто не знайдено", False

            if r.status_code != 200:
                return "⚠️ Проблема з сервером погоди", False

            data = r.json()

        except requests.exceptions.Timeout:
            return "⏳ Сервер не відповідає", False
        except requests.exceptions.ConnectionError:
            return "🌐 Немає інтернету", False
        except Exception as e:
            print("API error:", e)
            return "⚠️ Помилка API", False

        try:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            result = f"🌦 Погода в {city}:\n🌡 Температура: {temp}°C\n📝 Опис: {desc}"
        except Exception as e:
            print("Parse error:", e)
            return "⚠️ Помилка обробки даних", False

        try:
            self.redis.setex(cache_key, 300, result)
        except Exception as e:
            print("Redis save error:", e)

        return result, False


class TelegramBot:
    def __init__(self, token, weather_service):
        self.token = token
        self.weather_service = weather_service

        self.menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Dice", callback_data="dice"),
             InlineKeyboardButton("🌦 Weather", callback_data="weather")]
        ])

        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("weather", self.weather))
        self.app.add_handler(CallbackQueryHandler(self.on_click))
        self.app.add_error_handler(self.on_error)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Привіт! Обери дію:", reply_markup=self.menu)

    async def on_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()

        if q.data == "dice":
            try:
                msg = await q.message.reply_dice(emoji="🎲")
                if msg.dice.value == 6:
                    await q.message.reply_text("🔥 Максимум!")
            except Exception as e:
                print("Dice error:", e)
            return

        if q.data == "weather":
            await q.message.reply_text("Напиши:\n/weather Київ")
            return

    async def weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Напиши так:\n/weather Київ")
            return

        city = " ".join(context.args)

        result, from_cache = self.weather_service.get_weather(city)

        if from_cache:
            result += "\n⚡ (з кешу)"

        await update.message.reply_text(result)

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

    weather_service = WeatherService(WEATHER_API)
    bot = TelegramBot(TOKEN, weather_service)
    bot.run()


if __name__ == "__main__":
    main()