# 🤖 Steam Price Tracker Bot

Telegram-бот, который следит за ценами на игры в Steam: пришли ссылку — бот запомнит
игру и её цену, каждый день проверяет её сам и присылает уведомление, когда цена
снижается.

> 🚧 **Статус:** проект в активной разработке (учебный проект по асинхронному Python).
> Основное уже работает: добавление игр, ежедневная проверка цен, уведомления
> о снижении, история цен. Дальше — тесты и графики (см. [Roadmap](#roadmap)).

![CI](https://github.com/Ibndaud/mp-price-tracker-bot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.31%2B-26A5E4?logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

## Возможности

- `/start`, `/help` — знакомство и справка
- `/list` — список отслеживаемых игр с кнопками удаления (если цена ещё не известна — бот подтянет её при показе)
- ссылка на `store.steampowered.com` → бот получает название и цену через официальный Steam API и сохраняет игру в БД; повторно добавить ту же игру нельзя (`UNIQUE` на пару «пользователь + игра»)
- 🕛 ежедневная проверка цен в 12:00 МСК — планировщик `APScheduler`
- 🔔 уведомление при снижении цены: было / стало + процент скидки
- 📈 история цен — каждая проверка пишется в таблицу `price_history`
- `/check` — ручной запуск проверки цен (доступен только администратору, `ADMIN_ID` в `.env`)
- SQLite через `aiosqlite` — всё асинхронно, без блокировки event loop

## Структура проекта

```
.
├── main.py               # точка входа: хэндлеры aiogram, планировщик, запуск бота
├── parser.py             # получение названия и цены через Steam API (aiohttp)
├── price_checker.py      # ежедневная проверка цен и уведомления о снижении
├── database.py           # слой БД: таблицы users, items, price_history (aiosqlite)
├── keyboards.py          # inline-клавиатура удаления (aiogram)
├── utils.py              # Steam App ID из ссылки, формат цены и списка
├── migrate.py            # миграция самой старой БД: колонка steam_app_id
├── migrate_prices.py     # миграция: цена в копейках, валюта, история цен
├── legacy/               # первая версия парсера (HTML вместо API) — история эволюции
│   └── steam_html_parser.py
├── .env.example          # шаблон переменных окружения
├── pyproject.toml        # зависимости и конфигурация ruff
└── uv.lock
```

## Установка и запуск

Нужны [Python 3.10+](https://www.python.org/) и [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Ibndaud/mp-price-tracker-bot.git
cd mp-price-tracker-bot
uv sync
```

Создайте файл `.env` рядом с кодом (см. [.env.example](.env.example)):

```
BOT_TOKEN=токен_от_@BotFather
ADMIN_ID=ваш_telegram_id
```

Запуск:

```bash
uv run python main.py
```

<details>
<summary>Старая база данных (до Steam App ID / цен в копейках)</summary>

```bash
uv run python migrate.py         # добавить колонку steam_app_id
uv run python migrate_prices.py  # цена в копейках, валюта, таблица истории
```

</details>

## Как это работает

1. Пользователь присылает ссылку → `utils.get_steam_app_id()` извлекает App ID игры
2. `parser.get_steam_price()` спрашивает официальный Steam API (`appdetails`) — это надёжнее парсинга HTML (первая версия парсера сохранена в `legacy/`)
3. Игра сохраняется в SQLite вместе с ценой в копейках и валютой
4. Раз в день `price_checker.check_prices()` обходит все игры: обновляет цены, дописывает историю и при снижении отправляет пользователю уведомление

## Roadmap

- [x] Добавление игр по ссылке Steam, `/list`, удаление кнопкой
- [x] Steam App ID и миграции БД
- [x] Ежедневная проверка цен и уведомления о снижении (APScheduler)
- [x] История цен
- [ ] Тесты (pytest)
- [ ] График истории цен
- [ ] Другие магазины, кроме Steam

## Лицензия

[MIT](LICENSE.txt)