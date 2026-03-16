# 🕌 Nur Al-Quran — Telegram Quran Bot

> *بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ*

A beautiful, fully-featured Quran Telegram bot with a delicate Islamic aesthetic.
Search any Surah by name or number, read with translation, and listen to 50+ Qari voices.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📖 **Read Surah** | Full Arabic text + English translation, paginated |
| 🎧 **Audio** | 50+ Qaris from EveryAyah.com CDN (free) |
| 📥 **Download PDF** | Links to Quran.com & GlobalQuran |
| 🔍 **Smart Search** | Search by number (`18`), name (`Al-Kahf`), partial (`kahf`) |
| 🎲 **Random Surah** | Discover a new Surah each time |
| 📚 **Browse All 114** | Paginated list of all Surahs |
| ℹ️ **Surah Info** | Revelation type, ayah count, special notes |
| 🔤 **Transliteration** | External link to romanized text |

---

## 🚀 Quick Start

### 1. Get a Bot Token
1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Follow prompts, copy your token

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Token
```bash
# Linux / macOS
export TELEGRAM_TOKEN="your_token_here"

# Windows
set TELEGRAM_TOKEN=your_token_here

# Or edit bot.py line 53 directly:
# TOKEN = "your_token_here"
```

### 4. Run
```bash
python quran_bot.py
```

---

## ☁️ Deploy on Koyeb (Free)

1. Push to GitHub
2. Go to [koyeb.com](https://koyeb.com) → New App → GitHub
3. Set environment variable: `TELEGRAM_TOKEN = your_token`
4. Run command: `python quran_bot.py`
5. Done!

---

## 🎙️ Qari List (50+ Voices)

The bot includes voices from:

| Region | Reciters |
|---|---|
| 🇸🇦 Saudi Arabia | Mishary Al-Afasy, Maher Al-Muaiqly, Al-Sudais, Saud Al-Shuraim, Yasser Al-Dossary, and 15+ more |
| 🇪🇬 Egypt | Abdul Basit (Murattal & Mujawwad), Minshawi, Husary, Mustafa Ismail |
| 🇰🇼 Kuwait | Nasser Al-Qatami |
| 🇩🇿 Algeria | Fares Abbad |
| 🇴🇲 Oman | Obaid Alrawahi |
| 🇿🇦 South Africa | Ziyaad Patel |
| 🇦🇪 UAE | Khalifa Al-Taniji |
| 🇮🇷 Iran | Parhizgar |
| 🇲🇦 Morocco | Warsh (Madinah riwayah) |

All audio from [everyayah.com](https://everyayah.com) — free, no API key needed.

---

## 📡 APIs Used (All Free, No Keys Needed)

| API | Usage |
|---|---|
| [api.quran.com/api/v4](https://api.quran.com/api/v4) | Arabic text + English translations |
| [everyayah.com](https://everyayah.com) | MP3 audio files for all Qaris |

---

## 💬 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome screen with quick access |
| `/list` | Browse all 114 Surahs |
| `/search <query>` | Search by name or number |
| `/random` | Random Surah |
| `/juz` | Juz guide |
| `/help` | Help & commands |
| Just type! | e.g. `Yaseen`, `18`, `Al-Mulk` |

---

## 🌿 Notes

- Audio is streamed directly from EveryAyah CDN — no local storage needed
- Translation used: Sahih International (ID 131) via Quran.com API
- Surah 9 (At-Tawbah) has no Bismillah — handled correctly
- Telegram message limit (4096 chars) handled via pagination

---

*May Allah accept this effort and make it beneficial for all Muslims.* 🤍

*اللَّهُمَّ اجْعَلْنَا مِنْ أَهْلِ الْقُرْآنِ*
