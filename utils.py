import re
from urllib.parse import urlparse


def get_steam_app_id(url: str) -> int | None:
    """
    Извлекает ID игры из ссылки Steam.

    Например:
    https://store.steampowered.com/app/413150/Stardew_Valley/

    Вернёт:
    413150
    """

    parsed_url = urlparse(url)

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
            if price is not None
            else "Цена недоступна"
        )

        text += (
            f"🎮 {name}\n"
            f"💰 {price_text}\n"
            f"🔗 {item['url']}\n\n"
        )

    text += "Нажми на кнопку ниже, чтобы удалить игру."

    return text