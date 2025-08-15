import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from db import init_db
from texts import get_event_caption

logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
IMAGE_PATH = os.getenv("IMAGE_PATH")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./bedrum.sqlite3")

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env!")

bot = Bot(BOT_TOKEN, default=ParseMode.MARKDOWN)
dp = Dispatcher()

# Инициализация базы
init_db(DATABASE_PATH)

# Главное меню
def main_keyboard():
    kb = [
        [KeyboardButton(text="Отправить трек")],
        [KeyboardButton(text="Панель админа")] if ADMIN_IDS else []
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    caption = get_event_caption()
    try:
        with open(IMAGE_PATH, "rb") as photo:
            await message.answer_photo(photo=photo, caption=caption, reply_markup=main_keyboard())
    except Exception as e:
        await message.answer(f"Ошибка загрузки изображения: {e}", reply_markup=main_keyboard())

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
