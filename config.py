import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklaymiz
load_dotenv()

# Asosiy bot sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Loyihaning asosiy papkasi
BASE_DIR = Path(__file__).resolve().parent

# Yuklab olingan fayllar saqlanadigan papka
DOWNLOAD_DIR_NAME = os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR = BASE_DIR / DOWNLOAD_DIR_NAME
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Telegram orqali yuborish mumkin bo'lgan maksimal hajm (50 MB)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))
