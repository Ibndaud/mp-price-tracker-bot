import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

from parser import get_steam_price

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

# Фильтр F.text.contains ищет сообщения, в которых есть кусок текста "steampowered.com"
@dp.message(F.text.contains("steampowered.com"))
async def handle_steam_link(message: types.Message):
    # 1. Отправляем сообщение-заглушку, чтобы пользователь знал, что бот не завис
    wait_msg = await message.answer("⏳ Проверяю цену, подожди пару секунд...")
    
    # 2. Берем текст сообщения (пока предполагаем, что пользователь прислал только ссылку)
    url = message.text
    
    # 3. Вызываем нашу функцию парсера
    price = await get_steam_price(url)
    
    # 4. В зависимости от результата ИЗМЕНЯЕМ наше сообщение-заглушку
    if price:
        await wait_msg.edit_text(f"✅ Товар найден!\nТекущая цена: **{price}**", parse_mode="Markdown")
    else:
        await wait_msg.edit_text("❌ Не удалось найти цену. Проверь ссылку или попробуй другую.")

# Если пользователь пришлет любой другой текст (не команду /start и не ссылку на Steam)
@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Пока я понимаю только ссылки на Steam (steampowered.com). Пришли мне ссылку!")

# Функция запуска бота
async def main():
    print("Бот запущен!")
    # Запускаем постоянный опрос серверов Telegram
    await dp.start_polling(bot)

# Точка входа в программу
if __name__ == "__main__":
    asyncio.run(main())