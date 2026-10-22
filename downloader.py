import asyncio
import os
import re
import uuid
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yt_dlp

from config import DOWNLOAD_DIR, MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# Instagram havolalarini aniqlash uchun regex shabloni
INSTAGRAM_URL_PATTERN = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv|share)/[a-zA-Z0-9_\-]+/?(?:\?[^\s]+)?)"
    r"|(https?://(?:www\.)?instagr\.am/(?:p|reel|reels|tv|share)/[a-zA-Z0-9_\-]+/?(?:\?[^\s]+)?)"
)


@dataclass
class DownloadResult:
    """Yuklab olingan video ma'lumotlari modeli"""
    file_path: Path
    title: Optional[str]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    filesize: int


class DownloadError(Exception):
    """Yuklab olish jarayonidagi umumiy xatolik"""
    pass


class VideoTooLargeError(Exception):
    """Video hajmi Telegram limiti (50MB) dan oshgandagi xatolik"""
    pass


def extract_instagram_url(text: str) -> Optional[str]:
    """
    Xabar matnidan Instagram havolasini ajratib oladi.
    Foydalanuvchi havola bilan birga boshqa matn yozgan bo'lsa ham ishlaydi.
    """
    match = INSTAGRAM_URL_PATTERN.search(text)
    if match:
        # Match guruhlaridan birinchisini qaytaramiz
        url = match.group(1) or match.group(2)
        # URL oxiridagi keraksiz tracking parametrlarni tozalash (masalan, ?igsh=...)
        clean_url = url.split("?")[0].rstrip("/") + "/"
        return clean_url
    return None


def _sync_download(url: str, task_id: str) -> DownloadResult:
    """
    Sinxron ravishda yt-dlp orqali Instagram videosini yuklab olish.
    Bu funksiya asyncio.to_thread orqali alohida oqimda chaqiriladi.
    """
    output_template = str(DOWNLOAD_DIR / f"{task_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video haqidagi ma'lumotlarni olish va yuklab olish
            info_dict = ydl.extract_info(url, download=True)

            if not info_dict:
                raise DownloadError("Video haqida ma'lumot olib bo'lmadi.")

            # Haqiqiy yuklangan fayl yo'lini aniqlash
            expected_filepath = ydl.prepare_filename(info_dict)
            file_path = Path(expected_filepath)

            # Agar kengaytma mp4 ga o'zgargan bo'lsa tekshiramiz
            if not file_path.exists():
                mp4_variant = file_path.with_suffix(".mp4")
                if mp4_variant.exists():
                    file_path = mp4_variant
                else:
                    # Boshqa fayllarni qidiramiz
                    matching_files = list(DOWNLOAD_DIR.glob(f"{task_id}.*"))
                    if matching_files:
                        file_path = matching_files[0]
                    else:
                        raise DownloadError("Yuklangan video fayli topilmadi.")

            file_size = file_path.stat().st_size

            # Telegram Bot API 50MB limitini tekshirish
            if file_size > MAX_FILE_SIZE:
                # Faylni o'chirib, xatolik beramiz
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                raise VideoTooLargeError(
                    f"Video hajmi {file_size / (1024 * 1024):.1f} MB. "
                    f"Telegram bot faqat 50 MB gacha bo'lgan videolarni jo'nata oladi."
                )

            # Metadata
            title = info_dict.get("title") or info_dict.get("description")
            if title and len(title) > 300:
                title = title[:297] + "..."

            duration = info_dict.get("duration")
            width = info_dict.get("width")
            height = info_dict.get("height")

            return DownloadResult(
                file_path=file_path,
                title=title,
                duration=int(duration) if duration else None,
                width=int(width) if width else None,
                height=int(height) if height else None,
                filesize=file_size,
            )

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise DownloadError("Bu profil yopiq (private). Bot faqat ochiq profillardagi videolarni yuklay oladi.")
        elif "login" in error_msg or "checkpoint" in error_msg:
            raise DownloadError("Instagram bu videoga kirishni cheklagan yoki avtorizatsiya talab qilmoqda.")
        elif "not found" in error_msg or "404" in error_msg:
            raise DownloadError("Ushbu video topilmadi yoki o'chirib yuborilgan.")
        else:
            logger.error(f"yt-dlp xatosi: {e}")
            raise DownloadError("Instagramdan videoni yuklab olishda xatolik yuz berdi.")
    except VideoTooLargeError:
        raise
    except Exception as e:
        logger.exception(f"Kutilmagan xatolik: {e}")
        raise DownloadError(f"Yuklashda xatolik yuz berdi: {str(e)}")


async def download_instagram_video(url: str) -> DownloadResult:
    """
    Asinxron wrapper: yt-dlp yuklashni botning asosiy oqimini
    to'sib qo'ymasdan alohida oqimda (thread) bajaradi.
    """
    task_id = uuid.uuid4().hex
    return await asyncio.to_thread(_sync_download, url, task_id)
