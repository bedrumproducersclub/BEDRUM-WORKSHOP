import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from texts import (
    EVENT_DESCRIPTION, ASK_NAME, ASK_PHONE,
    AFTER_FORM, THANKS_REGISTERED, REMIND_SEND_RECEIPT,
    ADMIN_NEW_STARTED, ADMIN_NEW_RECEIPT
)
from keyboards import start_kb
import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
IMAGE_URL = os.getenv("IMAGE_URL")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./bedrum.sqlite3")

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

# Создаём объект базы
database = db.DB(DATABASE_PATH)

class Reg(StatesGroup):
    name = State()
    phone = State()
    receipt = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    database.upsert_user(message.from_user.id, message.from_user.username)
    await state.clear()
    await message.answer_photo(
        photo=IMAGE_URL,
        caption=EVENT_DESCRIPTION,
        reply_markup=start_kb(is_admin(message.from_user.id))
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
