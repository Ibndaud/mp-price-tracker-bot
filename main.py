import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Твой токен (позже мы спрячем его в безопасное место)
BOT_TOKEN = "8853210308:AAEtit88C8QfIQqucFTblBVHF-B12wj4Xpo"

# Создаем объекты бота и диспетчера (диспетчер управляет входящими сообщениями)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Этот декоратор ловит команду /start
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    # Бот отвечает пользователю
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я бот для отслеживания цен. Пришли мне ссылку на товар!"
    )

# Функция запуска бота
async def main():
    print("Бот запущен!")
    # Запускаем постоянный опрос серверов Telegram
    await dp.start_polling(bot)

# Точка входа в программу
if __name__ == "__main__":
    asyncio.run(main())