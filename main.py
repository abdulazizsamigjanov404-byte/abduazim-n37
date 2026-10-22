import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import router as main_router

# Log tizimini sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s : %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("InstagramBot")


async def main():
    """Botni ishga tushiruvchi asosiy funksiya"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "DIQQAT! BOT_TOKEN ko'rsatilmagan!\n"
            ".env fayliga kiring va BOT_TOKEN qatoriga Telegram botingiz\n"
            "tokenini kiriting. (Tokenni @BotFather orqali olasiz)\n"
            + "=" * 60
        )
        return

    # Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(main_router)

    # Bot ma'lumotlarini olish va logga yozish
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username} ({bot_info.full_name})")
    except Exception as e:
        logger.error(f"Telegram Bot API ga ulanishda xatolik: {e}")
        await bot.session.close()
        return

    # Bot o'chirilgan vaqtda kelgan eski xabarlarni o'tkazib yuborish (drop_pending_updates)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        logger.info("Xabarlarni qabul qilish boshlandi (Polling)...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Bot to'xtatilmoqda...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
