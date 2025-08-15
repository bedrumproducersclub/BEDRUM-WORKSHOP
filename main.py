import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
import asyncio

# Загружаем .env локально
load_dotenv()

# Читаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
EVENT_TITLE = os.getenv("EVENT_TITLE")
EVENT_DATE = os.getenv("EVENT_DATE")
EVENT_CITY = os.getenv("EVENT_CITY")
PRICE_TEXT = os.getenv("PRICE_TEXT")
PAYMENT_TEXT = os.getenv("PAYMENT_TEXT")
IMAGE_URL_OR_FILE_ID = os.getenv("IMAGE_URL_OR_FILE_ID")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./database.sqlite3")

# Проверка переменных
required_vars = {
    "BOT_TOKEN": BOT_TOKEN,
    "ADMIN_IDS": ADMIN_IDS,
    "EVENT_TITLE": EVENT_TITLE,
    "EVENT_DATE": EVENT_DATE,
    "EVENT_CITY": EVENT_CITY,
    "PRICE_TEXT": PRICE_TEXT,
    "PAYMENT_TEXT": PAYMENT_TEXT,
    "IMAGE_URL_OR_FILE_ID": IMAGE_URL_OR_FILE_ID,
    "DATABASE_PATH": DATABASE_PATH
}

missing_vars = [k for k, v in required_vars.items() if not v]
if missing_vars:
    raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")

# Создаем бота
bot = Bot(BOT_TOKEN, default=ParseMode.MARKDOWN)
dp = Dispatcher()

# Кнопки
def main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить участие", callback_data="pay")
    return kb.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    caption = (
        f"*{EVENT_TITLE}*\n\n"
        f"📅 Дата: {EVENT_DATE}\n"
        f"📍 Город: {EVENT_CITY}\n\n"
        f"{PRICE_TEXT}"
    )
    await message.answer_photo(photo=IMAGE_URL_OR_FILE_ID, caption=caption, reply_markup=main_keyboard())

@dp.callback_query(F.data == "pay")
async def send_payment_info(callback: types.CallbackQuery):
    await callback.message.answer(PAYMENT_TEXT)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
