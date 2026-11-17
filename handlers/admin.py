from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from stats import stats

router = Router()


def _keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Yangilash", callback_data="admin_refresh")
    return kb.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id if message.from_user else 0
    if not ADMIN_ID:
        await message.answer(
            "⚙️ Admin hali sozlanmagan.\n\n"
            f"Sizning Telegram ID: <code>{user_id}</code>\n"
            "Render'da <b>ADMIN_ID</b> o'zgaruvchisiga shu raqamni yozing."
        )
        return
    if user_id != ADMIN_ID:
        await message.answer("⛔️ Bu buyruq faqat admin uchun.")
        return
    await message.answer(stats.report(), reply_markup=_keyboard())


@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(callback: types.CallbackQuery):
    if not ADMIN_ID or callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ Faqat admin uchun", show_alert=True)
        return
    try:
        await callback.message.edit_text(stats.report(), reply_markup=_keyboard())
    except Exception:
        pass  # matn o'zgarmagan bo'lsa Telegram xato beradi
    await callback.answer("Yangilandi")
