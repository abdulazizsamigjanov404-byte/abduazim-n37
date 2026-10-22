import logging
from aiogram import Router, types, Bot
from aiogram.enums import ChatAction
from aiogram.types import FSInputFile

from downloader import (
    extract_instagram_url,
    download_instagram_video,
    DownloadError,
    VideoTooLargeError,
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(lambda message: bool(message.text and extract_instagram_url(message.text)))
async def handle_instagram_link(message: types.Message, bot: Bot):
    """
    Instagram havolasi kelganda ishga tushadigan asosiy handler.
    Videoni yuklaydi va foydalanuvchiga yuboradi.
    """
    raw_text = message.text or ""
    url = extract_instagram_url(raw_text)
    if not url:
        return

    # Foydalanuvchiga jarayon boshlanganini bildirish
    status_msg = await message.answer(
        "⏳ <b>Video qidirilmoqda va yuklanmoqda...</b>\n<i>Iltimos, biroz kuting.</i>",
        parse_mode="HTML"
    )

    download_result = None

    try:
        # Telegram chatida "video yuklanmoqda" holatini ko'rsatish
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)

        # Videoni asinxron yuklab olish
        download_result = await download_instagram_video(url)

        # Telegramga jo'natish uchun FSInputFile tayyorlaymiz
        video_file = FSInputFile(download_result.file_path)

        # Video tavsifini tayyorlash
        bot_info = await bot.get_me()
        bot_username = bot_info.username or "Bot"

        caption_parts = ["🎬 <b>Instagram Video</b>"]
        if download_result.title:
            caption_parts.append(f"\n📝 <b>Tavsif:</b> {download_result.title}")
        
        caption_parts.append(f"\n🤖 <b>Yuklab beruvchi:</b> @{bot_username}")
        caption = "\n".join(caption_parts)

        # Videoni foydalanuvchiga jo'natish
        await message.answer_video(
            video=video_file,
            caption=caption,
            duration=download_result.duration,
            width=download_result.width,
            height=download_result.height,
            parse_mode="HTML",
            supports_streaming=True
        )

        # "Yuklanmoqda..." xabarini o'chirib tashlaymiz
        try:
            await status_msg.delete()
        except Exception:
            pass

    except VideoTooLargeError as e:
        await status_msg.edit_text(
            f"❌ <b>Xatolik:</b>\n{str(e)}",
            parse_mode="HTML"
        )
    except DownloadError as e:
        await status_msg.edit_text(
            f"⚠️ <b>Yuklab bo'lmadi:</b>\n{str(e)}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception(f"Kutilmagan xatolik: {e}")
        await status_msg.edit_text(
            "❌ <b>Kechirasiz, videoni yuklab olishda xatolik yuz berdi.</b>\n"
            "Iltimos, havola to'g'riligini va video hamma uchun ochiqligini tekshirib qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
    finally:
        # Har qanday holatda ham diskda ortiqcha joy egallamaslik uchun faylni o'chiramiz
        if download_result and download_result.file_path and download_result.file_path.exists():
            try:
                download_result.file_path.unlink(missing_ok=True)
                logger.info(f"Vaqtinchalik fayl tozalandi: {download_result.file_path.name}")
            except Exception as e:
                logger.warning(f"Faylni o'chirishda xatolik: {e}")


@router.message()
async def handle_other_messages(message: types.Message):
    """
    Instagram havolasi bo'lmagan boshqa har qanday xabar uchun yo'l ko'rsatuvchi handler.
    """
    await message.answer(
        "🤔 <b>Men faqat Instagram havolalarini tushunaman!</b>\n\n"
        "Menga Instagram’dagi Reels, Post yoki Video havolasini yuboring.\n"
        "<i>Misol: https://www.instagram.com/reel/C...</i>",
        parse_mode="HTML"
    )
