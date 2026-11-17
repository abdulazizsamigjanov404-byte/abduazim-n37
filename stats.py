"""
Foydalanuvchilar statistikasi.

Render bepul tarifida disk har deploy'da tozalanadi, shuning uchun statistika
Telegram'ning o'zida saqlanadi: bot ma'lumotni JSON fayl qilib adminga yuboradi,
xabarni pin qiladi va keyin o'sha xabardagi faylni yangilab boradi.
Bot qayta ishga tushganda pin qilingan fayldan ma'lumotni qayta o'qiydi.
"""

import asyncio
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import BufferedInputFile, InputMediaDocument, TelegramObject, Update

from config import ADMIN_ID

logger = logging.getLogger("InstagramBot.stats")

TZ = timezone(timedelta(hours=5))  # O'zbekiston vaqti
STATS_FILENAME = "bot_stats.json"
SAVE_INTERVAL = 300  # har 5 daqiqada (o'zgarish bo'lsa) saqlanadi


def _now() -> datetime:
    return datetime.now(TZ)


class Stats:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = self._empty()
        self.dirty = False
        self.message_id: int | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _empty() -> Dict[str, Any]:
        # users: {user_id: {"name", "username", "first", "last"}}
        # months: {"2026-11": {"users": [ids], "new": n, "requests": n}}
        # days: {"2026-11-18": {"users": [ids], "requests": n}}  (oxirgi 31 kun)
        return {"version": 1, "users": {}, "months": {}, "days": {}}

    # ------------------------------------------------------------- hisoblash

    def track(self, user) -> None:
        if not user or user.is_bot:
            return
        now = _now()
        uid = str(user.id)
        month, day = now.strftime("%Y-%m"), now.strftime("%Y-%m-%d")
        users = self.data["users"]
        m = self.data["months"].setdefault(month, {"users": [], "new": 0, "requests": 0})
        d = self.data["days"].setdefault(day, {"users": [], "requests": 0})

        if uid not in users:
            users[uid] = {"first": day}
            m["new"] += 1
        u = users[uid]
        u["name"] = (user.full_name or "")[:64]
        u["username"] = user.username or ""
        u["last"] = day

        if uid not in m["users"]:
            m["users"].append(uid)
        if uid not in d["users"]:
            d["users"].append(uid)
        m["requests"] += 1
        d["requests"] += 1

        # 31 kundan eski kunlik ma'lumotlarni o'chiramiz
        if len(self.data["days"]) > 31:
            for key in sorted(self.data["days"])[:-31]:
                del self.data["days"][key]
        self.dirty = True

    def report(self) -> str:
        now = _now()
        month, day = now.strftime("%Y-%m"), now.strftime("%Y-%m-%d")
        months = self.data["months"]
        days = self.data["days"]
        cur = months.get(month, {"users": [], "new": 0, "requests": 0})
        today = days.get(day, {"users": [], "requests": 0})

        week_users: set[str] = set()
        for i in range(7):
            key = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            week_users.update(days.get(key, {}).get("users", []))

        lines = [
            "📊 <b>Admin panel — statistika</b>",
            "",
            f"👥 Jami foydalanuvchilar: <b>{len(self.data['users'])}</b>",
            "",
            f"📅 <b>Shu oy ({month})</b>",
            f"• Faol foydalanuvchilar: <b>{len(cur['users'])}</b>",
            f"• Yangi foydalanuvchilar: <b>{cur['new']}</b>",
            f"• So'rovlar: <b>{cur['requests']}</b>",
            "",
            f"🗓 Oxirgi 7 kun: <b>{len(week_users)}</b> foydalanuvchi",
            f"☀️ Bugun: <b>{len(today['users'])}</b> foydalanuvchi, <b>{today['requests']}</b> so'rov",
        ]

        history = sorted(months)[-6:]
        if history:
            lines += ["", "📈 <b>Oylar bo'yicha</b> (faol / yangi / so'rov)"]
            for key in reversed(history):
                m = months[key]
                lines.append(f"<code>{key}</code>  {len(m['users'])} / {m['new']} / {m['requests']}")

        lines += ["", f"<i>Yangilandi: {now.strftime('%d.%m.%Y %H:%M')}</i>"]
        return "\n".join(lines)

    # ---------------------------------------------------- Telegram'da saqlash

    async def load(self, bot: Bot) -> None:
        """Admin chatidagi pin qilingan fayldan statistikani o'qiydi."""
        if not ADMIN_ID:
            logger.warning("ADMIN_ID sozlanmagan: statistika saqlanmaydi")
            return
        try:
            chat = await bot.get_chat(ADMIN_ID)
            pinned = chat.pinned_message
            if not (pinned and pinned.document and pinned.document.file_name == STATS_FILENAME):
                logger.info("Pin qilingan statistika fayli topilmadi, yangidan boshlanadi")
                return
            buf = io.BytesIO()
            await bot.download(pinned.document, destination=buf)
            loaded = json.loads(buf.getvalue().decode("utf-8"))
            async with self._lock:
                self.data = loaded
                self.message_id = pinned.message_id
            logger.info(f"Statistika yuklandi: {len(self.data['users'])} foydalanuvchi")
        except Exception as e:
            logger.warning(f"Statistikani yuklab bo'lmadi: {e}")

    async def save(self, bot: Bot, force: bool = False) -> None:
        if not ADMIN_ID or (not self.dirty and not force):
            return
        async with self._lock:
            payload = json.dumps(self.data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.dirty = False
        file = BufferedInputFile(payload, filename=STATS_FILENAME)
        caption = "🗄 Bot statistikasi (bu xabarni o'chirmang va pindan olmang)"
        try:
            if self.message_id:
                try:
                    await bot.edit_message_media(
                        chat_id=ADMIN_ID,
                        message_id=self.message_id,
                        media=InputMediaDocument(media=file, caption=caption),
                    )
                    return
                except Exception as e:
                    if "not modified" in str(e).lower():
                        return
                    logger.warning(f"Statistika xabarini yangilab bo'lmadi, yangisi yuboriladi: {e}")
            msg = await bot.send_document(ADMIN_ID, file, caption=caption, disable_notification=True)
            await bot.pin_chat_message(ADMIN_ID, msg.message_id, disable_notification=True)
            self.message_id = msg.message_id
        except Exception as e:
            self.dirty = True
            logger.warning(f"Statistikani saqlab bo'lmadi: {e}")

    async def autosave(self, bot: Bot) -> None:
        while True:
            await asyncio.sleep(SAVE_INTERVAL)
            await self.save(bot)


stats = Stats()


class StatsMiddleware(BaseMiddleware):
    """Har bir xabar va tugma bosilishida foydalanuvchini hisobga oladi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            if isinstance(event, Update):
                obj = event.message or event.callback_query
                if obj is not None:
                    stats.track(obj.from_user)
        except Exception as e:
            logger.warning(f"Statistika xatosi: {e}")
        return await handler(event, data)
