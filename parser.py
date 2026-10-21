import asyncio
import logging
import aiohttp

from utils import get_steam_app_id


logger = logging.getLogger(__name__)

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"


async def get_steam_price(
        steam_app_id: int
        ) -> tuple[str | None, int | None, str | None]:
    """
    Получает название игры, цену в копейках и валюту.

    Возвращает:
        (название, цена, валюта)

    Например:
        ("Stardew Valley", 14900, "RUB")

    Если данные получить не удалось:
        (None, None, None)
    """
    params = {
        "appids": steam_app_id,
        "cc": "ru",
        "l": "russian"
    }

    timeout = aiohttp.ClientTimeout(total=15)

    try:
        # Открываем асинхронную сессию
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Делаем GET-запрос по STEAM_API_URL
            async with session.get(STEAM_API_URL, params=params) as response:
                # Проверяем, что страница успешно загрузилась (статус 200)
                if response.status != 200:
                    logger.warning(
                        "Steam API вернул статус %s", response.status
                        )
                    return None, None, None
                
                # Получаем HTML-код страницы
                data = await response.json()
                
        app_data = data.get(str(steam_app_id))

        if not app_data or not app_data.get("success"):
            logger.warning(
                "Steam не вернул данные для игры %s", steam_app_id
                )
            return None, None, None

        game = app_data.get("data", {})
        title = game.get("name")

        if game.get("is_free"):
            return title, 0, "RUB"
        
        price_info = game.get("price_overview")

        if not price_info:
            logger.warning(
                "Нет информации о цене игры %s", steam_app_id
                )
            return None, None, None

        currency = price_info.get("currency")
        price = price_info.get("final")

        if currency != "RUB":
            logger.warning(
                "Неожиданная валюта для игры %s: %s", steam_app_id, currency
                )
            return None, None, None

        if (not title or 
            not isinstance(price, int) or 
            isinstance(price, bool) or 
            price < 0):
            logger.warning(
                "Некорректные данные игры %s", steam_app_id
                )
            return None, None, None

        return title, price, currency

    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        logger.error(
            "Ошибка получения цены игры %s: %s", steam_app_id, e
            )
        return None, None, None


# Блок для тестирования нашего парсера
# Этот код выполнится только если запустить именно этот файл напрямую
async def main():
    # Берем для примера игру Stardew Valley (она без возрастного ограничения, что упрощает парсинг)
    test_url = "https://store.steampowered.com/app/413150/Stardew_Valley/"
    print(f"Проверяем цену по ссылке: {test_url}")
    
    title, price, currency = await get_steam_price(get_steam_app_id(test_url))
    
    if title and price is not None and currency:
        print(f"Ура! 🎮 На игру: {title} 💰 текущая цена: {price / 100:.2f}  и валюта: {currency}")
    else:
        print("Не удалось найти цену. Возможно, изменилась верстка сайта.")

if __name__ == "__main__":
    asyncio.run(main())