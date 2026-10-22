# 🎬 Instagram Video Downloader Telegram Bot

Zamonaviy va professional arxitekturada yaratilgan Telegram boti. Instagram'dagi **Reels**, **Post**, **Video** va **IGTV** havolalarini qabul qilib, ularni to'g'ridan-to'g'ri foydalanuvchiga tayyor video (`.mp4`) holatida yuklab beradi.

---

## ✨ Imkoniyatlari va Afzalliklari

- ⚡️ **Asinxron va Tezkor**: `aiogram 3.x` va `asyncio.to_thread` orqali to'liq asinxron ishlaydi, bot bir nechta foydalanuvchiga bir vaqtning o'zida parallel xizmat ko'rsata oladi.
- 🎯 **Keng qamrovli yuklash**: `yt-dlp` kutubxonasi yordamida Reels, Post, IGTV hamda qisqa ulashish havolalari (`/share/`, `/reel/`, `/p/`) bilan mukammal ishlaydi.
- 🧹 **Avtomatik Disk Tozalash**: Video yuborilgach yoki xatolik yuz berganda serverdagi vaqtinchalik video fayl avtomatik o'chiriladi. Diskda keraksiz fayllar to'planib qolmaydi.
- 🛡 **Xatoliklar nazorati**: Yopiq profillar, o'chirilgan videolar va Telegram'ning 50MB hajmiy cheklovlarini tushunarli xabarlar bilan foydalanuvchiga yetkazadi.
- 💬 **Jonli holat**: Foydalanuvchiga yuklash jarayoni (`⏳ Video qidirilmoqda...`) va chatda `upload_video` harakati ko'rsatiladi.

---

## 📁 Loyiha Tuzilishi

```text
installerbot/
├── config.py              # Konfiguratsiya va sozlamalar
├── downloader.py          # Instagram videolarini yuklab oluvchi asinxron modul
├── main.py                # Botni ishga tushiruvchi asosiy fayl
├── requirements.txt       # Kerakli Python kutubxonalari
├── .env.example           # Sozlamalar namunasi
├── .env                   # Bot tokeni va maxfiy ma'lumotlar (o'zingiz to'ldirasiz)
├── .gitignore             # Git uchun e'tibordan chetda qoldiriladigan fayllar
└── handlers/              # Telegram buyruqlari va xabarlarni qayta ishlovchi modullar
    ├── __init__.py        # Routerlarni birlashtiruvchi modul
    ├── start.py           # /start va /help buyruqlari
    └── instagram.py       # Instagram havolalarini qayta ishlash va video jo'natish
```

---

## 🚀 O'rnatish va Ishga Tushirish

### 1-qadam: Python o'rnatilganligini tekshirish
Kompyuteringizda **Python 3.10 yoki undan yuqori** versiya o'rnatilgan bo'lishi kerak.
```bash
python --version
```

### 2-qadam: Telegram Bot Tokenini olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring.
3. Bot nomini va unikal `username`ini kiriting (masalan, `my_insta_downloader_bot`).
4. Sizga berilgan `API Token`ni nusxalab oling.

### 3-qadam: Virtual muhit (Virtual Environment) yaratish va faollashtirish
Loyihaning asosiy papkasida quyidagi buyruqlarni bajaring:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4-qadam: Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

> **Tavsiya (FFmpeg):** Videolarni eng yuqori sifatda birlashtirish uchun tizimda `ffmpeg` o'rnatilgan bo'lishi maqsadga muvofiq (Windows: `winget install Gyan.FFmpeg`, Ubuntu/Debian: `sudo apt install ffmpeg`).

### 5-qadam: `.env` faylini sozlash
Loyihadagi `.env` faylini oching va `BOT_TOKEN` qismiga o'z botingiz tokenini yozing:

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### 6-qadam: Botni ishga tushirish
```bash
python main.py
```

Barcha sozlamalar to'g'ri bo'lsa, terminalda quyidagi yozuv paydo bo'ladi:
```text
INFO | InstagramBot : Bot muvaffaqiyatli ishga tushdi: @SizningBotingiz (Instagram Video Downloader)
INFO | InstagramBot : Xabarlarni qabul qilish boshlandi (Polling)...
```

Endi Telegram'ga o'tib botingizga `/start` buyrug'ini bosing va istalgan Instagram video havolasini yuboring! 🎉

---

## 🌐 Serverda (VPS/Ubuntu) doimiy (24/7) yurgizish (Systemd)

Agar botni Linux serverda doimiy uzilishlarsiz ishlatmoqchi bo'lsangiz, `systemd` xizmatini yaratishingiz mumkin:

1. Fayl oching:
```bash
sudo nano /etc/systemd/system/instabot.service
```

2. Quyidagi konfiguratsiyani kiriting:
```ini
[Unit]
Description=Instagram Video Downloader Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/installerbot
ExecStart=/path/to/installerbot/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Xizmatni ishga tushiring:
```bash
sudo systemctl daemon-reload
sudo systemctl enable instabot
sudo systemctl start instabot
```
