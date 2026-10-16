from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_items_keyboard(items: list) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру с кнопками удаления для каждого товара.
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
                callback_data=f"delete_{item['id']}"
            )
        )

    # as_markup() собирает финальный объект клавиатуры
    return builder.as_markup()