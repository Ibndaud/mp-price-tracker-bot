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

# Блок для ручного тестирования
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())