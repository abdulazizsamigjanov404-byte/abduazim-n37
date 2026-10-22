from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    /start buyrug'i uchun handler. Foydalanuvchini samimiy kutib oladi
    va botdan qanday foydalanishni tushuntiradi.
    """
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="ℹ️ Qo'llanma", callback_data="help_callback")
    keyboard.adjust(1)

    text = (
        f"👋 <b>Assalomu alaykum, {user_name}!</b>\n\n"
        "🎬 <b>Instagram Video Downloader</b> botiga xush kelibsiz!\n\n"
        "Men sizga Instagram’dagi istalgan <b>Reels</b>, <b>Post</b> va <b>IGTV</b> "
        "videolarini sifatli qilib yuklab berishim mumkin.\n\n"
        "📌 <b>Foydalanish juda oson:</b>\n"
        "Shunchaki videoning havolasini (linkini) menga yuboring!\n\n"
        "<i>Masalan: https://www.instagram.com/reel/C...</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard.as_markup())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    /help buyrug'i uchun handler.
    """
    text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1️⃣ Instagram ilovasida o'zingizga yoqqan videoni oching.\n"
        "2️⃣ <b>Ulashish (Share)</b> tugmasini bosib, <b>Havoladan nusxa olish (Copy Link)</b> ni tanlang.\n"
        "3️⃣ Nusxalangan havolani ushbu botga jo'nating.\n"
        "4️⃣ Bot videoni yuklab olib, to'g'ridan-to'g'ri Telegram orqali sizga yuboradi!\n\n"
        "⚠️ <b>Eslatma:</b>\n"
        "• Faqat ochiq (public) akkauntdagi videolar yuklanadi.\n"
        "• Telegram Bot API qoidalariga ko'ra video hajmi 50 MB gacha bo'lishi kerak."
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "help_callback")
async def process_help_callback(callback_query: types.CallbackQuery):
    """Inline tugma bosilganda qo'llanmani ko'rsatish"""
    text = (
        "📖 <b>Tezkor yo'riqnoma:</b>\n\n"
        "1. Instagram'dan video havolasini nusxalang.\n"
        "2. Ushbu chatga jo'nating.\n"
        "3. Bir necha soniyada tayyor video faylni qabul qilib oling! 🚀\n\n"
        "<i>Sinab ko'rish uchun hoziroq havola yuboring!</i>"
    )
    await callback_query.answer()
    if callback_query.message:
        await callback_query.message.answer(text, parse_mode="HTML")
