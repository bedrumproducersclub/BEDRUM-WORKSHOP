# BEDRUM WORKSHOP BOT

Минимальный Telegram-бот на **Python + aiogram v3** для регистрации на событие с оплатой по реквизитам и загрузкой чека.

## Локальный запуск

1) Установи зависимости:
```
pip install -r requirements.txt
```

2) Создай `.env` по примеру `.env.example` и заполни:
- `BOT_TOKEN` — токен бота
- `ADMIN_IDS` — ID админов через запятую (по умолчанию твой ID уже указан)
- `PAYMENT_TEXT` — твои реквизиты Kaspi/карта
- (опц.) `IMAGE_URL_OR_FILE_ID` — URL или file_id обложки
- (опц.) `DATABASE_PATH` — путь к базе (по умолчанию ./bedrum.sqlite3)

3) Запусти бота:
```
python main.py
```

## Railway деплой

1) Залей репозиторий на GitHub.
2) В Railway: **New Project → Deploy from GitHub**.
3) В **Variables** добавь минимум: `BOT_TOKEN`, `ADMIN_IDS`, `PAYMENT_TEXT`, (опц.) `IMAGE_URL_OR_FILE_ID`, `DATABASE_PATH=/data/bedrum.sqlite3`.
4) В **Settings → Volumes** создай том `/data`, чтобы база не терялась.
5) Procfile уже содержит: `worker: python main.py`.

## Что умеет бот

- Карточка события (картинка + описание) и кнопка **«Участвовать»**.
- Анкета: Имя → Фамилия → Телефон (без строгой валидации).
- Реквизиты + запрос чека (фото/файл). После чека — авто‑подтверждение.
- Сохранение прогресса в SQLite, заявки видны даже незавершённые.
- Админ-панель: просмотр заявок (вперёд/назад), «Показать чек», @username.
- Уведомления админу при старте регистрации и получении чека.
