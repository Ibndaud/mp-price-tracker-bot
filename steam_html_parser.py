import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def get_steam_price(url: str) -> tuple[str | None, str | None]:
    """
    Асинхронно получает цену игры со страницы Steam.
    Возвращает строку с ценой или None, если цена не найдена.
    """
    # Сайты не любят ботов. Мы маскируемся под обычный браузер с помощью заголовка User-Agent.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # Открываем асинхронную сессию (как будто открыли вкладку браузера)
        async with aiohttp.ClientSession() as session:
            # Делаем GET-запрос по ссылке
            async with session.get(url, headers=headers) as response:
                # Проверяем, что страница успешно загрузилась (статус 200)
                if response.status != 200:
                    print(f"Ошибка: Сервер вернул статус {response.status}")
                    return None, None
                
                # Получаем HTML-код страницы
                html = await response.text()
                
                # Отдаем HTML в BeautifulSoup для поиска нужных тегов
                soup = BeautifulSoup(html, 'html.parser')

                # 6. Ищем название игры. В Steam оно всегда лежит в теге <div class="apphub_AppName">
                title_block = soup.find("div", class_="apphub_AppName")
                if title_block:
                    title = title_block.text.strip()
                else:
                    print("Название не найдено")
                    title = None
                
                # В Steam цена обычно лежит в div с классом "discount_final_price" (если скидка)
                # или "game_purchase_price" (если без скидки)
                
                # Сначала ищем цену со скидкой
                price_div = soup.find('div', class_='discount_final_price')
                
                # Если скидки нет, ищем обычную цену
                if not price_div:
                    price_div = soup.find('div', class_='game_purchase_price')

                if not price_div:
                    print("Цена не найдена")
                    return title, None
                
                # Если нашли блок с ценой - очищаем от пробелов и возвращаем
                price = price_div.text.strip()

                return title, price

    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return None, None

# Блок для тестирования нашего парсера
# Этот код выполнится только если запустить именно этот файл напрямую
async def main():
    # Берем для примера игру Stardew Valley (она без возрастного ограничения, что упрощает парсинг)
    test_url = "https://store.steampowered.com/app/413150/Stardew_Valley/"
    print(f"Проверяем цену по ссылке: {test_url}")
    
    title, price = await get_steam_price(test_url)
    
    if title:
        print(f"Ура! 🎮 На игру: {title} 💰 текущая цена: {price}")
    else:
        print("Не удалось найти цену. Возможно, изменилась верстка сайта.")

if __name__ == "__main__":
    asyncio.run(main())