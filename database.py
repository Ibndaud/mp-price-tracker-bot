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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT
            )
        ''')
        
        # 2. Таблица отслеживаемых товаров
        # id - внутренний номер записи (автоматически увеличивается - AUTOINCREMENT)
        # user_id - ID пользователя, который добавил ссылку (чтобы знать, кому писать)
        # url - сама ссылка на товар
        # name - название товара (чтобы красиво писать в уведомлении)
        # last_price - последняя известная цена (может быть пустой - NULL, пока мы её не спарсили)
        # steam_app_id - уникальный идентификатор игры в steam, получаемый из url
        await db.execute('''
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
        ''')
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);
        ''')
        
        # Сохраняем (коммитим) изменения в файл
        await db.commit()
        logger.info("База данных успешно инициализирована!")


async def add_user(user_id: int, username: str, first_name: str):
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
        ) -> bool:
    """Добавляет новую ссылку на товар для конкретного пользователя"""
    async with get_db_connection(DB_NAME) as db:
        cursor = await db.execute(
            '''
            INSERT INTO items 
            (user_id, url, name, last_price, currency, steam_app_id) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, steam_app_id) DO NOTHING
            ''',
            (user_id, url, name, last_price, currency, steam_app_id)
        )
        await db.commit()
        return cursor.rowcount > 0


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

        
# Блок для ручного тестирования
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())