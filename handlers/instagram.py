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
from ai_service import ask_gemini_ai

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
async def handle_ai_chat(message: types.Message, bot: Bot):
    """
    Instagram havolasi bo'lmagan barcha matnli xabarlarni
    aqlli AI suhbatchiga yo'naltiruvchi handler.
    """
    user_text = message.text
    if not user_text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    # Telegramda "yozmoqda..." harakatini ko'rsatish
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Gemini AI dan javob olish
    reply = await ask_gemini_ai(user_id=user_id, user_message=user_text)

    # Agar javob 4000 belgidan uzun bo'lsa, qismlarga bo'lib yuboramiz
    MAX_LENGTH = 4000
    if len(reply) <= MAX_LENGTH:
        try:
            await message.answer(reply, parse_mode="Markdown")
        except Exception:
            await message.answer(reply)
    else:
        for i in range(0, len(reply), MAX_LENGTH):
            chunk = reply[i:i + MAX_LENGTH]
            try:
                await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                await message.answer(chunk)
