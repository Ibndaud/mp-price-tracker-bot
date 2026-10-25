import asyncio
import logging

from aiogram import Bot

from parser import get_steam_price
from database import get_all_items, record_price_update
from utils import format_price


logger = logging.getLogger(__name__)


async def check_prices(bot: Bot):
    """
    Вызывается автоматически по расписанию (например раз в сутки).
    Проверяет актуальные цены всех отслеживаемых игр
    и уведомляет пользователей, если цена снизилась.
    """
    logger.info("🔍 Начинаю плановую проверку цен...")
    items = await get_all_items()

    if not items:
        logger.info("Нет товаров для проверки.")
        return

    logger.info("Всего записей для проверки: %d", len(items))

    # Группируем записи по steam_app_id.
    # setdefault(key, []) — если ключа ещё нет в словаре, создаёт пустой список
    # если есть — просто возвращает существующий
    items_by_app_id: dict[int, list[dict]] = {}
    for item in items:
        items_by_app_id.setdefault(item['steam_app_id'], []).append(item)

    logger.info(
        "Уникальных игр для обновления: %d", len(items_by_app_id)
    )

    # Теперь идём не по всем строкам, а по уникальным играм
    # group — список словарей полученых из строк в таблице со всеми пользователями, отслеживающими именно эту игру
    for steam_app_id, group in items_by_app_id.items():
        title, new_price, currency = await get_steam_price(steam_app_id)

        if new_price is None:
            logger.warning(
                "Не удалось получить цену для steam_app_id=%s, пропускаю",
                steam_app_id
            )
            continue

        # Применяем полученную цену к каждому из пользователей, отслеживающему именно эту игру
        for item in group:
            old_price = item['last_price']
            old_currency = item['currency']
            user_id = item['user_id']
            item_id = item['id']

            # Не сравниваем разные валюты
            if currency is None or currency != old_currency:
                logger.warning(
                    'У пользователя %s изменилась валюта отслеживания '
                    'для steam_app_id=%s, пропускаю',
                    user_id, steam_app_id
                    )
                continue

            # Записываем новую точку в историю ВСЕГДА,
            # даже если цена не изменилась — так график будет непрерывным,
            # а не состоять только из моментов изменения цены
            saved = await record_price_update(item_id, new_price, currency)
            if not saved:
                logger.warning(
                    "Строки с id=%s в таблице больше не существует", 
                    item_id
                    )
                continue

            # Определяем снижение ДО обновления базы
            price_dropped = old_price is not None and new_price < old_price

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

    logger.info("✅ Проверка цен завершена")