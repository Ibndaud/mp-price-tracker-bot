import asyncio
import logging

from aiogram import Bot

from parser import get_steam_price
from database import get_all_items, save_price_check
from utils import format_price


logger = logging.getLogger(__name__)


async def check_prices(bot: Bot):
    """
    Проверяет цены всех отслеживаемых игр.
    """
    logger.info("Начинаем проверку цен...")
    items = await get_all_items()

    if not items:
        logger.info("Нет товаров для проверки.")
        return

    for item in items:
        item_id = item["id"]
        user_id = item["user_id"]
        steam_app_id = item["steam_app_id"]
        old_price = item["last_price"]
        old_currency = item["currency"]

        logger.info(
            "Проверяем игру %s (App ID: %s)",
            item["name"],
            steam_app_id
        )

        title, new_price, new_currency = await get_steam_price(
            steam_app_id
        )

        # Если цену получить не удалось
        if new_price is None or new_currency != "RUB":
            logger.warning(
                "Не удалось получить цену игры %s",
                steam_app_id
            )
            continue

        # Не сравниваем разные валюты
        if old_currency != new_currency:
            logger.warning(
                "Валюта изменилась у игры %s",
                steam_app_id
            )
            continue

        # Определяем снижение ДО обновления базы
        price_dropped = (
            old_price is not None
            and new_price < old_price
        )

        # Сохраняем новую цену и историю
        saved = await save_price_check(
            item_id=item_id,
            price=new_price,
            currency=new_currency
        )

        if not saved:
            logger.warning(
                "Товар %s больше не существует",
                item_id
            )
            continue

        # Если цена снизилась — уведомляем пользователя
        if price_dropped:
            difference = old_price - new_price
            discount_percent = (difference / old_price) * 100

            text = (
                f"🎉 Цена снизилась!\n\n"
                f"🎮 {title or item['name']}\n\n"
                f"Было: {format_price(old_price)}, "
                f"стало: {format_price(new_price)}\n"
                f"Снижение: {discount_percent:.1f}%\n\n"
                f"🔗 {item['url']}"
                )

            try:
                await bot.send_message(chat_id=user_id, text=text)

                logger.info(
                    "Уведомление отправлено пользователю %s",
                    user_id
                )

            except Exception:
                logger.exception(
                    "Не удалось отправить уведомление пользователю %s",
                    user_id
                )

        # Небольшая пауза между запросами
        await asyncio.sleep(1)

    logger.info("Проверка цен завершена.")