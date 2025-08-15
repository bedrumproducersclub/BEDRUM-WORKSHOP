import os
import io
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile
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
IMAGE_URL = os.getenv("IMAGE_URL")
EVENT_TITLE = os.getenv("EVENT_TITLE", "")
EVENT_DATE = os.getenv("EVENT_DATE", "")
EVENT_CITY = os.getenv("EVENT_CITY", "")

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

class Reg(StatesGroup):
    name = State()
    phone = State()
    receipt = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def render_user_card(u: dict, pos: int, total: int) -> str:
    status = u.get("status") or "-"
    name = f"{u.get('first_name_input') or ''} {u.get('last_name_input') or ''}".strip() or "-"
    phone = u.get("phone") or "-"
    username = ("@" + u["username"]) if u.get("username") else "-"
    has_receipt = "Да" if u.get("receipt_file_id") else "Нет"
    return (
        f"*Заявка {pos}/{total}*\n"
        f"ID: `{u['user_id']}` | {username}\n"
        f"Имя Фамилия: {name}\n"
        f"Телефон: {phone}\n"
        f"Статус: `{status}`\n"
        f"Чек: {has_receipt}"
    )

# ===== Старт =====
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    db.upsert_user(message.from_user.id, message.from_user.username)
    await state.clear()
    await message.answer_photo(
        photo=IMAGE_URL,
        caption=EVENT_DESCRIPTION,
        reply_markup=start_kb(is_admin(message.from_user.id))
    )

# ===== Кнопка "Участвовать" =====
@dp.callback_query(F.data == "participate")
async def participate_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(ASK_NAME)
    await state.set_state(Reg.name)

@dp.message(Reg.name)
async def process_name(message: Message, state: FSMContext):
    # Имя + Фамилия в одном сообщении
    raw = " ".join(message.text.split()).strip()
    parts = raw.split(" ", 1)
    first = parts[0] if parts else ""
    last  = parts[1] if len(parts) > 1 else ""
    db.set_field(message.from_user.id, "first_name_input", first)
    db.set_field(message.from_user.id, "last_name_input", last)
    await message.answer(ASK_PHONE)
    await state.set_state(Reg.phone)

@dp.message(Reg.phone)
async def process_phone(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "phone", message.text.strip())
    await message.answer(AFTER_FORM)
    await state.set_state(Reg.receipt)

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

    if not file_id:
        await message.answer(REMIND_SEND_RECEIPT)
        return

    db.set_field(message.from_user.id, "receipt_file_id", file_id)
    db.set_field(message.from_user.id, "receipt_type", file_type)
    db.set_field(message.from_user.id, "status", "REGISTERED")

    # уведомим админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                ADMIN_NEW_RECEIPT.format(username=message.from_user.username or "no_username",
                                         user_id=message.from_user.id)
            )
        except Exception:
            pass

    await message.answer(THANKS_REGISTERED.format(
        title=EVENT_TITLE, date=EVENT_DATE, city=EVENT_CITY
    ))
    await state.clear()

@dp.message(Reg.receipt)
async def remind_receipt(message: Message):
    await message.answer(REMIND_SEND_RECEIPT)

# ===== Админ-панель =====
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    users = db.all_users()
    if not users:
        await callback.answer()
        await callback.message.answer("Нет заявок")
        return
    await callback.answer()
    text = render_user_card(users[0], pos=1, total=len(users))
    await callback.message.answer(text, reply_markup=admin_nav_kb(0, users[0]["user_id"]))

async def show_admin_user(cb: CallbackQuery, idx: int):
    users = db.all_users()
    total = len(users)
    if total == 0:
        await cb.answer()
        await cb.message.edit_text("Нет заявок")
        return
    if idx < 0: idx = 0
    if idx >= total: idx = total - 1
    u = users[idx]
    await cb.answer()
    await cb.message.edit_text(
        render_user_card(u, pos=idx+1, total=total),
        reply_markup=admin_nav_kb(idx, u["user_id"])
    )

@dp.callback_query(F.data.startswith("admin_prev:"))
async def admin_prev(cb: CallbackQuery):
    try:
        idx = int(cb.data.split(":")[1]) - 1
    except Exception:
        idx = 0
    await show_admin_user(cb, idx)

@dp.callback_query(F.data.startswith("admin_next:"))
async def admin_next(cb: CallbackQuery):
    try:
        idx = int(cb.data.split(":")[1]) + 1
    except Exception:
        idx = 0
    await show_admin_user(cb, idx)

@dp.callback_query(F.data.startswith("admin_receipt:"))
async def admin_receipt(cb: CallbackQuery):
    try:
        idx = int(cb.data.split(":")[1])
    except Exception:
        idx = 0
    users = db.all_users()
    if not users:
        await cb.answer("Нет заявок", show_alert=True); return
    if idx < 0 or idx >= len(users):
        await cb.answer("Некорректный индекс", show_alert=True); return
    u = users[idx]
    fid = u.get("receipt_file_id"); rtype = u.get("receipt_type")
    if not fid:
        await cb.answer("Чек отсутствует", show_alert=True); return
    await cb.answer()
    if rtype == "photo":
        await cb.message.answer_photo(fid, caption=f"Чек пользователя ID {u['user_id']}")
    else:
        await cb.message.answer_document(fid, caption=f"Чек пользователя ID {u['user_id']}")

@dp.callback_query(F.data.startswith("admin_delete:"))
async def admin_delete(cb: CallbackQuery):
    _, user_id, idx = cb.data.split(":")
    await cb.answer()
    await cb.message.answer(
        f"Удалить заявку пользователя {user_id}?",
        reply_markup=admin_confirm_delete_kb(int(user_id), int(idx))
    )

@dp.callback_query(F.data.startswith("admin_confirm_delete:"))
async def admin_confirm_delete(cb: CallbackQuery):
    _, user_id, idx = cb.data.split(":")
    db.delete_user(int(user_id))
    await cb.answer("Удалено")
    await show_admin_user(cb, int(idx))

@dp.callback_query(F.data.startswith("admin_cancel_delete:"))
async def admin_cancel_delete(cb: CallbackQuery):
    _, idx = cb.data.split(":")
    await cb.answer("Отменено")
    await show_admin_user(cb, int(idx))

# ===== Оплатившие — список сообщением =====
def _chunk_msgs(text: str, limit: int = 3900):
    # Telegram лимит ~4096, оставим запас на форматирование
    lines = text.splitlines(keepends=True)
    buf = ""
    for line in lines:
        if len(buf) + len(line) > limit:
            yield buf
            buf = ""
        buf += line
    if buf:
        yield buf

@dp.callback_query(F.data == "admin_list_paid")
async def admin_list_paid(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    users = db.all_users()
    paid = [u for u in users if (u.get("status") or "").upper() == "REGISTERED"]

    if not paid:
        await cb.answer()
        await cb.message.answer("Оплативших пока нет.")
        return

    # Формируем читаемый список
    header = f"*Оплатившие ({len(paid)})*\n"
    lines = []
    for i, u in enumerate(paid, 1):
        username = ("@" + u["username"]) if u.get("username") else "-"
        name = f"{u.get('first_name_input') or ''} {u.get('last_name_input') or ''}".strip() or "-"
        phone = u.get("phone") or "-"
        lines.append(f"{i}) {username} (id={u['user_id']}) — {name} — {phone}\n")

    text = header + "".join(lines)

    # Если список большой — разобьём на несколько сообщений
    for chunk in _chunk_msgs(text):
        await cb.message.answer(chunk)
    await cb.answer()

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
