import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from db import DB
import texts

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
EVENT_TITLE = os.getenv("EVENT_TITLE")
EVENT_DATE = os.getenv("EVENT_DATE")
EVENT_CITY = os.getenv("EVENT_CITY")
PRICE_TEXT = os.getenv("PRICE_TEXT")
PAYMENT_TEXT = os.getenv("PAYMENT_TEXT")
IMAGE_SRC = os.getenv("IMAGE_URL_OR_FILE_ID")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./bedrum.sqlite3")

bot = Bot(BOT_TOKEN, default=ParseMode.MARKDOWN)
dp = Dispatcher()
db = DB(DATABASE_PATH)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def start_kb(is_admin=False):
    buttons = [["Записаться"], ["Реквизиты для оплаты"]]
    if is_admin:
        buttons.append(["Панель админа"])
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=b) for b in row] for row in buttons], resize_keyboard=True)

async def send_event_card(message: Message):
    caption = f"*{EVENT_TITLE}*\n\n{texts.EVENT_DESCRIPTION}\n\n{PRICE_TEXT}"
    kb = start_kb(is_admin=is_admin(message.from_user.id))
    try:
        await message.answer_photo(IMAGE_SRC, caption=caption, reply_markup=kb)
    except Exception:
        await message.answer(caption, reply_markup=kb)

@dp.message(F.text == "/start")
async def on_start(message: Message):
    await send_event_card(message)

@dp.message(F.text == "Реквизиты для оплаты")
async def send_payment(message: Message):
    await message.answer(PAYMENT_TEXT)

# Остальной код бота — тут твои обработчики записи и панели админа
