from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def start_kb(is_admin: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎟 Участвовать", callback_data="participate")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠 Панель админа", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_nav_kb(idx: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_prev:{idx}"),
            InlineKeyboardButton(text="▶️ Далее", callback_data=f"admin_next:{idx}")
        ],
        [InlineKeyboardButton(text="🧾 Показать чек", callback_data=f"admin_receipt:{idx}")],
        [InlineKeyboardButton(text="🗑 Удалить заявку", callback_data=f"admin_delete:{user_id}:{idx}")],
        [InlineKeyboardButton(text="📋 Оплатившие", callback_data="admin_list_paid")]
    ])

def admin_confirm_delete_kb(user_id: int, idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin_confirm_delete:{user_id}:{idx}"),
            InlineKeyboardButton(text="↩️ Отмена", callback_data=f"admin_cancel_delete:{idx}")
        ]
    ])
