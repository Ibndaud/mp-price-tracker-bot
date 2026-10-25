from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_items_keyboard(items: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру с кнопками удаления для текущей страницы
    + строка навигации между страницами (если страниц больше одной).
    items — список словарей [{id, name, url, last_price}, ...]
    """
    # Builder — удобный помощник для сборки клавиатур
    # Позволяет добавлять кнопки по одной, не думая о рядах вручную
    builder = InlineKeyboardBuilder()

    for item in items:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 Удалить: {item['name'] or 'Без названия'}",
                # callback_data — это "начинка" кнопки
                # Приходит боту когда пользователь нажмёт
                # Формат "delete_5" потом разберём на части
                callback_data=f"delete_{item['id']}_{page}"
                )
            )

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}")
        )
    if total_pages > 1:
        # Кнопка-индикатор, не кликабельна по смыслу — просто показывает текущую позицию
        nav_row.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page + 1}")
        )

    if nav_row:
        builder.row(*nav_row)

    # as_markup() собирает финальный объект клавиатуры
    return builder.as_markup()