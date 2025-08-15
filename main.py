import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
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
import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

# Ссылка на raw картинку GitHub
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

# Старт
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    db.upsert_user(message.from_user.id, message.from_user.username)
    await state.clear()
    await message.answer_photo(
        photo=IMAGE_URL_OR_FILE_ID,
        caption=EVENT_DESCRIPTION,
        reply_markup=start_kb(is_admin(message.from_user.id))
    )

# Кнопка "Участвовать"
@dp.callback_query(F.data == "participate")
async def participate_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(ASK_NAME)
    await state.set_state(Reg.name)

# Ввод имени
@dp.message(Reg.name)
async def process_name(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "first_name_input", message.text)
    await message.answer(ASK_PHONE)
    await state.set_state(Reg.phone)

# Ввод телефона
@dp.message(Reg.phone)
async def process_phone(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "phone", message.text)
    await message.answer(AFTER_FORM)
    await state.set_state(Reg.receipt)

# Приём чека
@dp.message(Reg.receipt, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def process_receipt(message: Message, state: FSMContext):
    file_id = None
    file_type = None
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"

    if file_id:
        db.set_field(message.from_user.id, "receipt_file_id", file_id)
        db.set_field(message.from_user.id, "receipt_type", file_type)
        db.set_field(message.from_user.id, "status", "RECEIPT_SENT")
        await message.answer(THANKS_REGISTERED.format(
            title=os.getenv("EVENT_TITLE"),
            date=os.getenv("EVENT_DATE"),
            city=os.getenv("EVENT_CITY")
        ))
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                ADMIN_NEW_RECEIPT.format(username=message.from_user.username, user_id=message.from_user.id)
            )
    await state.clear()

# Панель админа
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    users = db.all_users()
    if not users:
        await callback.message.answer("Нет заявок")
        return
    await callback.answer()
    await callback.message.answer(
        f"Всего заявок: {len(users)}",
        reply_markup=admin_nav_kb(0, users[0]["user_id"])
    )

# Навигация по заявкам
@dp.callback_query(F.data.startswith("admin_prev"))
async def admin_prev(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    users = db.all_users()
    if idx > 0:
        idx -= 1
    await show_admin_user(callback, users, idx)

@dp.callback_query(F.data.startswith("admin_next"))
async def admin_next(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    users = db.all_users()
    if idx < len(users) - 1:
        idx += 1
    await show_admin_user(callback, users, idx)

async def show_admin_user(callback: CallbackQuery, users, idx):
    user = users[idx]
    await callback.answer()
    await callback.message.edit_text(
        f"ID: {user['user_id']}\n"
        f"Username: @{user['username']}\n"
        f"Имя: {user['first_name_input']}\n"
        f"Телефон: {user['phone']}\n"
        f"Статус: {user['status']}",
        reply_markup=admin_nav_kb(idx, user['user_id'])
    )

# Показ чека
@dp.callback_query(F.data.startswith("admin_receipt"))
async def admin_receipt(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    users = db.all_users()
    if 0 <= idx < len(users):
        user = users[idx]
        if user["receipt_type"] == "photo":
            await callback.message.answer_photo(user["receipt_file_id"])
        elif user["receipt_type"] == "document":
            await callback.message.answer_document(user["receipt_file_id"])
        else:
            await callback.message.answer("Чек отсутствует.")
    await callback.answer()

# Удаление заявки
@dp.callback_query(F.data.startswith("admin_delete"))
async def admin_delete(callback: CallbackQuery):
    _, user_id, idx = callback.data.split(":")
    await callback.message.answer(
        f"Удалить заявку пользователя {user_id}?",
        reply_markup=admin_confirm_delete_kb(int(user_id), int(idx))
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_confirm_delete"))
async def admin_confirm_delete(callback: CallbackQuery):
    _, user_id, idx = callback.data.split(":")
    db.delete_user(int(user_id))
    await callback.message.answer("Заявка удалена.")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_delete"))
async def admin_cancel_delete(callback: CallbackQuery):
    await callback.message.answer("Удаление отменено.")
    await callback.answer()

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
