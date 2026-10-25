import math
import re
import aiosqlite
from urllib.parse import urlparse
from contextlib import asynccontextmanager


def get_steam_app_id(url: str) -> int | None:
    """
    Извлекает ID игры из ссылки Steam.

    Например:
    https://store.steampowered.com/app/413150/Stardew_Valley/

    Вернёт:
    413150
    """

    parsed_url = urlparse(url.lower())

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "store.steampowered.com"
    ):
        return None

    match = re.fullmatch(
        r"/app/(\d+)(?:/[^/?#]*)?/?",
        parsed_url.path
    )

    if not match:
        return None

    return int(match.group(1))


def format_price(price: int, currency: str = "RUB") -> str:
    """
    Преобразует цену из копеек
    в удобную для пользователя строку.
    """

    if currency != "RUB":
        raise ValueError(f"Неподдерживаемая валюта: {currency}")

    rub = price // 100
    kop = price % 100

    if kop == 0:
        return f"{rub:,} ₽".replace(",", " ")

    return f"{rub:,}.{kop:02d} ₽".replace(",", " ")


def format_items_list(items: list[dict]) -> str:
    text = "📋 Твои отслеживаемые игры:\n\n"

    for item in items:
        name = item['name'] or "Без названия"
        price = item['last_price']

        price_text = (
            format_price(price, item['currency'])
            if price is not None else "Цена недоступна"
        )

        text += (
            f"🎮 {name}\n"
            f"💰 {price_text}\n"
            f"🔗 {item['url']}\n\n"
            )

    text += "Нажми на кнопку ниже, чтобы удалить игру."
    return text


def format_items_page(
        items: list[dict], page: int, total_pages: int, total_items: int
        ) -> str:
    """Форматирует ОДНУ страницу списка отслеживаемых игр."""
    text = f"📋 Твои отслеживаемые игры ({total_items} шт.)\n"
    if total_pages > 1:
        text += f"Страница {page} из {total_pages}\n"
    text += "\n"

    for item in items:
        name = item['name'] or "Без названия"
        price = item['last_price']
        price_text = (
            format_price(price, item['currency'])
            if price is not None else "Цена недоступна"
        )
        text += (
            f"🎮 {name}\n"
            f"💰 {price_text}\n"
            f"🔗 {item['url']}\n\n"
            )

    text += "Нажми на кнопку ниже, чтобы удалить игру."
    return text


def paginate(items: list, page: int, page_size: int) -> tuple[list, int, int]:
    """
    Разбивает список на страницы.
    
    Возвращает срез элементов для текущей страницы, всего страниц, 
    нормализованный номер страницы.
    
    Нормализация нужна на случай если список стал короче
    (например, что-то удалили) — не даём page выйти за границы.
    """
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size

    return items[start:end], total_pages, page


@asynccontextmanager
async def get_db_connection(db_name):
    db = await aiosqlite.connect(db_name)
    try:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")
        yield db
    finally:
        await db.close()