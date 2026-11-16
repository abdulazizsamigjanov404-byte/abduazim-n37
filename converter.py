import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Telegram dumaloq video (video note) cheklovlari
VIDEO_NOTE_SIZE = 640         # kvadrat tomoni (piksel)
VIDEO_NOTE_MAX_DURATION = 60  # maksimal davomiylik (soniya)


class ConversionError(Exception):
    """ffmpeg orqali videoni qayta ishlashdagi xatolik"""
    pass


def _run_ffmpeg(args: list[str], dst: Path) -> Path:
    """ffmpeg buyrug'ini bajaradi va xatolarni ConversionError ga aylantiradi."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *args, str(dst)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise ConversionError("Serverda ffmpeg o'rnatilmagan.")
    except subprocess.TimeoutExpired:
        dst.unlink(missing_ok=True)
        raise ConversionError("Videoni qayta ishlash juda uzoq davom etdi.")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg xatosi: {e.stderr}")
        dst.unlink(missing_ok=True)
        raise ConversionError("Videoni qayta ishlab bo'lmadi.")
    return dst


def _sync_to_video_note(src: Path) -> Path:
    """
    Videoni markazidan kvadrat qilib qirqadi, 640x640 ga keltiradi va
    60 soniyagacha qisqartiradi. Natija Telegram video note talablariga mos keladi.
    """
    return _run_ffmpeg([
        "-i", str(src),
        "-t", str(VIDEO_NOTE_MAX_DURATION),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", (
            "crop='min(iw,ih)':'min(iw,ih)',"
            f"scale={VIDEO_NOTE_SIZE}:{VIDEO_NOTE_SIZE},setsar=1"
        ),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
    ], src.with_name(f"{src.stem}_note.mp4"))


def _sync_extract_audio(src: Path) -> Path:
    """Videodagi musiqani (audio yo'lagini) to'liq uzunlikda MP3 qilib ajratadi."""
    return _run_ffmpeg([
        "-i", str(src),
        "-map", "0:a:0", "-vn",
        "-c:a", "libmp3lame", "-b:a", "192k",
    ], src.with_name(f"{src.stem}_audio.mp3"))


async def convert_to_video_note(src: Path) -> Path:
    """Asinxron wrapper: dumaloq videoni alohida oqimda (thread) tayyorlaydi."""
    return await asyncio.to_thread(_sync_to_video_note, src)


async def extract_audio(src: Path) -> Path:
    """Asinxron wrapper: musiqani alohida oqimda (thread) ajratadi."""
    return await asyncio.to_thread(_sync_extract_audio, src)
