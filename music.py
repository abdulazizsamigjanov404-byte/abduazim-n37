import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yt_dlp

from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

# To'liq qo'shiq qidiriladigan manbalar (birinchisi ishlamasa keyingisi sinaladi)
SEARCH_SOURCES = ["ytsearch1:", "scsearch1:"]

# Juda uzun natijalarni (mikslar, jonli efirlar) o'tkazib yuborish uchun (soniya)
MAX_SONG_DURATION = 15 * 60


@dataclass
class SongInfo:
    """Aniqlangan qo'shiq ma'lumotlari"""
    title: str
    artist: str


async def recognize_song(audio_path: Path) -> Optional[SongInfo]:
    """
    Shazam orqali audio parchadan qo'shiq nomi va ijrochisini aniqlaydi.
    Aniqlanmasa yoki xizmat ishlamasa None qaytaradi.
    """
    try:
        from shazamio import Shazam

        shazam = Shazam()
        recognize = getattr(shazam, "recognize", None) or shazam.recognize_song
        result = await recognize(str(audio_path))
    except Exception as e:
        logger.warning(f"Qo'shiqni aniqlashda xatolik: {e}")
        return None

    track = (result or {}).get("track") or {}
    title = track.get("title")
    artist = track.get("subtitle")
    if not title:
        return None
    return SongInfo(title=title, artist=artist or "")


def _sync_download_song(song: SongInfo) -> Path:
    """yt-dlp orqali qo'shiqning to'liq versiyasini qidirib MP3 qilib yuklaydi."""
    task_id = uuid.uuid4().hex
    query = f"{song.artist} - {song.title}".strip(" -")

    ydl_opts = {
        "outtmpl": str(DOWNLOAD_DIR / f"{task_id}_song.%(ext)s"),
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration < {MAX_SONG_DURATION}"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    last_error = None
    for source in SEARCH_SOURCES:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(f"{source}{query}", download=True)
            matches = list(DOWNLOAD_DIR.glob(f"{task_id}_song*.mp3"))
            if matches:
                return matches[0]
        except Exception as e:
            last_error = e
            logger.warning(f"{source} orqali qo'shiqni yuklab bo'lmadi: {e}")
        # Keyingi manbaga o'tishdan oldin chala fayllarni tozalaymiz
        for leftover in DOWNLOAD_DIR.glob(f"{task_id}_song*"):
            leftover.unlink(missing_ok=True)

    raise RuntimeError(f"Qo'shiq hech bir manbadan topilmadi: {last_error}")


async def download_full_song(song: SongInfo) -> Path:
    """Asinxron wrapper: to'liq qo'shiqni alohida oqimda (thread) yuklaydi."""
    return await asyncio.to_thread(_sync_download_song, song)
