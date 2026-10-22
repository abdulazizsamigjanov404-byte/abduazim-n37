import logging
from collections import defaultdict
from typing import Dict, List
import aiohttp

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Foydalanuvchilarning suhbat tarixini xotirada saqlash (chat memory)
# user_id -> [{'role': 'user'|'model', 'parts': [{'text': '...'}]}]
user_histories: Dict[int, List[dict]] = defaultdict(list)
MAX_HISTORY_MESSAGES = 10

# Birlamchi va ehtiyot modellari ro'yxati (biri band bo'lsa, keyingisi ishlaydi)
GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]

SYSTEM_PROMPT = (
    "Sen 'InstaDownload' Telegram botining aqlli, xushmuomala va do'stona AI suhbatchisisan. "
    "Foydalanuvchilar bilan ular qaysi tilda murojaat qilsa (o'zbek, rus, ingliz va h.k.), "
    "o'sha tilda samimiy, aniq va tushunarli javob ber. "
    "Kerak bo'lganda Telegram uchun mos chiroyli emojilar va formatlardan foydalan. "
    "Botingiz shuningdek Instagramdan (Reels, Post, IGTV) sifatli video yuklab bera olishini ham bilasan."
)


def clear_user_history(user_id: int):
    """Foydalanuvchi suhbat tarixini tozalash"""
    if user_id in user_histories:
        user_histories[user_id].clear()


async def ask_gemini_ai(user_id: int, user_message: str) -> str:
    """
    Google Gemini AI API orqali foydalanuvchi xabariga javob olish.
    Kontekstni (suhbat tarixini) saqlab boradi va bir nechta modellar zaxirasiga ega.
    """
    if not GEMINI_API_KEY:
        return "Kechirasiz, hozirda AI xizmati ulanmagan. Iltimos, keyinroq urinib ko'ring."

    # Foydalanuvchi tarixini olamiz
    history = user_histories[user_id]

    # Yangi xabarni tarixga qo'shamiz
    history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # Xotira hajmini cheklash (oxirgi N ta xabar)
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]
        user_histories[user_id] = history

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": history,
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 2048,
        }
    }

    timeout = aiohttp.ClientTimeout(total=25)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            reply_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if reply_text:
                                # AI javobini ham tarixga saqlaymiz
                                history.append({
                                    "role": "model",
                                    "parts": [{"text": reply_text}]
                                })
                                return reply_text.strip()
                    elif response.status in (404, 503, 429):
                        logger.warning(f"Model {model} vaqtincha javob bermadi (status: {response.status}), keyingi model sinab ko'riladi.")
                        continue
                    else:
                        error_body = await response.text()
                        logger.error(f"Gemini API xatoligi ({model}): {response.status} - {error_body}")
            except Exception as e:
                logger.warning(f"Model {model} bilan ulanishda xatolik: {e}")
                continue

    # Agar barcha modellar band bo'lsa
    # Tarixdagi oxirgi xabarni o'chiramiz, chunki javob olinmadi
    if history and history[-1]["role"] == "user":
        history.pop()

    return (
        "Hozirda AI serverida yuklama yuqori bo'lgani sababli javob bera olmadim. "
        "Iltimos, birozdan so'ng qayta yozib ko'ring! 🤖"
    )
