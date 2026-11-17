import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yt_dlp

from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

# To'liq qo'shiq qidiriladigan manba. YouTube Render kabi bulut serverlarini
# bloklaydi va har urinish vaqtni behuda oladi, shuning uchun faqat SoundCloud.
SEARCH_SOURCE = "scsearch3:"

# 60 soniyadan qisqa natijalar odatda pullik qo'shiqlarning 30 soniyalik parchasi,
# 15 daqiqadan uzunlari esa mikslar yoki jonli efirlar (soniya)
MIN_SONG_DURATION = 60
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
        # Tayyor MP3 bo'lsa uni olamiz: kuchsiz serverda qayta kodlash sekin
        "format": "bestaudio[ext=mp3]/bestaudio/best",
        "noplaylist": True,
        "max_downloads": 1,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "match_filter": yt_dlp.utils.match_filter_func(
            f"duration > {MIN_SONG_DURATION} & duration < {MAX_SONG_DURATION}"
        ),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(f"{SEARCH_SOURCE}{query}", download=True)
    except yt_dlp.utils.MaxDownloadsReached:
        # Birinchi mos qo'shiq yuklangach qidiruv shu xato bilan to'xtaydi
        pass
    except Exception as e:
        logger.warning(f"Qo'shiqni yuklab bo'lmadi: {e}")

    matches = list(DOWNLOAD_DIR.glob(f"{task_id}_song*.mp3"))
    if matches:
        return matches[0]

    for leftover in DOWNLOAD_DIR.glob(f"{task_id}_song*"):
        leftover.unlink(missing_ok=True)
    raise RuntimeError(f"To'liq qo'shiq topilmadi: {query}")


async def download_full_song(song: SongInfo) -> Path:
    """Asinxron wrapper: to'liq qo'shiqni alohida oqimda (thread) yuklaydi."""
    return await asyncio.to_thread(_sync_download_song, song)
