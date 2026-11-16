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
from converter import (
    convert_to_video_note,
    extract_audio,
    ConversionError,
    VIDEO_NOTE_SIZE,
    VIDEO_NOTE_MAX_DURATION,
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(lambda message: bool(message.text and extract_instagram_url(message.text)))
async def handle_instagram_link(message: types.Message, bot: Bot):
    """
    Instagram havolasi kelganda ishga tushadigan asosiy handler.
    Videoni yuklaydi, dumaloq video va alohida MP3 musiqa qilib yuboradi.
    """
    raw_text = message.text or ""
    url = extract_instagram_url(raw_text)
    if not url:
        return

    # Foydalanuvchiga jarayon boshlanganini bildirish
    status_msg = await message.answer(
        "⏳ <b>Video yuklanmoqda va dumaloq ko'rinishga keltirilmoqda...</b>\n<i>Iltimos, biroz kuting.</i>",
        parse_mode="HTML"
    )

    download_result = None
    note_path = None
    audio_path = None

    try:
        # Telegram chatida "dumaloq video yuklanmoqda" holatini ko'rsatish
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO_NOTE)

        # Videoni asinxron yuklab olish
        download_result = await download_instagram_video(url)

        # Videoni kvadrat 640x640 va 60 soniyagacha bo'lgan dumaloq video formatiga o'tkazish
        note_path = await convert_to_video_note(download_result.file_path)

        duration = download_result.duration
        if duration:
            duration = min(duration, VIDEO_NOTE_MAX_DURATION)

        # Dumaloq videoni foydalanuvchiga jo'natish
        await message.answer_video_note(
            video_note=FSInputFile(note_path),
            duration=duration,
            length=VIDEO_NOTE_SIZE,
        )

        if download_result.duration and download_result.duration > VIDEO_NOTE_MAX_DURATION:
            await message.answer(
                f"ℹ️ Video {download_result.duration} soniya edi. Dumaloq video "
                f"{VIDEO_NOTE_MAX_DURATION} soniyadan oshmaydi, shuning uchun faqat boshidagi "
                f"{VIDEO_NOTE_MAX_DURATION} soniya olindi. Musiqa to'liq yuboriladi."
            )

        # Reels musiqasini alohida MP3 qilib yuborish (videoda ovoz bo'lmasa o'tkazib yuboriladi)
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
            audio_path = await extract_audio(download_result.file_path)
            await message.answer_audio(
                audio=FSInputFile(audio_path, filename="instagram_music.mp3"),
                title="Instagram Reels musiqasi",
                duration=download_result.duration,
            )
        except ConversionError:
            await message.answer("🔇 Bu videoda musiqa (ovoz) topilmadi.")

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
    except ConversionError as e:
        await status_msg.edit_text(
            f"⚠️ <b>Dumaloq videoga o'tkazib bo'lmadi:</b>\n{str(e)}",
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
        # Har qanday holatda ham diskda ortiqcha joy egallamaslik uchun fayllarni o'chiramiz
        paths = [note_path, audio_path]
        if download_result:
            paths.append(download_result.file_path)
        for path in paths:
            if path and path.exists():
                try:
                    path.unlink(missing_ok=True)
                    logger.info(f"Vaqtinchalik fayl tozalandi: {path.name}")
                except Exception as e:
                    logger.warning(f"Faylni o'chirishda xatolik: {e}")


@router.message()
async def handle_other_messages(message: types.Message):
    """Instagram havolasi bo'lmagan xabarlarga yo'riqnoma bilan javob beradi."""
    await message.answer(
        "📎 Menga Instagram Reels havolasini yuboring — uni dumaloq video va MP3 musiqa qilib qaytaraman."
    )
