import aiosqlite

# Имя файла нашей базы данных (создастся автоматически рядом с кодом)
DB_NAME = "price_tracker.db"

async def init_db():
    """
    Создает таблицы в базе данных, если их еще нет.
    Эту функцию мы будем вызывать при старте бота.
    """
    # Открываем асинхронное соединение с файлом БД
    async with aiosqlite.connect(DB_NAME) as db:
        
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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                name TEXT,
                last_price TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) 
            )
        ''')
        
        # Сохраняем (коммитим) изменения в файл
        await db.commit()
        print("База данных успешно инициализирована!")

async def add_user(user_id: int, username: str, first_name: str):
    """Добавляет пользователя в БД, если его там еще нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        # INSERT OR IGNORE означает: "Вставь данные, а если такой id уже есть - просто проигнорируй и не выдавай ошибку"
        await db.execute(
            'INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        await db.commit()

async def add_item(user_id: int, url: str, last_price: str):
    """Добавляет новую ссылку на товар для конкретного пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO items (user_id, url, last_price) VALUES (?, ?, ?)',
            (user_id, url, last_price)
        )
        await db.commit()
        
# Блок для ручного тестирования
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())