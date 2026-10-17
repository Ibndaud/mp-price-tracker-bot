# 🤖 Steam Price Tracker Bot

Telegram-бот, который следит за ценами на игры в Steam: пришли ссылку — бот запомнит
игру и её текущую цену, а список отслеживаемых игр всегда под рукой.

> 🚧 **Статус:** проект в активной разработке (учебный проект по асинхронному Python).
> Бот уже умеет добавлять игры и вести список; периодическая проверка цен и уведомления —
> в планах (см. [Roadmap](#roadmap)).

![CI](https://github.com/Ibndaud/mp-price-tracker-bot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.31%2B-26A5E4?logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

## Возможности

- `/start`, `/help` — знакомство и справка
- `/list` — список отслеживаемых игр с кнопками удаления
- ссылка на `store.steampowered.com` → бот парсит название и текущую цену и сохраняет в БД
- пользователи и игры — SQLite через `aiosqlite`, без блокировки event loop

## Структура проекта

```
.
├── main.py          # точка входа: хэндлеры aiogram, запуск long polling
├── parser.py        # асинхронный парсер страницы Steam (aiohttp + BeautifulSoup)
├── database.py      # слой БД: таблицы users и items (aiosqlite)
├── keyboards.py     # inline-клавиатура удаления (aiogram)
├── utils.py         # извлечение Steam App ID из ссылки
├── migrate.py       # разовая миграция: колонка steam_app_id для старой БД
├── .env.example     # шаблон переменных окружения
├── pyproject.toml   # зависимости и конфигурация ruff
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
```

Запуск:

```bash
uv run python main.py
```

<details>
<summary>Старая база данных без колонки <code>steam_app_id</code></summary>

```bash
uv run python migrate.py
```

</details>

## Roadmap

- [x] Добавление игр по ссылке Steam, `/list`, удаление кнопкой
- [x] Steam App ID в БД (миграция `migrate.py`)
- [ ] Периодическая проверка цен (планировщик)
- [ ] Уведомления об изменении цены
- [ ] История цен и скидки

## Лицензия

MIT — см. [LICENSE.txt](LICENSE.txt).
