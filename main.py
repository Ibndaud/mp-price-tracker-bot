import os
import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery

from parser import get_steam_price
from database import (
    init_db, add_user, add_item, get_user_items, delete_item, 
    get_item_by_app_id, db_update_price
    )
from keyboards import get_items_keyboard
from utils import get_steam_app_id, format_price, format_items_list

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
        f"Я бот для отслеживания цен. Пришли мне ссылку на игру в Steam 🎮, и "
        "я буду за ней следить!"
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
    user_id = message.from_user.id
    items = await get_user_items(user_id)

    # Если список пустой — сразу говорим об этом и выходим
    if not items:
        await message.answer(
            "📭 У тебя пока нет отслеживаемых игр.\n"
            "Пришли ссылку на Steam, чтобы добавить первую! 🎮"
        )
        return

    # Обновляем отсутствующие цены ДО форматирования
    for item in items:
        if item['last_price'] is None:
            price = await handle_none_price(user_id, item['steam_app_id'])
            if price is not None:
                item['last_price'] = price

    # Форматируем уже подготовленные данные
    text = format_items_list(items)

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

    if not success:
        await callback.answer("❌ Не удалось удалить товар", show_alert=True)
        return
    
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
        text = format_items_list(items)            
        keyboard = get_items_keyboard(items)
        await callback.message.edit_text(text, reply_markup=keyboard)


# 5. Фильтр F.text.contains ищет сообщения, в которых есть кусок текста "steampowered.com"
@dp.message(F.text.contains("steampowered.com"))
async def handle_steam_link(message: types.Message):
    # 1. Берем текст сообщения (пока предполагаем, что пользователь прислал только ссылку)
    url = message.text.strip()

    # Получаем Steam App ID
    steam_app_id = get_steam_app_id(url)

    if steam_app_id is None:
        await message.answer("❌ Некорректная ссылка Steam.")
        return

    # 2. Проверяем, есть ли игра в отслеживании
    user_id = message.from_user.id
    existing_item = await get_item_by_app_id(user_id, steam_app_id)

    if existing_item:
        await message.answer(
            f"⚠️ Игра {existing_item['name']} уже отслеживается!"
            )
        return
    else:
        # Отправляем сообщение-заглушку, чтобы пользователь знал, что бот не завис
        wait_msg = await message.answer("⏳ Проверяю цену, подожди пару секунд...")

    
    # 3. Вызываем нашу функцию парсера
    title, price, currency = await get_steam_price(steam_app_id)

    await add_user(
        user_id=message.from_user.id, 
        username=message.from_user.username, 
        first_name=message.from_user.first_name
        )
    
    # 4. В зависимости от результата ИЗМЕНЯЕМ наше сообщение-заглушку
    if title and price is not None and currency == "RUB":
        # СОХРАНЯЕМ ТОВАР В БД
        added = await add_item(
            user_id = message.from_user.id, 
            url = url, 
            name = title,
            last_price = price,
            currency=currency,
            steam_app_id = steam_app_id
            )
        if added:
            await wait_msg.edit_text(
                f"✅ Товар найден и добавлен в базу!\n"
                f"Название: {title}\n"
                f"Текущая цена: {format_price(price, currency)}\n\n"
                f"💰 Теперь я буду проверять её каждый день."
                )
        else:
            await wait_msg.edit_text(
                "⚠️ Эта игра уже находится в отслеживании."
                )
    else:
        await wait_msg.edit_text(
            "❌ Не удалось получить цену. Проверь ссылку или попробуй другую."
            )


async def handle_none_price(user_id, steam_app_id):
    title, price, currency = await get_steam_price(steam_app_id)
    if price is not None and currency == "RUB":
        await db_update_price(user_id, price, steam_app_id)

        return price
    return None


# 6. Если пользователь пришлет любой другой текст (не команду и не ссылку на Steam)
@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer(
        "Пока я понимаю только ссылки на Steam (steampowered.com). "
        "Пришли мне ссылку!"
        )


# Функция запуска бота
async def main():
    print("Инициализация базы данных...")
    await init_db()
    print("Бот запущен!")
    # Запускаем постоянный опрос серверов Telegram (есть ли для нас новые сообщения?)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


# Точка входа в программу
# Эта конструкция значит: "Запусти функцию main, только если файл запущен напрямую"
if __name__ == "__main__":
    asyncio.run(main())
