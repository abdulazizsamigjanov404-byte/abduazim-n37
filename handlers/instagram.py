import logging
import uuid
from aiogram import Router, types, Bot, F
from aiogram.enums import ChatAction
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DOWNLOAD_DIR
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

# Telegram Bot API orqali bot yuklab ola oladigan maksimal fayl hajmi (20 MB)
TELEGRAM_GET_FILE_LIMIT = 20 * 1024 * 1024


def _remove_files(*paths):
    """Diskda ortiqcha joy egallamaslik uchun vaqtinchalik fayllarni o'chiradi."""
    for path in paths:
        if path and path.exists():
            try:
                path.unlink(missing_ok=True)
                logger.info(f"Vaqtinchalik fayl tozalandi: {path.name}")
            except Exception as e:
                logger.warning(f"Faylni o'chirishda xatolik: {e}")


def _video_actions_keyboard():
    """Video ostidagi "Dumaloq qilish" va "Musiqa" tugmalari."""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⭕ Dumaloq qilish", callback_data="to_note")
    keyboard.button(text="🎵 Musiqa", callback_data="to_audio")
    keyboard.adjust(2)
    return keyboard.as_markup()


@router.message(lambda message: bool(message.text and extract_instagram_url(message.text)))
async def handle_instagram_link(message: types.Message, bot: Bot):
    """
    Instagram havolasi kelganda ishga tushadigan asosiy handler.
    Videoni yuklaydi va oddiy video qilib, ostida tugmalar bilan yuboradi.
    """
    raw_text = message.text or ""
    url = extract_instagram_url(raw_text)
    if not url:
        return

    # Foydalanuvchiga jarayon boshlanganini bildirish
    status_msg = await message.answer(
        "⏳ <b>Video yuklanmoqda...</b>\n<i>Iltimos, biroz kuting.</i>",
        parse_mode="HTML"
    )

    download_result = None

    try:
        # Telegram chatida "video yuklanmoqda" holatini ko'rsatish
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)

        # Videoni asinxron yuklab olish
        download_result = await download_instagram_video(url)

        # Videoni foydalanuvchiga tugmalar bilan jo'natish
        await message.answer_video(
            video=FSInputFile(download_result.file_path),
            caption="🎬 Dumaloq video yoki musiqa kerak bo'lsa, pastdagi tugmani bosing.",
            duration=download_result.duration,
            width=download_result.width,
            height=download_result.height,
            supports_streaming=True,
            reply_markup=_video_actions_keyboard(),
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
        if download_result:
            _remove_files(download_result.file_path)


async def _download_attached_video(callback_query: types.CallbackQuery, bot: Bot):
    """
    Tugma bosilgan xabardagi videoni Telegram serveridan qayta yuklab oladi.
    Muammo bo'lsa foydalanuvchiga xabar beradi va None qaytaradi.
    """
    message = callback_query.message
    video = message.video if isinstance(message, types.Message) else None
    if not video:
        await callback_query.answer("Video topilmadi.", show_alert=True)
        return None

    if video.file_size and video.file_size > TELEGRAM_GET_FILE_LIMIT:
        await callback_query.answer(
            "Video 20 MB dan katta, Telegram botga uni qayta ishlashga ruxsat bermaydi.",
            show_alert=True,
        )
        return None

    await callback_query.answer("⏳ Tayyorlanmoqda, biroz kuting...")
    src = DOWNLOAD_DIR / f"{uuid.uuid4().hex}.mp4"
    await bot.download(video, destination=src)
    return video, src


@router.callback_query(F.data == "to_note")
async def process_to_note(callback_query: types.CallbackQuery, bot: Bot):
    """Videoni dumaloq video (video note) ko'rinishiga keltirib yuboradi."""
    src = note_path = None
    try:
        result = await _download_attached_video(callback_query, bot)
        if not result:
            return
        video, src = result
        message = callback_query.message

        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO_NOTE)
        note_path = await convert_to_video_note(src)

        await message.answer_video_note(
            video_note=FSInputFile(note_path),
            duration=min(video.duration, VIDEO_NOTE_MAX_DURATION) if video.duration else None,
            length=VIDEO_NOTE_SIZE,
        )
        if video.duration and video.duration > VIDEO_NOTE_MAX_DURATION:
            await message.answer(
                f"ℹ️ Dumaloq video {VIDEO_NOTE_MAX_DURATION} soniyadan oshmaydi, "
                f"shuning uchun faqat boshidagi {VIDEO_NOTE_MAX_DURATION} soniya olindi."
            )
    except ConversionError as e:
        await callback_query.message.answer(f"⚠️ Dumaloq videoga o'tkazib bo'lmadi: {e}")
    except Exception as e:
        logger.exception(f"Dumaloq video tayyorlashda xatolik: {e}")
        await callback_query.message.answer("❌ Dumaloq video tayyorlashda xatolik yuz berdi.")
    finally:
        _remove_files(src, note_path)


@router.callback_query(F.data == "to_audio")
async def process_to_audio(callback_query: types.CallbackQuery, bot: Bot):
    """Videodagi musiqani MP3 qilib yuboradi."""
    src = audio_path = None
    try:
        result = await _download_attached_video(callback_query, bot)
        if not result:
            return
        video, src = result
        message = callback_query.message

        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
        audio_path = await extract_audio(src)

        await message.answer_audio(
            audio=FSInputFile(audio_path, filename="instagram_music.mp3"),
            title="Instagram Reels musiqasi",
            duration=video.duration,
        )
    except ConversionError:
        await callback_query.message.answer("🔇 Bu videoda musiqa (ovoz) topilmadi.")
    except Exception as e:
        logger.exception(f"Musiqani ajratishda xatolik: {e}")
        await callback_query.message.answer("❌ Musiqani ajratishda xatolik yuz berdi.")
    finally:
        _remove_files(src, audio_path)


@router.message()
async def handle_other_messages(message: types.Message):
    """Instagram havolasi bo'lmagan xabarlarga yo'riqnoma bilan javob beradi."""
    await message.answer(
        "📎 Menga Instagram Reels havolasini yuboring — videoni yuklab beraman."
    )
