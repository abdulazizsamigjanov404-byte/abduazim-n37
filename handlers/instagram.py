import html
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
from music import recognize_song, download_full_song

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
        # Asl havola caption'da link sifatida turadi: video 20 MB dan katta bo'lsa,
        # tugma bosilganda bot uni Telegram'dan emas, shu havola orqali qayta yuklaydi.
        await message.answer_video(
            video=FSInputFile(download_result.file_path),
            caption=(
                "🎬 Dumaloq video yoki musiqa kerak bo'lsa, pastdagi tugmani bosing.\n"
                f'<a href="{html.escape(url, quote=True)}">🔗 Instagram</a>'
            ),
            parse_mode="HTML",
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


def _source_url(message: types.Message):
    """Video caption'idagi asl Instagram havolasini qaytaradi."""
    for entity in message.caption_entities or []:
        if entity.type == "text_link" and entity.url and extract_instagram_url(entity.url):
            return entity.url
    return None


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
        # Telegram botlarga 20 MB dan katta faylni yuklab olishga ruxsat bermaydi,
        # shuning uchun videoni caption'dagi asl havola orqali Instagram'dan qayta yuklaymiz.
        source_url = _source_url(message)
        if not source_url:
            await callback_query.answer(
                "Video 20 MB dan katta. Instagram havolasini qaytadan yuboring, keyin tugmani bosing.",
                show_alert=True,
            )
            return None
        await callback_query.answer("⏳ Tayyorlanmoqda, biroz kuting...")
        try:
            result = await download_instagram_video(source_url)
        except (DownloadError, VideoTooLargeError) as e:
            await message.answer(f"⚠️ Videoni qayta yuklab bo'lmadi: {html.escape(str(e), quote=False)}", parse_mode="HTML")
            return None
        return video, result.file_path

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
    """
    Videodagi qo'shiqni aniqlab, uning to'liq versiyasini MP3 qilib yuboradi.
    Qo'shiq aniqlanmasa yoki topilmasa, videoning o'z ovozini yuboradi.
    """
    src = audio_path = song_path = status_msg = None
    try:
        result = await _download_attached_video(callback_query, bot)
        if not result:
            return
        video, src = result
        message = callback_query.message

        # Jarayon bir necha o'n soniya olishi mumkin, foydalanuvchiga bosqichlarni ko'rsatamiz
        status_msg = await message.answer("🔍 Qo'shiq aniqlanmoqda...")
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
        audio_path = await extract_audio(src)

        song = await recognize_song(audio_path)
        if song:
            try:
                await status_msg.edit_text(
                    f"🎵 Topildi: <b>{html.escape(song.artist)} — {html.escape(song.title)}</b>\n"
                    "⏳ To'liq versiyasi yuklanmoqda...",
                    parse_mode="HTML",
                )
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
                song_path = await download_full_song(song)
                await message.answer_audio(
                    audio=FSInputFile(song_path, filename=f"{song.artist} - {song.title}.mp3"),
                    title=song.title,
                    performer=song.artist or None,
                )
                return
            except Exception as e:
                logger.warning(f"To'liq qo'shiqni yuklab bo'lmadi: {e}")
                note = (
                    f"🎵 Qo'shiq: <b>{html.escape(song.artist)} — {html.escape(song.title)}</b>\n"
                    "To'liq versiyasini yuklab bo'lmadi, videodagi ovozni yubordim."
                )
        else:
            note = "🔍 Qo'shiqni aniqlab bo'lmadi, videodagi ovozni yubordim."

        await message.answer(note, parse_mode="HTML")
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
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass
        _remove_files(src, audio_path, song_path)


@router.message()
async def handle_other_messages(message: types.Message):
    """Instagram havolasi bo'lmagan xabarlarga yo'riqnoma bilan javob beradi."""
    await message.answer(
        "📎 Menga Instagram Reels havolasini yuboring — videoni yuklab beraman."
    )
