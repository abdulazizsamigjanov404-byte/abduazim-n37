from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    /start buyrug'i uchun handler.
    """
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="ℹ️ Qo'llanma", callback_data="help_callback")

    text = (
        f"👋 <b>Assalomu alaykum, {user_name}!</b>\n\n"
        "🎬 <b>Instagram Video Downloader</b> botiga xush kelibsiz!\n\n"
        "📥 Menga Instagram'dagi istalgan Reels, Post yoki Video havolasini yuboring — "
        "videoni yuklab beraman. Video ostidagi tugmalar orqali uni dumaloq video "
        "qilish yoki musiqasini MP3 qilib olish mumkin.\n\n"
        "<i>Boshlash uchun Instagram havolasini tashlang! 🚀</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard.as_markup())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    /help buyrug'i uchun handler.
    """
    text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "• Instagram ilovasidan video havolasini nusxalang va botga jo'nating.\n"
        "• Bot videoni oddiy video qilib yuboradi.\n"
        "• <b>⭕ Dumaloq qilish</b> tugmasi videoni dumaloq video ko'rinishiga keltiradi "
        "(60 soniyadan uzun bo'lsa, faqat boshidagi 60 soniya olinadi).\n"
        "• <b>🎵 Musiqa</b> tugmasi videodagi qo'shiqni aniqlab, uning to'liq versiyasini MP3 qilib yuboradi. "
        "Qo'shiq aniqlanmasa, videoning o'z ovozi yuboriladi.\n\n"
        "🧹 <b>Buyruqlar:</b>\n"
        "/start — Botni ishga tushirish\n"
        "/help — Qo'llanma"
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "help_callback")
async def process_help_callback(callback_query: types.CallbackQuery):
    """Inline tugma bosilganda qo'llanmani ko'rsatish"""
    await callback_query.answer()
    if callback_query.message:
        await cmd_help(callback_query.message)
