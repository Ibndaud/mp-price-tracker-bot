import asyncio
import aiosqlite


DB_NAME = "price_tracker.db"


async def migrate_prices():

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("PRAGMA foreign_keys = OFF")

        try:
            await db.execute("BEGIN")

            # Создаём новую таблицу
            await db.execute("""
                CREATE TABLE items_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    name TEXT,
                    last_price INTEGER,
                    currency TEXT NOT NULL DEFAULT 'RUB',
                    steam_app_id INTEGER NOT NULL,

                    FOREIGN KEY(user_id) 
                    REFERENCES users(id) ON DELETE CASCADE,

                    UNIQUE(user_id, steam_app_id)
                )
                """)

            # Переносим существующие игры
            await db.execute("""
                INSERT INTO items_new (
                    id,
                    user_id,
                    url,
                    name,
                    last_price,
                    currency,
                    steam_app_id
                )
                SELECT
                    id,
                    user_id,
                    url,
                    name,
                    NULL,
                    'RUB',
                    steam_app_id
                FROM items
                """)

            # Удаляем старую таблицу
            await db.execute("DROP TABLE items")

            # Переименовываем новую
            await db.execute(
                "ALTER TABLE items_new RENAME TO items"
            )

            # Восстанавливаем индекс
            await db.execute("""
                CREATE INDEX idx_items_user_id ON items(user_id)
                """)

            await db.commit()

        except Exception:
            await db.rollback()
            raise

        finally:
            await db.execute("PRAGMA foreign_keys = ON")

        print("✅ Миграция цен успешно завершена!")


if __name__ == "__main__":
    asyncio.run(migrate_prices())