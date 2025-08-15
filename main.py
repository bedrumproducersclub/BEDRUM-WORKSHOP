import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
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
from keyboards import start_kb, admin_nav_kb, admin_confirm_delete_kb
import db  # если была логика сохранения

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

# Вот именно ссылка на raw картинку GitHub
IMAGE_URL_OR_FILE_ID = "https://raw.githubusercontent.com/bedrumproducersclub/BEDRUM-WORKSHOP/main/images/bedrum_ws_28_08.png"

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

class Reg(StatesGroup):
    name = State()
    phone = State()
    receipt = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    db.upsert_user(message.from_user.id)
    await state.clear()
    caption = EVENT_DESCRIPTION
    await message.answer_photo(
        photo=IMAGE_URL_OR_FILE_ID,
        caption=caption,
        reply_markup=start_kb(is_admin(message.from_user.id))
    )

# ... остальная логика регистрации, как раньше, без изменений ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
