import os
import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

from parser import get_steam_price
from database import init_db, add_user, add_item


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

# Включаем логирование.
# Это позволит видеть в терминале всё, что происходит с ботом (ошибки, входящие сообщения).
logging.basicConfig(level=logging.INFO)

# Создаем основные объекты.
# Создаем объекты бота и диспетчера (диспетчер управляет входящими сообщениями)
# Bot - это сам бот (он отправляет запросы в Telegram).
bot = Bot(token=BOT_TOKEN)
# Dispatcher - это "маршрутизатор". Он получает сообщения и решает, какая функция должна их обработать.
dp = Dispatcher()

# Пишем обработчики (хэндлеры).
# Этот декоратор ловит команду /start
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await add_user(
        user_id = message.from_user.id, 
        username = message.from_user.username, 
        first_name = message.from_user.first_name
    )

    # Бот отвечает пользователю
    # message.answer - отправляет сообщение в тот же чат, откуда пришел запрос
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я бот для отслеживания цен. Пришли мне ссылку на игру в Steam, и я буду за ней следить!"
    )

# Фильтр F.text.contains ищет сообщения, в которых есть кусок текста "steampowered.com"
@dp.message(F.text.contains("steampowered.com"))
async def handle_steam_link(message: types.Message):
    # 1. Отправляем сообщение-заглушку, чтобы пользователь знал, что бот не завис
    wait_msg = await message.answer("⏳ Проверяю цену, подожди пару секунд...")
    
    # 2. Берем текст сообщения (пока предполагаем, что пользователь прислал только ссылку)
    url = message.text
    
    # 3. Вызываем нашу функцию парсера
    title, price = await get_steam_price(url)
    
    # 4. В зависимости от результата ИЗМЕНЯЕМ наше сообщение-заглушку
    if title and price:
        # СОХРАНЯЕМ ТОВАР В БД
        await add_item(
            user_id = message.from_user.id, 
            url = url, 
            name = title,
            last_price = price
        )
        await wait_msg.edit_text(f"✅ Товар найден и добавлен в базу!\n"
                                 f"Название: {title}\n"
                                 f"Текущая цена: *{price}*\n\n"
                                 f"💰 Теперь я буду проверять её каждый день.")
    else:
        await wait_msg.edit_text("❌ Не удалось получить цену. Проверь ссылку или попробуй другую.")

# Если пользователь пришлет любой другой текст (не команду /start и не ссылку на Steam)
@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Пока я понимаю только ссылки на Steam (steampowered.com). Пришли мне ссылку!")

# Функция запуска бота
async def main():
    print("Инициализация базы данных...")
    await init_db()
    print("Бот запущен!")
    # Запускаем постоянный опрос серверов Telegram (есть ли для нас новые сообщения?)
    await dp.start_polling(bot)

# Точка входа в программу
# Эта конструкция значит: "Запусти функцию main, только если файл запущен напрямую"
if __name__ == "__main__":
    asyncio.run(main())
