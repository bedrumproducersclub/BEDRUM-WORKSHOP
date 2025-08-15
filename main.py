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

from db import DB
from keyboards import start_kb, admin_nav_kb, admin_confirm_delete_kb
import texts

logging.basicConfig(level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
EVENT_TITLE = os.getenv("EVENT_TITLE", "BEDRUM WORKSHOP")
EVENT_DATE = os.getenv("EVENT_DATE", "26 августа, 18:00")
EVENT_CITY = os.getenv("EVENT_CITY", "Алматы")
PRICE_TEXT = os.getenv("PRICE_TEXT", "Стоимость участия: 20 000 ₸")
PAYMENT_TEXT = os.getenv("PAYMENT_TEXT", "Оплата по номеру Kaspi ...")
IMAGE_SRC = os.getenv("IMAGE_URL_OR_FILE_ID", "").strip() or None
DB_PATH = os.getenv("DATABASE_PATH", "./bedrum.sqlite3")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())
db = DB(DB_PATH)

class Reg(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_receipt = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def send_event_card(message: Message):
    caption = f"*{EVENT_TITLE}*\n\n{texts.EVENT_DESCRIPTION}\n\n{PRICE_TEXT}"
    kb = start_kb(is_admin=is_admin(message.from_user.id))
    if IMAGE_SRC:
        try:
            await message.answer_photo(IMAGE_SRC, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(caption, reply_markup=kb)

@dp.message(CommandStart())
async def on_start(message: Message, state: FSMContext):
    db.upsert_user(message.from_user.id, message.from_user.username)
    await state.clear()
    await send_event_card(message)

@dp.callback_query(F.data == "participate")
async def on_participate(cb: CallbackQuery, state: FSMContext):
    user = cb.from_user
    db.upsert_user(user.id, user.username)
    db.set_field(user.id, "status", "FORM_START")
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                texts.ADMIN_NEW_STARTED.format(
                    username=user.username or "no_username",
                    user_id=user.id,
                    status="FORM_START"
                )
            )
        except Exception:
            pass
    await cb.message.answer(texts.ASK_NAME)
    await state.set_state(Reg.waiting_name)
    await cb.answer()

@dp.message(Reg.waiting_name, F.text.len() > 0)
async def got_name(message: Message, state: FSMContext):
    raw = " ".join(message.text.split()).strip()
    if not raw:
        await message.answer(texts.ASK_NAME)
        return
    parts = raw.split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    db.set_field(message.from_user.id, "first_name_input", first)
    db.set_field(message.from_user.id, "last_name_input", last)

    await message.answer(texts.ASK_PHONE)
    await state.set_state(Reg.waiting_phone)

@dp.message(Reg.waiting_phone, F.text.len() > 0)
async def got_phone(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "phone", message.text.strip())
    db.set_field(message.from_user.id, "status", "AWAITING_RECEIPT")
    pay_text = texts.AFTER_FORM.format(payment=PAYMENT_TEXT)
    await message.answer(pay_text)
    await state.set_state(Reg.waiting_receipt)

@dp.message(Reg.waiting_receipt, F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT}))
async def got_receipt(message: Message, state: FSMContext):
    file_id = None
    rtype = None
    if message.content_type == ContentType.PHOTO:
        file_id = message.photo[-1].file_id
        rtype = "photo"
    elif message.content_type == ContentType.DOCUMENT:
        file_id = message.document.file_id
        rtype = "document"

    if file_id:
        db.set_field(message.from_user.id, "receipt_file_id", file_id)
        db.set_field(message.from_user.id, "receipt_type", rtype)
        db.set_field(message.from_user.id, "status", "REGISTERED")
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    texts.ADMIN_NEW_RECEIPT.format(
                        username=message.from_user.username or "no_username",
                        user_id=message.from_user.id
                    )
                )
            except Exception:
                pass
        thanks = texts.THANKS_REGISTERED.format(
            title=EVENT_TITLE, date=EVENT_DATE, city=EVENT_CITY
        )
        await message.answer(thanks)
        await state.clear()
    else:
        await message.answer(texts.REMIND_SEND_RECEIPT)

@dp.message(Reg.waiting_receipt)
async def wrong_receipt_type(message: Message, state: FSMContext):
    await message.answer(texts.REMIND_SEND_RECEIPT)

def render_user_card(u: dict) -> str:
    status = u.get("status") or "-"
    name = (u.get("first_name_input") or "") + " " + (u.get("last_name_input") or "")
    name = name.strip() or "-"
    phone = u.get("phone") or "-"
    username = ("@" + u["username"]) if u.get("username") else "-"
    has_receipt = "Да" if u.get("receipt_file_id") else "Нет"
    return (
        f"*Заявка*\n"
        f"ID: `{u['user_id']}` | {username}\n"
        f"Имя Фамилия: {name}\n"
        f"Телефон: {phone}\n"
        f"Статус: `{status}`\n"
        f"Чек: {has_receipt}"
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    users = db.all_users()
    if not users:
        await cb.message.answer("Заявок пока нет.")
        await cb.answer()
        return
    idx = 0
    text = render_user_card(users[idx])
    await cb.message.answer(text, reply_markup=admin_nav_kb(idx, users[idx]["user_id"]))
    await cb.answer()

@dp.callback_query(F.data.startswith("admin_prev:"))
async def admin_prev(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, idx_s = cb.data.split(":")
    idx = max(0, int(idx_s) - 1)
    users = db.all_users()
    if not users:
        await cb.answer()
        return
    text = render_user_card(users[idx])
    await cb.message.edit_text(text, reply_markup=admin_nav_kb(idx, users[idx]["user_id"]))
    await cb.answer()

@dp.callback_query(F.data.startswith("admin_next:"))
async def admin_next(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, idx_s = cb.data.split(":")
    idx = int(idx_s) + 1
    users = db.all_users()
    if not users:
        await cb.answer()
        return
    if idx >= len(users):
        idx = len(users) - 1
    text = render_user_card(users[idx])
    await cb.message.edit_text(text, reply_markup=admin_nav_kb(idx, users[idx]["user_id"]))
    await cb.answer()

@dp.callback_query(F.data.startswith("admin_receipt:"))
async def admin_receipt(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, idx_s = cb.data.split(":")
    idx = int(idx_s)
    users = db.all_users()
    if not users:
        await cb.answer()
        return
    u = users[min(max(idx, 0), len(users)-1)]
    file_id = u.get("receipt_file_id")
    rtype = u.get("receipt_type")
    if not file_id:
        await cb.answer("Чек не приложен.", show_alert=True)
        return
    try:
        if rtype == "photo":
            await cb.message.answer_photo(
                file_id,
                caption=f"Чек от @{u.get('username') or 'no_username'} (id={u['user_id']})"
            )
        else:
            await cb.message.answer_document(
                file_id,
                caption=f"Чек от @{u.get('username') or 'no_username'} (id={u['user_id']})"
            )
    except Exception:
        await cb.message.answer("Не удалось показать чек (возможно, файл недоступен).")
    await cb.answer()

# --- Удаление заявки (двухшаговое подтверждение) ---

@dp.callback_query(F.data.startswith("admin_delete:"))
async def admin_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, user_id_s, idx_s = cb.data.split(":")
    user_id = int(user_id_s)
    idx = int(idx_s)
    await cb.message.edit_text(
        f"Удалить заявку пользователя ID `{user_id}`? Это действие необратимо.",
        reply_markup=admin_confirm_delete_kb(user_id, idx),
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("admin_confirm_delete:"))
async def admin_confirm_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, user_id_s, idx_s = cb.data.split(":")
    user_id = int(user_id_s)
    idx = int(idx_s)

    # удаляем пользователя
    db.delete_user(user_id)

    # подготавливаем следующий экран
    users = db.all_users()
    if not users:
        await cb.message.edit_text("Заявка удалена. Заявок больше нет.")
        await cb.answer("Удалено")
        return

    # после удаления остаёмся на том же индексе (он «сдвинется» на следующего)
    if idx >= len(users):
        idx = len(users) - 1
    text = render_user_card(users[idx])
    await cb.message.edit_text(text, reply_markup=admin_nav_kb(idx, users[idx]["user_id"]))
    await cb.answer("Удалено")

@dp.callback_query(F.data.startswith("admin_cancel_delete:"))
async def admin_cancel_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Недостаточно прав.", show_alert=True)
        return
    _, idx_s = cb.data.split(":")
    idx = int(idx_s)
    users = db.all_users()
    if not users:
        await cb.message.edit_text("Заявок пока нет.")
        await cb.answer()
        return
    if idx >= len(users):
        idx = len(users) - 1
    text = render_user_card(users[idx])
    await cb.message.edit_text(text, reply_markup=admin_nav_kb(idx, users[idx]["user_id"]))
    await cb.answer("Отменено")

@dp.message()
async def any_message(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.username)
    await send_event_card(message)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
