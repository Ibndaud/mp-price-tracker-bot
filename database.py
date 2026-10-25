import aiosqlite
import logging
from utils import get_db_connection

logger = logging.getLogger(__name__)

# Имя файла нашей базы данных (создастся автоматически рядом с кодом)
DB_NAME = "price_tracker.db"


async def init_db():
    """
    Создает таблицы в базе данных, если их еще нет.
    Эту функцию мы будем вызывать при старте бота.
    """
    # Открываем асинхронное соединение с файлом БД
    async with get_db_connection(DB_NAME) as db:
        
        # 1. Таблица пользователей
        # id - уникальный номер пользователя в Telegram (PRIMARY KEY значит, что он не может повторяться)
        # username - его никнейм в Телеграме (может быть пустым)
        # first_name - имя
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT
                )
            '''
            )
        
        # 2. Таблица отслеживаемых товаров
        # id - внутренний номер записи (автоматически увеличивается - AUTOINCREMENT)
        # user_id - ID пользователя, который добавил ссылку (чтобы знать, кому писать)
        # url - сама ссылка на товар
        # name - название товара (чтобы красиво писать в уведомлении)
        # last_price - последняя известная цена (может быть пустой - NULL, пока мы её не спарсили)
        # steam_app_id - уникальный идентификатор игры в steam, получаемый из url
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                name TEXT,
                last_price INTEGER,
                currency TEXT NOT NULL DEFAULT 'RUB',
                steam_app_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, steam_app_id)
                )
            '''
            )
        await db.execute(
            'CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);'
            )

        # Новая таблица — журнал всех изменений цены
        # Одна запись = одно значение цены в конкретный момент времени
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                price INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'RUB',
                checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            '''
            )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_history_item_id
                ON price_history(item_id, checked_at);
            """
            )
        
        # Сохраняем (коммитим) изменения в файл
        await db.commit()
        logger.info("База данных успешно инициализирована!")


async def add_user(user_id: int, username: str | None, first_name: str):
    """Добавляет пользователя в БД, если его там еще нет"""
    async with get_db_connection(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO users (id, username, first_name) 
            VALUES (?, ?, ?)

            ON CONFLICT(id) DO UPDATE 
            SET username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name)
        )
        await db.commit()


async def add_item(
        user_id: int, 
        url: str, 
        name: str, 
        last_price: int, 
        currency: str, 
        steam_app_id: int
        ) -> int | None:
    """Добавляет новую ссылку на товар для конкретного пользователя"""
    async with get_db_connection(DB_NAME) as db:
        try:
            cursor = await db.execute(
                '''
                INSERT INTO items 
                (user_id, url, name, last_price, currency, steam_app_id) 
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, steam_app_id) DO NOTHING
                ''',
                (user_id, url, name, last_price, currency, steam_app_id)
                )
            # Если rowcount == 0 — ON CONFLICT сработал, строка не вставилась
            # Значит игра уже была в базе — выходим без лишней записи в историю
            if cursor.rowcount == 0:
                await db.rollback()
                return
            
            # lastrowid — id только что вставленного товара
            item_id = cursor.lastrowid

            # Сразу пишем первую точку истории —
            # цену на момент добавления игры в отслеживание
            await db.execute(
                '''
                INSERT INTO price_history (item_id, price, currency)
                VALUES (?, ?, ?)
                ''',
                (item_id, last_price, currency)
                )

            # Коммитим ОБЕ вставки одновременно — это и есть атомарность
            await db.commit()
            return item_id
        
        except Exception:
            await db.rollback()
            raise


async def get_user_items(user_id: int) -> list[dict]:
    """
    Возвращает список товаров пользователя.
    Каждый товар — словарь {id, name, url, last_price}
    """
    async with get_db_connection(DB_NAME) as db:
        # row_factory превращает строки результата в объекты-словари
        # Без этого пришлось бы обращаться по индексам: row[0], row[1]...
        db.row_factory = aiosqlite.Row

        async with db.execute(
            '''
            SELECT id, name, url, last_price, currency, steam_app_id
            FROM items
            WHERE user_id = ?
            ORDER BY id
            ''',
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            # dict(row) превращает каждую Row в обычный словарь Python
            return [dict(row) for row in rows]


async def get_all_items() -> list[dict]:
    """
    Возвращает список ВСЕХ отслеживаемых товаров ВСЕХ пользователей.
    Используется планировщиком — проверяет цены для каждой записи.
    """
    async with get_db_connection(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, steam_app_id, name, url, last_price, currency
            FROM items
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        

async def delete_item(item_id: int, user_id: int) -> bool:
    """
    Удаляет товар с указанными id товара и пользователя.
    Возвращает True если удаление прошло успешно.
    """
    async with get_db_connection(DB_NAME) as db:
        cursor = await db.execute(
            '''
            DELETE FROM items
            WHERE id = ? AND user_id = ?
            ''',
            (item_id, user_id,),
        )
        await db.commit()

        # rowcount — сколько строк затронул запрос
        # Если 0 — товар не найден
        return cursor.rowcount > 0


async def get_item_by_app_id(user_id: int, steam_app_id: int) -> dict | None:

    async with get_db_connection(DB_NAME) as db:

        db.row_factory = aiosqlite.Row

        async with db.execute(
            '''
            SELECT id, name, url, last_price
            FROM items
            WHERE user_id = ? AND steam_app_id = ?
            ''',
            (user_id, steam_app_id)
        ) as cursor:

            row = await cursor.fetchone()

            return dict(row) if row else None


async def db_update_price(
        user_id: int, 
        last_price: int, 
        steam_app_id: int
        ) -> bool:
    async with get_db_connection(DB_NAME) as db:
        cursor = await db.execute(
            """
            UPDATE items
            SET last_price = ?
            WHERE user_id = ?
            AND steam_app_id = ?
            """,
            (last_price, user_id, steam_app_id)
            )
        await db.commit()
        return cursor.rowcount > 0


async def record_price_update(item_id: int, new_price: int, currency: str) -> bool:
    """
    Обновляет текущую цену товара (items.last_price)
    и одновременно добавляет точку в историю (price_history).

    Используется и планировщиком при плановой проверке,
    и вручную — например когда обнаруживаем товар с неизвестной ценой.
    """
    async with get_db_connection(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE items SET last_price = ? WHERE id = ?",
            (new_price, item_id)
            )

        # Если rowcount == 0 — товара с таким id не существует
        if cursor.rowcount == 0:
            await db.commit()
            return False

        await db.execute(
            '''
            INSERT INTO price_history (item_id, price, currency)
            VALUES (?, ?, ?)
            ''',
            (item_id, new_price, currency)
            )

        await db.commit()
        return True

async def add_price_history(item_id: int, price: int, currency: str):
    """
    Сохраняет результат проверки цены.
    """
    async with get_db_connection(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO price_history (
                item_id,
                price,
                currency
                )
            VALUES (?, ?, ?)
            """,
            (item_id, price, currency)
            )
        await db.commit()


async def save_price_check(item_id: int, price: int, currency: str) -> bool:
    """
    Обновляет последнюю цену товара
    и сохраняет запись истории.

    Оба действия выполняются в одной транзакции.
    """
    async with get_db_connection(DB_NAME) as db:
        try:
            cursor = await db.execute(
                """
                UPDATE items
                SET last_price = ?,
                    currency = ?
                WHERE id = ?
                """,
                (price, currency, item_id)
                )
            if cursor.rowcount == 0:
                await db.rollback()
                return False

            await db.execute(
                """
                INSERT INTO price_history (
                    item_id,
                    price,
                    currency
                    )
                VALUES (?, ?, ?)
                """,
                (item_id, price, currency)
                )
            await db.commit()
            return True

        except Exception:
            await db.rollback()
            raise


async def get_price_history(item_id: int) -> list[dict]:
    """
    Возвращает всю историю цен товара в хронологическом порядке
    (от старых записей к новым), для построения графика через matplotlib.
    """
    async with get_db_connection(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            '''
            SELECT price, currency, checked_at
            FROM price_history
            WHERE item_id = ?
            ORDER BY checked_at ASC, id ASC
            ''',
            (item_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        
        
# Блок для ручного тестирования
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())