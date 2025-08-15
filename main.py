import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio

from texts import (
    EVENT_DESCRIPTION,
    ASK_NAME,
    ASK_PHONE,
    AFTER_FORM,
    THANKS_REGISTERED,
    REMIND_SEND_RECEIPT,
    ADMIN_NEW_STARTED,
    ADMIN_NEW_RECEIPT
)
from keyboards import main_keyboard, admin_keyboard

# ====== НАСТРОЙКИ ======
BOT_TOKEN = "ТОКЕН_ТВОЕГО_БОТА"
ADMIN_IDS = [123456789]  # ID админов
IMAGE_URL_OR_FILE_ID = "images/bedrum-ws-28-08.png"  # путь к картинке в проекте

# ====== ЛОГИ ======
logging.basicConfig(level=logging.INFO)

# ====== ИНИЦИАЛИЗАЦИЯ ======
bot = Bot(BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# ====== ХЭНДЛЕРЫ ======
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    caption = EVENT_DESCRIPTION
    await message.answer_photo(
        photo=FSInputFile(IMAGE_URL_OR_FILE_ID),
        caption=caption,
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "📝 Зарегистрироваться")
async def register(message: types.Message):
    await message.answer(ASK_NAME)

# ====== СТАРТ ======
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
