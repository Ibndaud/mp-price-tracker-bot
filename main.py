import os
import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery

from parser import get_steam_price
from database import init_db, add_user, add_item, get_user_items, delete_item
from keyboards import get_items_keyboard

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

# Включаем логирование.
# Это позволит видеть в терминале всё, что происходит с ботом (ошибки, входящие сообщения).
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера (диспетчер управляет входящими сообщениями)
# Bot - это сам бот (он отправляет запросы в Telegram).
bot = Bot(token=BOT_TOKEN)
# Dispatcher - это "маршрутизатор". Он получает сообщения и решает, какая функция должна их обработать.
dp = Dispatcher()


# Пишем обработчики (хэндлеры).
# 1. Этот декоратор ловит команду /start
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
        f"Я бот для отслеживания цен. Пришли мне ссылку на игру в Steam 🎮, и я буду за ней следить!"
        )


# 2. Этот декоратор ловит команду /help
@dp.message(Command("help"))
async def handle_help(message: types.Message):
    await message.answer(
        "📖 Доступные команды:\n\n"
        "/start — начать работу с ботом\n"
        "/help — это сообщение\n"
        "/list — показать отслеживаемые игры\n\n"
        "Чтобы добавить игру — просто пришли мне ссылку на страницу Steam 🎮"
        )


# 3. Этот декоратор ловит команду /list
@dp.message(Command("list"))
async def handle_list(message: types.Message):
    items = await get_user_items(message.from_user.id)

    # Если список пустой — сразу говорим об этом и выходим
    if not items:
        await message.answer(
            "📭 У тебя пока нет отслеживаемых игр.\n"
            "Пришли ссылку на Steam, чтобы добавить первую! 🎮"
        )
        return

    # Формируем текстовое сообщение со списком
    text = "📋 Твои отслеживаемые игры:\n\n"
    for item in items:
        name = item['name'] or "Без названия"
        text += f"🎮 {name}\n💰 {item['last_price']}\n🔗 {item['url']}\n\n"

    text += "Нажми на кнопку ниже, чтобы удалить игру."

    # Строим клавиатуру с кнопками удаления
    keyboard = get_items_keyboard(items)

    await message.answer(text, reply_markup=keyboard)


# 4. Команда /delete
@dp.callback_query(F.data.startswith("delete_"))
async def handle_delete_callback(callback: CallbackQuery):
    # callback.data — это та самая строка "delete_5" которую мы задавали
    # Разбиваем по "_" и берём вторую часть — число
    item_id = int(callback.data.split("_")[1])

    # Удаляем товар, проверяя что он принадлежит именно этому пользователю
    success = await delete_item(item_id, callback.from_user.id)

    if success:
        # Отправляем всплывающее уведомление (не занимает место в чате)
        await callback.answer("✅ Товар удалён!")
        
        # Обновляем список — получаем свежие данные без удалённого товара
        items = await get_user_items(callback.from_user.id)

        if not items:
            # Если товаров больше нет — меняем текст сообщения
            await callback.message.edit_text(
                "📭 Список пуст. Пришли ссылку на Steam чтобы добавить игру! 🎮"
            )
        else:
            # Пересобираем текст и клавиатуру с оставшимися товарами
            text = "📋 Твои отслеживаемые игры:\n\n"
            for item in items:
                name = item['name'] or "Без названия"
                text += f"🎮 {name}\n💰 {item['last_price']}\n🔗 {item['url']}\n\n"

            text += "Нажми на кнопку ниже, чтобы удалить игру."
            
            keyboard = get_items_keyboard(items)
            await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.answer("❌ Не удалось удалить товар", show_alert=True)


# 5. Фильтр F.text.contains ищет сообщения, в которых есть кусок текста "steampowered.com"
@dp.message(F.text.contains("steampowered.com"))
async def handle_steam_link(message: types.Message):
    # 1. Отправляем сообщение-заглушку, чтобы пользователь знал, что бот не завис
    wait_msg = await message.answer("⏳ Проверяю цену, подожди пару секунд...")
    
    # 2. Берем текст сообщения (пока предполагаем, что пользователь прислал только ссылку)
    url = message.text
    
    # 3. Вызываем нашу функцию парсера
    title, price = await get_steam_price(url)

    await add_user(
        user_id=message.from_user.id, 
        username=message.from_user.username, 
        first_name=message.from_user.first_name
        )
    
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


# 6. Если пользователь пришлет любой другой текст (не команду и не ссылку на Steam)
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
