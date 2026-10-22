from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ai_service import clear_user_history

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    /start buyrug'i uchun handler.
    """
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="ℹ️ Qo'llanma", callback_data="help_callback")
    keyboard.button(text="🧹 Suhbatni tozalash", callback_data="clear_callback")
    keyboard.adjust(1, 1)

    text = (
        f"👋 <b>Assalomu alaykum, {user_name}!</b>\n\n"
        "🎬 <b>Instagram Video Downloader & 🤖 AI Suhbatchi</b> botiga xush kelibsiz!\n\n"
        "📌 <b>Bot imkoniyatlari:</b>\n"
        "1. 📥 <b>Instagram Video:</b> Menga Instagram'dagi istalgan Reels, Post yoki Video havolasini yuboring — bir zumda yuklab beraman.\n"
        "2. 🧠 <b>Aqlli AI Suhbatchi:</b> Menga istalgan savolingizni bering, maslahat so'rang yoki shunchaki suhbatlashing!\n\n"
        "<i>Boshlash uchun Instagram havolasini tashlang yoki biror savol yozing! 🚀</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard.as_markup())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    /help buyrug'i uchun handler.
    """
    text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "📥 <b>Instagramdan video yuklash:</b>\n"
        "• Instagram ilovasidan video havolasini nusxalang va botga jo'nating.\n"
        "• Bot videoni yuklab olib, tayyor video qilib yuboradi.\n\n"
        "🤖 <b>AI Suhbatchi:</b>\n"
        "• Botga istalgan mavzuda xabar yozing (masalan: <i>'Dasturlashni qanday o'rgansam bo'ladi?'</i> yoki <i>'Menga motivatsiya ber'</i>).\n"
        "• AI sizning xabarlaringiz kontekstini eslab qoladi.\n"
        "• Yangi mavzudan boshlash uchun /clear buyrug'ini yuborishingiz mumkin.\n\n"
        "🧹 <b>Buyruqlar:</b>\n"
        "/start — Botni ishga tushirish\n"
        "/help — Qo'llanma\n"
        "/clear — AI bilan suhbat tarixini tozalash"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """AI suhbat tarixini tozalash buyrug'i"""
    if message.from_user:
        clear_user_history(message.from_user.id)
    await message.answer("🧹 <b>Suhbat xotirasi tozalandi!</b> Yangi mavzuda suhbatlashishimiz mumkin. 😊", parse_mode="HTML")


@router.callback_query(lambda c: c.data == "help_callback")
async def process_help_callback(callback_query: types.CallbackQuery):
    """Inline tugma bosilganda qo'llanmani ko'rsatish"""
    await callback_query.answer()
    if callback_query.message:
        await cmd_help(callback_query.message)


@router.callback_query(lambda c: c.data == "clear_callback")
async def process_clear_callback(callback_query: types.CallbackQuery):
    """Inline tugma orqali suhbatni tozalash"""
    if callback_query.from_user:
        clear_user_history(callback_query.from_user.id)
    await callback_query.answer("Suhbat xotirasi tozalandi! ✅", show_alert=True)
    if callback_query.message:
        await callback_query.message.answer("🧹 <b>Suhbat xotirasi tozalandi!</b> Yangi savolingizni berishingiz mumkin.", parse_mode="HTML")
