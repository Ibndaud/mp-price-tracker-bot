import asyncio
import aiosqlite

from utils import get_steam_app_id


DB_NAME = "price_tracker.db"


async def migrate():

    async with aiosqlite.connect(DB_NAME) as db:

        # Проверяем существующие колонки
        async with db.execute(
            "PRAGMA table_info(items)"
        ) as cursor:

            columns = await cursor.fetchall()

        column_names = [column[1] for column in columns]

        # Добавляем колонку, если её ещё нет
        if "steam_app_id" not in column_names:

            await db.execute(
                """
                ALTER TABLE items
                ADD COLUMN steam_app_id INTEGER
                """
            )

        # Получаем существующие товары
        async with db.execute(
            """
            SELECT id, user_id, url
            FROM items
            """
        ) as cursor:

            items = await cursor.fetchall()

        # Заполняем Steam App ID
        for item_id, user_id, url in items:

            steam_app_id = get_steam_app_id(url)

            if steam_app_id is None:
                print(f"Пропускаем некорректную ссылку: {url}")
                continue

            await db.execute(
                """
                UPDATE items
                SET steam_app_id = ?
                WHERE id = ?
                """,
                (steam_app_id, item_id)
            )

        await db.commit()

        print("Миграция завершена!")


if __name__ == "__main__":
    asyncio.run(migrate())