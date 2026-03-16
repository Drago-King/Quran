"""
╔══════════════════════════════════════════════════════════════╗
║          🕌 NUR AL-QURAN BOT — Telegram Quran Bot            ║
║     Beautiful • Delicate • Complete Islamic Experience        ║
╚══════════════════════════════════════════════════════════════╝

APIs Used (ALL FREE, NO KEY NEEDED):
  - Quran API: https://api.quran.com/api/v4
  - Audio:     https://everyayah.com  (100+ Qaris)
  - MP3Quran:  https://mp3quran.net/api
  - PDF:       https://quran.com downloads

Setup:
  pip install python-telegram-bot==21.6 aiohttp aiofiles

Set your token:
  export TELEGRAM_TOKEN="your_bot_token_here"
"""

import os
import re
import json
import asyncio
import aiohttp
import aiofiles
import tempfile
import logging
from pathlib import Path
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)
from telegram.constants import ParseMode, ChatAction

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ─────────────────────────────────────────────
#  USER PREFERENCES (in-memory, resets on restart)
# ─────────────────────────────────────────────
# Stores per-user script choice: "uthmani" or "indopak"
USER_SCRIPT: dict[int, str] = {}

def get_script(user_id: int) -> str:
    return USER_SCRIPT.get(user_id, "uthmani")

def set_script(user_id: int, script: str):
    USER_SCRIPT[user_id] = script

def script_field(user_id: int) -> str:
    """Return the API field name for the user's chosen script."""
    return "text_uthmani" if get_script(user_id) == "uthmani" else "text_indopak"

def script_label(user_id: int) -> str:
    s = get_script(user_id)
    return "🕌 Uthmani" if s == "uthmani" else "📿 Indo-Pak"

def script_toggle_label(user_id: int) -> str:
    """Label for the toggle button — shows what it will SWITCH TO."""
    s = get_script(user_id)
    return "Switch to 📿 Indo-Pak" if s == "uthmani" else "Switch to 🕌 Uthmani"

# ─────────────────────────────────────────────
#  TRANSLATIONS — 35+ Languages
#  IDs from api.quran.com/api/v4/resources/translations
# ─────────────────────────────────────────────
TRANSLATIONS = [
    # (id, English name, flag, native name)
    (131,  "English (Sahih Intl)",  "🇬🇧", "English"),
    (85,   "English (Yusuf Ali)",   "🇬🇧", "English (Yusuf Ali)"),
    (84,   "English (Pickthall)",   "🇬🇧", "English (Pickthall)"),
    (203,  "Tamil",                 "🇮🇳", "தமிழ்"),
    (37,   "Malayalam",             "🇮🇳", "മലയാളം"),
    (54,   "Urdu (Jalandhri)",      "🇵🇰", "اردو"),
    (97,   "Urdu (Ahmed Ali)",      "🇵🇰", "اردو (احمد علی)"),
    (33,   "Hindi",                 "🇮🇳", "हिंदी"),
    (163,  "Bengali",               "🇧🇩", "বাংলা"),
    (161,  "Indonesian",            "🇮🇩", "Bahasa Indonesia"),
    (134,  "Turkish",               "🇹🇷", "Türkçe"),
    (136,  "Russian",               "🇷🇺", "Русский"),
    (149,  "French",                "🇫🇷", "Français"),
    (27,   "German",                "🇩🇪", "Deutsch"),
    (83,   "Spanish",               "🇪🇸", "Español"),
    (153,  "Chinese (Simplified)",  "🇨🇳", "中文 (简体)"),
    (76,   "Japanese",              "🇯🇵", "日本語"),
    (120,  "Korean",                "🇰🇷", "한국어"),
    (39,   "Malay",                 "🇲🇾", "Bahasa Melayu"),
    (95,   "Hausa",                 "🇳🇬", "Hausa"),
    (103,  "Swahili",               "🇹🇿", "Kiswahili"),
    (31,   "Amharic",               "🇪🇹", "አማርኛ"),
    (74,   "Somali",                "🇸🇴", "Soomaali"),
    (32,   "Bosnian",               "🇧🇦", "Bosanski"),
    (26,   "Dutch",                 "🇳🇱", "Nederlands"),
    (43,   "Persian (Farsi)",       "🇮🇷", "فارسی"),
    (78,   "Pashto",                "🇦🇫", "پښتو"),
    (80,   "Portuguese",            "🇧🇷", "Português"),
    (53,   "Romanian",              "🇷🇴", "Română"),
    (35,   "Albanian",              "🇦🇱", "Shqip"),
    (45,   "Polish",                "🇵🇱", "Polski"),
    (52,   "Azerbaijani",           "🇦🇿", "Azərbaycanca"),
    (106,  "Uzbek",                 "🇺🇿", "Oʻzbekcha"),
    (62,   "Kazakh",                "🇰🇿", "Қазақша"),
    (81,   "Sindhi",                "🇵🇰", "سنڌي"),
    (17,   "Gujarati",              "🇮🇳", "ગુજરાતી"),
    (122,  "Kannada",               "🇮🇳", "ಕನ್ನಡ"),
    (124,  "Telugu",                "🇮🇳", "తెలుగు"),
    (44,   "Punjabi",               "🇮🇳", "ਪੰਜਾਬੀ"),
]

TRANSLATION_BY_ID = {t[0]: t for t in TRANSLATIONS}

# Per-user translation preference (default: English Sahih Intl)
USER_TRANSLATION: dict[int, int] = {}
# Per-user reciter search: user_id -> surah_num they're browsing
USER_RECITER_SEARCH: dict[int, int] = {}

def get_translation(user_id: int) -> int:
    return USER_TRANSLATION.get(user_id, 131)

def set_translation(user_id: int, trans_id: int):
    USER_TRANSLATION[user_id] = trans_id

def translation_label(user_id: int) -> str:
    tid = get_translation(user_id)
    t = TRANSLATION_BY_ID.get(tid)
    return f"{t[2]} {t[1]}" if t else "🇬🇧 English"

# ─────────────────────────────────────────────
#  CONSTANTS & STATE
# ─────────────────────────────────────────────
CHOOSING_RECITER, CHOOSING_FORMAT = range(2)

BASE_URL = "https://api.quran.com/api/v4"
EVERYAYAH = "https://everyayah.com/data"

# 114 Surahs — name, arabic name, total ayahs, revelation type
SURAHS = [
    (1, "Al-Fatihah", "الفاتحة", 7, "Meccan"),
    (2, "Al-Baqarah", "البقرة", 286, "Medinan"),
    (3, "Ali 'Imran", "آل عمران", 200, "Medinan"),
    (4, "An-Nisa", "النساء", 176, "Medinan"),
    (5, "Al-Ma'idah", "المائدة", 120, "Medinan"),
    (6, "Al-An'am", "الأنعام", 165, "Meccan"),
    (7, "Al-A'raf", "الأعراف", 206, "Meccan"),
    (8, "Al-Anfal", "الأنفال", 75, "Medinan"),
    (9, "At-Tawbah", "التوبة", 129, "Medinan"),
    (10, "Yunus", "يونس", 109, "Meccan"),
    (11, "Hud", "هود", 123, "Meccan"),
    (12, "Yusuf", "يوسف", 111, "Meccan"),
    (13, "Ar-Ra'd", "الرعد", 43, "Medinan"),
    (14, "Ibrahim", "إبراهيم", 52, "Meccan"),
    (15, "Al-Hijr", "الحجر", 99, "Meccan"),
    (16, "An-Nahl", "النحل", 128, "Meccan"),
    (17, "Al-Isra", "الإسراء", 111, "Meccan"),
    (18, "Al-Kahf", "الكهف", 110, "Meccan"),
    (19, "Maryam", "مريم", 98, "Meccan"),
    (20, "Ta-Ha", "طه", 135, "Meccan"),
    (21, "Al-Anbiya", "الأنبياء", 112, "Meccan"),
    (22, "Al-Hajj", "الحج", 78, "Medinan"),
    (23, "Al-Mu'minun", "المؤمنون", 118, "Meccan"),
    (24, "An-Nur", "النور", 64, "Medinan"),
    (25, "Al-Furqan", "الفرقان", 77, "Meccan"),
    (26, "Ash-Shu'ara", "الشعراء", 227, "Meccan"),
    (27, "An-Naml", "النمل", 93, "Meccan"),
    (28, "Al-Qasas", "القصص", 88, "Meccan"),
    (29, "Al-'Ankabut", "العنكبوت", 69, "Meccan"),
    (30, "Ar-Rum", "الروم", 60, "Meccan"),
    (31, "Luqman", "لقمان", 34, "Meccan"),
    (32, "As-Sajdah", "السجدة", 30, "Meccan"),
    (33, "Al-Ahzab", "الأحزاب", 73, "Medinan"),
    (34, "Saba", "سبأ", 54, "Meccan"),
    (35, "Fatir", "فاطر", 45, "Meccan"),
    (36, "Ya-Sin", "يس", 83, "Meccan"),
    (37, "As-Saffat", "الصافات", 182, "Meccan"),
    (38, "Sad", "ص", 88, "Meccan"),
    (39, "Az-Zumar", "الزمر", 75, "Meccan"),
    (40, "Ghafir", "غافر", 85, "Meccan"),
    (41, "Fussilat", "فصلت", 54, "Meccan"),
    (42, "Ash-Shura", "الشورى", 53, "Meccan"),
    (43, "Az-Zukhruf", "الزخرف", 89, "Meccan"),
    (44, "Ad-Dukhan", "الدخان", 59, "Meccan"),
    (45, "Al-Jathiyah", "الجاثية", 37, "Meccan"),
    (46, "Al-Ahqaf", "الأحقاف", 35, "Meccan"),
    (47, "Muhammad", "محمد", 38, "Medinan"),
    (48, "Al-Fath", "الفتح", 29, "Medinan"),
    (49, "Al-Hujurat", "الحجرات", 18, "Medinan"),
    (50, "Qaf", "ق", 45, "Meccan"),
    (51, "Adh-Dhariyat", "الذاريات", 60, "Meccan"),
    (52, "At-Tur", "الطور", 49, "Meccan"),
    (53, "An-Najm", "النجم", 62, "Meccan"),
    (54, "Al-Qamar", "القمر", 55, "Meccan"),
    (55, "Ar-Rahman", "الرحمن", 78, "Medinan"),
    (56, "Al-Waqi'ah", "الواقعة", 96, "Meccan"),
    (57, "Al-Hadid", "الحديد", 29, "Medinan"),
    (58, "Al-Mujadila", "المجادلة", 22, "Medinan"),
    (59, "Al-Hashr", "الحشر", 24, "Medinan"),
    (60, "Al-Mumtahanah", "الممتحنة", 13, "Medinan"),
    (61, "As-Saf", "الصف", 14, "Medinan"),
    (62, "Al-Jumu'ah", "الجمعة", 11, "Medinan"),
    (63, "Al-Munafiqun", "المنافقون", 11, "Medinan"),
    (64, "At-Taghabun", "التغابن", 18, "Medinan"),
    (65, "At-Talaq", "الطلاق", 12, "Medinan"),
    (66, "At-Tahrim", "التحريم", 12, "Medinan"),
    (67, "Al-Mulk", "الملك", 30, "Meccan"),
    (68, "Al-Qalam", "القلم", 52, "Meccan"),
    (69, "Al-Haqqah", "الحاقة", 52, "Meccan"),
    (70, "Al-Ma'arij", "المعارج", 44, "Meccan"),
    (71, "Nuh", "نوح", 28, "Meccan"),
    (72, "Al-Jinn", "الجن", 28, "Meccan"),
    (73, "Al-Muzzammil", "المزمل", 20, "Meccan"),
    (74, "Al-Muddaththir", "المدثر", 56, "Meccan"),
    (75, "Al-Qiyamah", "القيامة", 40, "Meccan"),
    (76, "Al-Insan", "الإنسان", 31, "Medinan"),
    (77, "Al-Mursalat", "المرسلات", 50, "Meccan"),
    (78, "An-Naba", "النبأ", 40, "Meccan"),
    (79, "An-Nazi'at", "النازعات", 46, "Meccan"),
    (80, "'Abasa", "عبس", 42, "Meccan"),
    (81, "At-Takwir", "التكوير", 29, "Meccan"),
    (82, "Al-Infitar", "الانفطار", 19, "Meccan"),
    (83, "Al-Mutaffifin", "المطففين", 36, "Meccan"),
    (84, "Al-Inshiqaq", "الانشقاق", 25, "Meccan"),
    (85, "Al-Buruj", "البروج", 22, "Meccan"),
    (86, "At-Tariq", "الطارق", 17, "Meccan"),
    (87, "Al-A'la", "الأعلى", 19, "Meccan"),
    (88, "Al-Ghashiyah", "الغاشية", 26, "Meccan"),
    (89, "Al-Fajr", "الفجر", 30, "Meccan"),
    (90, "Al-Balad", "البلد", 20, "Meccan"),
    (91, "Ash-Shams", "الشمس", 15, "Meccan"),
    (92, "Al-Layl", "الليل", 21, "Meccan"),
    (93, "Ad-Duha", "الضحى", 11, "Meccan"),
    (94, "Ash-Sharh", "الشرح", 8, "Meccan"),
    (95, "At-Tin", "التين", 8, "Meccan"),
    (96, "Al-'Alaq", "العلق", 19, "Meccan"),
    (97, "Al-Qadr", "القدر", 5, "Meccan"),
    (98, "Al-Bayyinah", "البينة", 8, "Medinan"),
    (99, "Az-Zalzalah", "الزلزلة", 8, "Medinan"),
    (100, "Al-'Adiyat", "العاديات", 11, "Meccan"),
    (101, "Al-Qari'ah", "القارعة", 11, "Meccan"),
    (102, "At-Takathur", "التكاثر", 8, "Meccan"),
    (103, "Al-'Asr", "العصر", 3, "Meccan"),
    (104, "Al-Humazah", "الهمزة", 9, "Meccan"),
    (105, "Al-Fil", "الفيل", 5, "Meccan"),
    (106, "Quraysh", "قريش", 4, "Meccan"),
    (107, "Al-Ma'un", "الماعون", 7, "Meccan"),
    (108, "Al-Kawthar", "الكوثر", 3, "Meccan"),
    (109, "Al-Kafirun", "الكافرون", 6, "Meccan"),
    (110, "An-Nasr", "النصر", 3, "Medinan"),
    (111, "Al-Masad", "المسد", 5, "Meccan"),
    (112, "Al-Ikhlas", "الإخلاص", 4, "Meccan"),
    (113, "Al-Falaq", "الفلق", 5, "Meccan"),
    (114, "An-Nas", "الناس", 6, "Meccan"),
]

# 100+ Qaris from EveryAyah + Quran.com audio API
RECITERS = [
    # Slug, Display Name, Country/Style, everyayah folder
    ("mishary_alafasy",       "Mishary Rashid Al-Afasy",     "🇰🇼 Kuwait",       "Alafasy_128kbps"),
    ("abu_bakr_shatri",       "Abu Bakr Al-Shatri",          "🇸🇦 Saudi Arabia", "Abu_Bakr_Ash-Shaatree_128kbps"),
    ("maher_almuaiqly",       "Maher Al-Muaiqly",            "🇸🇦 Saudi Arabia", "Maher_Al_Muaiqly_128kbps"),
    ("saad_alghamdi",         "Saad Al-Ghamdi",              "🇸🇦 Saudi Arabia", "Saad_Al-Ghamidi_128kbps"),
    ("abdulrahman_assudais",  "Abdul Rahman Al-Sudais",      "🇸🇦 Saudi Arabia", "Abdul_Basit_Murattal_192kbps"),
    ("saud_shuraim",          "Saud Al-Shuraim",             "🇸🇦 Saudi Arabia", "Saud_Al-Shuraim_128kbps"),
    ("ahmed_ajamy",           "Ahmed Al-Ajamy",              "🇸🇦 Saudi Arabia", "Ahmed_ibn_Ali_al-Ajamy_128kbps"),
    ("hani_rifai",            "Hani Al-Rifai",               "🇸🇦 Saudi Arabia", "Hani_Rifai_192kbps"),
    ("khalid_qahtani",        "Khalid Al-Qahtani",           "🇸🇦 Saudi Arabia", "Khalid_Al-Qahtani_192kbps"),
    ("nasser_alqatami",       "Nasser Al-Qatami",            "🇰🇼 Kuwait",       "Nasser_Alqatami_128kbps"),
    ("abdulbasit_murattal",   "Abdul Basit (Murattal)",      "🇪🇬 Egypt",        "Abdul_Basit_Murattal_192kbps"),
    ("abdulbasit_mujawwad",   "Abdul Basit (Mujawwad)",      "🇪🇬 Egypt",        "Abdul_Basit_Mujawwad_128kbps"),
    ("minshawi_murattal",     "Mohamed Siddiq Al-Minshawi",  "🇪🇬 Egypt",        "Minshawi_Murattal_128kbps"),
    ("minshawi_mujawwad",     "Minshawi (Mujawwad)",         "🇪🇬 Egypt",        "Minshawi_Mujawwad_128kbps"),
    ("husary_murattal",       "Mahmoud Khalil Al-Husary",    "🇪🇬 Egypt",        "Husary_128kbps"),
    ("husary_mujawwad",       "Husary (Mujawwad)",           "🇪🇬 Egypt",        "Husary_Mujawwad_128kbps"),
    ("ibrahim_akhdar",        "Ibrahim Al-Akhdar",           "🇸🇦 Saudi Arabia", "Ibrahim_Al-Akhdar_128kbps"),
    ("ali_jaber",             "Ali Ibn Abi Al-'Iz Jaber",    "🇸🇦 Saudi Arabia", "Ali_Jaber_128kbps"),
    ("fares_abbad",           "Fares Abbad",                 "🇩🇿 Algeria",      "Fares_Abbad_64kbps"),
    ("yasser_dosari",         "Yasser Al-Dossari",           "🇸🇦 Saudi Arabia", "Yasser_Ad-Dussary_128kbps"),
    ("bandar_baleelah",       "Bandar Baleelah",             "🇸🇦 Saudi Arabia", "Bandar_Baleelah_128kbps"),
    ("muhammad_luhaidan",     "Muhammad Al-Luhaidan",        "🇸🇦 Saudi Arabia", "Muhammad_Luhaidan_128kbps"),
    ("mustafa_ismail",        "Mustafa Ismail",              "🇪🇬 Egypt",        "Mustafa_Ismail_128kbps"),
    ("tawfiq_alsayegh",       "Tawfiq Al-Sayegh",            "🇸🇦 Saudi Arabia", "Tawfiq_As-Sayegh_128kbps"),
    ("salah_bukhatir",        "Salah Bukhatir",              "🇸🇦 Saudi Arabia", "Salah_Bukhatir_128kbps"),
    ("idris_abkar",           "Idris Abkar",                 "🇸🇦 Saudi Arabia", "Idrees_Abkar_128kbps"),
    ("obaid_alrawahi",        "Obaid Alrawahi",              "🇴🇲 Oman",         "Obaid_Alrawahi_128kbps"),
    ("ramadan_shalaby",       "Ramadan Shalaby",             "🇪🇬 Egypt",        "Ramadan_As-Sabliy_96kbps"),
    ("ziyad_patel",           "Ziyaad Patel",                "🇿🇦 South Africa", "Ziyaad_Patel_128kbps"),
    ("hatem_farid",           "Hatem Farid Al-Wardy",        "🇸🇦 Saudi Arabia", "Hatem_Farid_al-Wardee_128kbps"),
    ("nabil_rifa",            "Nabil Al-Rifa'i",             "🇸🇾 Syria",        "Nabil_Ar-Rifai_128kbps"),
    ("akram_alwaqfy",         "Akram Al-Alaqmi",             "🇸🇦 Saudi Arabia", "Akram_AlAlaqmi_128kbps"),
    ("tarek_mohammed",        "Tarek Mohammed",              "🇸🇦 Saudi Arabia", "Tarek_Mohammed_128kbps"),
    ("warsh_madinah",         "Warsh (Madinah)",             "🇲🇦 Morocco",      "warsh_from_nafi_by_al-Minshawy_Murattal_128kbps"),
    ("ayman_suwaid",          "Ayman Suwayd",                "🇸🇦 Saudi Arabia", "Ayman_Sowaid_128kbps"),
    ("Abdullah_Basfar",       "Abdullah Basfar",             "🇸🇦 Saudi Arabia", "Abdullah_Basfar_128kbps"),
    ("abdulmohsen_harthy",    "Abdul Mohsen Al-Harthy",      "🇸🇦 Saudi Arabia", "AbdulMohsen_Al-Harthy_128kbps"),
    ("khaled_aljaleel",       "Khaled Al-Jaleel",            "🇸🇦 Saudi Arabia", "Khaled_Aljaleel_128kbps"),
    ("muhammad_al_tablawi",   "Muhammad Al-Tablawi",         "🇪🇬 Egypt",        "Muhammad_Jibreel_128kbps"),
    ("muhammad_jibreel",      "Muhammad Jibreel",            "🇸🇦 Saudi Arabia", "Muhammad_Jibreel_128kbps"),
    ("abdulaziz_alahmed",     "Abdul Aziz Al-Ahmed",         "🇸🇦 Saudi Arabia", "Abdul_Aziz_Al-Ahmad_128kbps"),
    ("nawaf_salamah",         "Nawaf Salamah",               "🇸🇦 Saudi Arabia", "Nawaf_Salamah_128kbps"),
    ("walid_ugayyir",         "Walid Al-Ugayyir",            "🇸🇦 Saudi Arabia", "Walid_Ugayyir_128kbps"),
    ("parhizgar",             "Parhizgar",                   "🇮🇷 Iran",         "Parhizgar_40kbps"),
    ("alqaasim",              "Abdullah Al-Qasim",           "🇸🇦 Saudi Arabia", "Abdullah_Al_Juhany_128kbps"),
    ("juhany",                "Abdullah Al-Juhany",          "🇸🇦 Saudi Arabia", "Abdullah_Al_Juhany_128kbps"),
    ("mansour_salimi",        "Mansoor Al-Zaahrani",         "🇸🇦 Saudi Arabia", "Mansour_Al-Zaahrani_128kbps"),
    ("khalifa_taniji",        "Khalifa Al-Taniji",           "🇦🇪 UAE",          "Khalefa_Al_Tunaiji_32kbps"),
    ("mahmoud_ali_banna",     "Mahmoud Ali Al-Banna",        "🇪🇬 Egypt",        "Mahmoud_Ali_Al_Banna_128kbps"),
    ("ibrahim_alduossary",    "Ibrahim Al-Dossary",          "🇸🇦 Saudi Arabia", "Ibrahim_Aldosary_128kbps"),
]

# Build lookup dicts
SURAH_BY_NUMBER = {s[0]: s for s in SURAHS}
SURAH_BY_NAME = {}
for s in SURAHS:
    SURAH_BY_NAME[s[1].lower()] = s
    SURAH_BY_NAME[s[2]] = s  # Arabic name lookup too
    # Short aliases
    clean = re.sub(r"[^a-z]", "", s[1].lower())
    SURAH_BY_NAME[clean] = s

RECITER_BY_SLUG = {r[0]: r for r in RECITERS}

# ─────────────────────────────────────────────
#  DECORATIVE TEXT HELPERS
# ─────────────────────────────────────────────

BISMILLAH = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
DIVIDER   = "─────────────────────"

def surah_header(surah):
    num, name_en, name_ar, ayahs, rev = surah
    badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"
    return (
        f"✨ *{name_ar}*\n"
        f"*Surah {num} — {name_en}*\n"
        f"_{badge} · {ayahs} Ayahs_\n"
        f"`{DIVIDER}`"
    )

def welcome_text():
    return (
        "🌿 *بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ* 🌿\n\n"
        "As-salamu alaykum wa rahmatullahi wa barakatuh 🤍\n\n"
        "Welcome to *Nur Al-Quran* — your personal Quran companion.\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "📖 *What I can do:*\n"
        "• Search any Surah by name or number\n"
        "• Read the full Surah with translation\n"
        "• Download audio from 100\\+ Qaris\n"
        "• Download Surah as PDF\n"
        "• Browse all 114 Surahs\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "💬 *Just type a Surah name or number:*\n"
        "`Al-Fatiha` · `Yaseen` · `Al-Mulk` · `18` · `112`\n\n"
        "Or use /list to browse all Surahs 📚"
    )

# ─────────────────────────────────────────────
#  QURAN API HELPERS
# ─────────────────────────────────────────────

async def fetch_surah_verses(surah_num: int, translation: str = "131", field: str = "text_uthmani") -> list:
    """Fetch verses with translation from quran.com API v4."""
    url = f"{BASE_URL}/verses/by_chapter/{surah_num}"
    params = {
        "language": "en",
        "words": "true",
        "translations": translation,
        "fields": field,
        "per_page": 286,
        "page": 1
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("verses", [])
    return []

async def fetch_audio_url_everyayah(surah_num: int, reciter_folder: str) -> str:
    """Build full surah audio URL from EveryAyah CDN."""
    surah_str = str(surah_num).zfill(3)
    # EveryAyah hosts full surah files too
    return f"{EVERYAYAH}/{reciter_folder}/{surah_str}001.mp3"

async def build_surah_text(surah_num: int) -> str:
    """Build readable Surah text with Arabic + English translation."""
    verses = await fetch_surah_verses(surah_num)
    if not verses:
        return None

    surah = SURAH_BY_NUMBER.get(surah_num)
    lines = []

    if surah_num != 9:  # Surah 9 has no Bismillah
        lines.append(f"*{BISMILLAH}*\n")

    for v in verses:
        ayah_key = v.get("verse_key", "")
        arabic = v.get("text_uthmani", "")
        translation_text = ""
        trans = v.get("translations", [])
        if trans:
            translation_text = trans[0].get("text", "")
            # Strip HTML tags
            translation_text = re.sub(r"<[^>]+>", "", translation_text)

        lines.append(
            f"*{ayah_key}*\n"
            f"{arabic}\n"
            f"_{translation_text}_\n"
        )

    return "\n".join(lines)

# ─────────────────────────────────────────────
#  SURAH SEARCH
# ─────────────────────────────────────────────

def find_surah(query: str) -> Optional[tuple]:
    query = query.strip()

    # By number
    if query.isdigit():
        n = int(query)
        if 1 <= n <= 114:
            return SURAH_BY_NUMBER[n]
        return None

    # By name (exact or partial)
    q_lower = query.lower()
    # Direct lookup
    if q_lower in SURAH_BY_NAME:
        return SURAH_BY_NAME[q_lower]

    # Partial match
    for s in SURAHS:
        if q_lower in s[1].lower():
            return s
        # Without "Al-" prefix
        if q_lower in s[1].lower().replace("al-", "").replace("an-", "").replace("as-", "").replace("at-", "").replace("az-", ""):
            return s

    # Arabic name
    if query in SURAH_BY_NAME:
        return SURAH_BY_NAME[query]

    return None

# ─────────────────────────────────────────────
#  KEYBOARDS
# ─────────────────────────────────────────────

def surah_action_keyboard(surah_num: int, user_id: int = 0):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Read Surah", callback_data=f"read:{surah_num}:0"),
            InlineKeyboardButton("🎧 Audio", callback_data=f"audio_menu:{surah_num}"),
        ],
        [
            InlineKeyboardButton("📥 Download PDF", callback_data=f"pdf:{surah_num}"),
            InlineKeyboardButton("🔤 Transliteration", callback_data=f"translit:{surah_num}"),
        ],
        [
            InlineKeyboardButton("ℹ️ Surah Info", callback_data=f"info:{surah_num}"),
            InlineKeyboardButton("🔀 Random Surah", callback_data="random"),
        ],
        [
            InlineKeyboardButton(
                f"🌍 {translation_label(user_id)}",
                callback_data=f"trans_menu:{surah_num}:0"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔡 {script_toggle_label(user_id)}",
                callback_data=f"script:{surah_num}"
            ),
        ],
        [
            InlineKeyboardButton("🏠 Home", callback_data="home"),
        ]
    ])

def reciter_keyboard(surah_num: int, page: int = 0):
    """Paginated reciter selection — 5 per page."""
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_reciters = RECITERS[start:end]
    total_pages = (len(RECITERS) + per_page - 1) // per_page

    rows = []
    for slug, name, country, _ in page_reciters:
        rows.append([InlineKeyboardButton(
            f"{country} {name}",
            callback_data=f"recite:{surah_num}:{slug}"
        )])

    # Navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"audio_page:{surah_num}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if end < len(RECITERS):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"audio_page:{surah_num}:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")])
    return InlineKeyboardMarkup(rows)

def list_keyboard(page: int = 0):
    """Browse all 114 surahs — 10 per page."""
    per_page = 10
    start = page * per_page
    end = min(start + per_page, 114)
    total_pages = (114 + per_page - 1) // per_page

    rows = []
    for i in range(start, end, 2):
        row = []
        s1 = SURAHS[i]
        row.append(InlineKeyboardButton(
            f"{s1[0]}. {s1[1]}", callback_data=f"surah:{s1[0]}"
        ))
        if i + 1 < end:
            s2 = SURAHS[i+1]
            row.append(InlineKeyboardButton(
                f"{s2[0]}. {s2[1]}", callback_data=f"surah:{s2[0]}"
            ))
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"list:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if end < 114:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"list:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def read_navigation_keyboard(surah_num: int, chunk: int, total_chunks: int):
    rows = []
    nav = []
    if chunk > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"read:{surah_num}:{chunk-1}"))
    nav.append(InlineKeyboardButton(f"{chunk+1}/{total_chunks}", callback_data="noop"))
    if chunk < total_chunks - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"read:{surah_num}:{chunk+1}"))
    rows.append(nav)
    rows.append([
        InlineKeyboardButton("🎧 Audio", callback_data=f"audio_menu:{surah_num}"),
        InlineKeyboardButton("↩️ Surah", callback_data=f"surah:{surah_num}"),
    ])
    return InlineKeyboardMarkup(rows)

def translation_keyboard(surah_num: int, page: int = 0, user_id: int = 0):
    """Paginated translation language picker — 5 per page."""
    per_page = 5
    start = page * per_page
    end = min(start + per_page, len(TRANSLATIONS))
    total_pages = (len(TRANSLATIONS) + per_page - 1) // per_page
    current_tid = get_translation(user_id)

    rows = []
    for tid, name, flag, native in TRANSLATIONS[start:end]:
        tick = " ✅" if tid == current_tid else ""
        rows.append([InlineKeyboardButton(
            f"{flag} {name} — {native}{tick}",
            callback_data=f"set_trans:{surah_num}:{tid}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"trans_menu:{surah_num}:{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if end < len(TRANSLATIONS):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"trans_menu:{surah_num}:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")])
    return InlineKeyboardMarkup(rows)

def reciter_search_results_keyboard(surah_num: int, results: list):
    """Show reciter search results."""
    rows = []
    for slug, name, country, _ in results[:10]:
        rows.append([InlineKeyboardButton(
            f"{country} {name}",
            callback_data=f"recite:{surah_num}:{slug}"
        )])
    rows.append([
        InlineKeyboardButton("🔍 Search Again", callback_data=f"reciter_search_prompt:{surah_num}"),
        InlineKeyboardButton("📋 Browse All", callback_data=f"audio_menu:{surah_num}"),
    ])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")])
    return InlineKeyboardMarkup(rows)

# ─────────────────────────────────────────────
#  COMMAND HANDLERS
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        welcome_text(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Browse All 114 Surahs", callback_data="list:0")],
            [
                InlineKeyboardButton("🌟 Al-Fatiha", callback_data="surah:1"),
                InlineKeyboardButton("📿 Ya-Sin", callback_data="surah:36"),
            ],
            [
                InlineKeyboardButton("🌙 Al-Mulk", callback_data="surah:67"),
                InlineKeyboardButton("💫 Al-Ikhlas", callback_data="surah:112"),
            ],
            [InlineKeyboardButton("🔀 Random Surah", callback_data="random")],
        ])
    )

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *All 114 Surahs of the Holy Quran*\n_Select a Surah to explore:_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=list_keyboard(0)
    )

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 Please provide a Surah name or number.\n\nExamples:\n`/search Yaseen`\n`/search 18`\n`/search Al-Mulk`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    query = " ".join(context.args)
    await handle_search(update, context, query)

async def cmd_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    surah = random.choice(SURAHS)
    await send_surah_card(update.message, surah)

async def cmd_juz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick Juz guide."""
    juz_map = """
📖 *Juz (Para) Guide*

Juz 1 → Al-Fatiha (1) to Al-Baqarah 2:141
Juz 2 → Al-Baqarah 2:142–252
Juz 3 → Al-Baqarah 2:253 to Ali 'Imran 3:92
Juz 4 → Ali 'Imran 3:93 to An-Nisa 4:23
Juz 5 → An-Nisa 4:24–147
Juz 7 → Al-Ma'idah 5:82 to Al-An'am 6:110
...and so on through Juz 30 (Surah 78–114)

_Type a Surah name or number to begin reading._
    """
    await update.message.reply_text(juz_map, parse_mode=ParseMode.MARKDOWN)

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        f"🌍 *Translation Language*\n\n"
        f"Current: *{translation_label(user_id)}*\n\n"
        f"Select any Surah first, then tap the\n"
        f"🌍 language button to change it.\n\n"
        f"Or open a quick Surah to change now:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌍 Change Language (via Al-Fatiha)", callback_data="trans_menu:1:0")],
        ])
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🌿 *Nur Al-Quran — Help*\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "*📖 Reading*\n"
        "`/start` — Welcome screen\n"
        "`/list` — Browse all 114 Surahs\n"
        "`/search <name or number>` — Find a Surah\n"
        "`/random` — Open a random Surah\n\n"
        "*🌍 Translation \\(35\\+ Languages\\)*\n"
        "`/lang` — Change translation language\n"
        "• Tamil, Malayalam, Urdu, Hindi, Bengali\n"
        "• English, French, Turkish, Indonesian\n"
        "• 35\\+ languages total\n\n"
        "*🎧 Audio \\(50\\+ Reciters\\)*\n"
        "• Tap 🎧 Audio → Browse or Search\n"
        "• 🔍 Search reciter by name\n"
        "• Audio sent as MP3\n\n"
        "*🔡 Script*\n"
        "• Toggle 🕌 Uthmani ↔ 📿 Indo\\-Pak\n\n"
        "*📥 Download*\n"
        "• PDF links, transliteration\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "_May Allah bless your recitation_ 🤍"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ─────────────────────────────────────────────
#  MESSAGE HANDLER (Smart Search)
# ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    # Check if user is in reciter search mode
    if user_id in USER_RECITER_SEARCH:
        surah_num = USER_RECITER_SEARCH.pop(user_id)
        query_lower = text.lower()
        results = [
            r for r in RECITERS
            if query_lower in r[1].lower() or query_lower in r[0].lower()
        ]
        surah = SURAH_BY_NUMBER[surah_num]
        if not results:
            await update.message.reply_text(
                f"🔍 No reciters found for *{text}*\n\n"
                f"Try: `mishary`, `basit`, `minshawi`, `sudais`, `luhaidan`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Try Again", callback_data=f"reciter_search_prompt:{surah_num}")],
                    [InlineKeyboardButton("📋 Browse All", callback_data=f"audio_page:{surah_num}:0")],
                ])
            )
        else:
            await update.message.reply_text(
                f"🎙️ *{len(results)} reciter(s) found for* `{text}`\n"
                f"_Surah {surah_num}: {surah[1]}_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reciter_search_results_keyboard(surah_num, results)
            )
        return

    await handle_search(update, context, text)

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    surah = find_surah(query)
    if not surah:
        # Try to help with common mistakes
        suggestions = []
        q = query.lower()
        for s in SURAHS:
            score = 0
            for part in q.split():
                if part in s[1].lower():
                    score += 2
            if score > 0:
                suggestions.append((score, s))
        suggestions.sort(reverse=True)
        top = suggestions[:3]

        if top:
            btns = [[InlineKeyboardButton(
                f"{s[0]}. {s[1]} ({s[2]})", callback_data=f"surah:{s[0]}"
            )] for _, s in top]
            btns.append([InlineKeyboardButton("📚 Browse All", callback_data="list:0")])
            msg = update.message if hasattr(update, 'message') and update.message else None
            if msg:
                await msg.reply_text(
                    f"🔍 No exact match for *{query}*.\n\nDid you mean?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(btns)
                )
        else:
            msg = update.message if hasattr(update, 'message') and update.message else None
            if msg:
                await msg.reply_text(
                    f"🤍 I couldn't find Surah *{query}*.\n\n"
                    "Try typing: `Yaseen`, `Al-Mulk`, `112`, or use /list",
                    parse_mode=ParseMode.MARKDOWN
                )
        return

    msg = update.message if hasattr(update, 'message') and update.message else None
    if msg:
        await send_surah_card(msg, surah)

async def send_surah_card(message, surah: tuple):
    num, name_en, name_ar, ayahs, rev = surah
    badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"
    user_id = message.from_user.id if message.from_user else 0
    text = (
        f"🌿 *{name_ar}*\n"
        f"✨ *Surah {num} — {name_en}*\n"
        f"`{badge}` · `{ayahs} Ayahs`\n\n"
        f"_{BISMILLAH}_\n\n"
        f"Script: _{script_label(user_id)}_\n"
        f"What would you like to do?"
    )
    await message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=surah_action_keyboard(num, user_id)
    )

# ─────────────────────────────────────────────
#  CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── home
    if data == "home":
        await query.edit_message_text(
            welcome_text(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Browse All 114 Surahs", callback_data="list:0")],
                [
                    InlineKeyboardButton("🌟 Al-Fatiha", callback_data="surah:1"),
                    InlineKeyboardButton("📿 Ya-Sin", callback_data="surah:36"),
                ],
                [
                    InlineKeyboardButton("🌙 Al-Mulk", callback_data="surah:67"),
                    InlineKeyboardButton("💫 Al-Ikhlas", callback_data="surah:112"),
                ],
                [InlineKeyboardButton("🔀 Random Surah", callback_data="random")],
            ])
        )
        return

    # ── noop
    if data == "noop":
        return

    # ── random
    if data == "random":
        import random
        surah = random.choice(SURAHS)
        num, name_en, name_ar, ayahs, rev = surah
        badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"
        user_id = query.from_user.id
        text = (
            f"🎲 *Random Surah*\n\n"
            f"🌿 *{name_ar}*\n"
            f"✨ *Surah {num} — {name_en}*\n"
            f"`{badge}` · `{ayahs} Ayahs`\n\n"
            f"_{BISMILLAH}_\n\n"
            f"Script: _{script_label(user_id)}_\n"
            f"What would you like to do?"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=surah_action_keyboard(num, user_id)
        )
        return

    # ── surah card
    if data.startswith("surah:"):
        num = int(data.split(":")[1])
        surah = SURAH_BY_NUMBER[num]
        num, name_en, name_ar, ayahs, rev = surah
        badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"
        user_id = query.from_user.id
        text = (
            f"🌿 *{name_ar}*\n"
            f"✨ *Surah {num} — {name_en}*\n"
            f"`{badge}` · `{ayahs} Ayahs`\n\n"
            f"_{BISMILLAH}_\n\n"
            f"Script: _{script_label(user_id)}_\n"
            f"What would you like to do?"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=surah_action_keyboard(num, user_id)
        )
        return

    # ── list browser
    if data.startswith("list:"):
        page = int(data.split(":")[1])
        await query.edit_message_text(
            "📚 *All 114 Surahs of the Holy Quran*\n_Select a Surah to explore:_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=list_keyboard(page)
        )
        return

    # ── read surah (paginated, 10 ayahs per page)
    if data.startswith("read:"):
        parts = data.split(":")
        surah_num = int(parts[1])
        chunk = int(parts[2])
        user_id = query.from_user.id

        await query.edit_message_text(
            "⏳ _Fetching Surah..._",
            parse_mode=ParseMode.MARKDOWN
        )

        field = script_field(user_id)
        verses = await fetch_surah_verses(surah_num, translation=str(get_translation(user_id)), field=field)
        if not verses:
            await query.edit_message_text("❌ Could not load Surah. Please try again.")
            return

        per_chunk = 10
        total_chunks = (len(verses) + per_chunk - 1) // per_chunk
        chunk = max(0, min(chunk, total_chunks - 1))

        start = chunk * per_chunk
        end = start + per_chunk
        chunk_verses = verses[start:end]

        surah = SURAH_BY_NUMBER[surah_num]
        script_name = script_label(user_id)
        trans_name = translation_label(user_id)
        lines = [f"📖 *{surah[2]}* — *{surah[1]}*\n_{script_name} · {trans_name}_\n"]

        if surah_num != 9 and chunk == 0:
            lines.append(f"_{BISMILLAH}_\n")

        for v in chunk_verses:
            ayah_key = v.get("verse_key", "")
            # Pick whichever field is present
            arabic = v.get(field) or v.get("text_uthmani") or v.get("text_indopak", "")
            trans = v.get("translations", [])
            translation_text = ""
            if trans:
                translation_text = re.sub(r"<[^>]+>", "", trans[0].get("text", ""))
            lines.append(f"*{ayah_key}*\n{arabic}\n_{translation_text}_\n")

        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n\n_...continued on next page_"

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=read_navigation_keyboard(surah_num, chunk, total_chunks)
        )
        return

    # ── script toggle
    if data.startswith("script:"):
        surah_num = int(data.split(":")[1])
        user_id = query.from_user.id
        # Flip the script
        current = get_script(user_id)
        new_script = "indopak" if current == "uthmani" else "uthmani"
        set_script(user_id, new_script)

        surah = SURAH_BY_NUMBER[surah_num]
        num, name_en, name_ar, ayahs, rev = surah
        badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"

        new_label = script_label(user_id)
        icon = "📿" if new_script == "indopak" else "🕌"
        await query.edit_message_text(
            f"🌿 *{name_ar}*\n"
            f"✨ *Surah {num} — {name_en}*\n"
            f"`{badge}` · `{ayahs} Ayahs`\n\n"
            f"_{BISMILLAH}_\n\n"
            f"Script: _{new_label}_ ✅\n"
            f"What would you like to do?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=surah_action_keyboard(num, user_id)
        )
        await query.answer(f"{icon} Switched to {new_label}!", show_alert=False)
        return

    # ── surah info
    if data.startswith("info:"):
        surah_num = int(data.split(":")[1])
        surah = SURAH_BY_NUMBER[surah_num]
        num, name_en, name_ar, ayahs, rev = surah

        # Additional info
        words_approx = ayahs * 12
        letters_approx = ayahs * 50

        text = (
            f"ℹ️ *Surah Information*\n\n"
            f"🌿 *{name_ar}* ({name_en})\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📌 *Number:* {num}\n"
            f"📜 *Revelation:* {'Makkah 🕌' if rev == 'Meccan' else 'Madinah 🌙'}\n"
            f"📿 *Total Ayahs:* {ayahs}\n"
            f"📖 *Approx Words:* ~{words_approx:,}\n\n"
        )

        # Special notes for famous Surahs
        notes = {
            1: "Known as Umm Al-Quran (Mother of the Quran). Recited in every unit of prayer.",
            2: "The longest Surah, contains Ayat Al-Kursi (2:255) — the greatest verse.",
            18: "Recommended to recite every Friday. Contains stories of the People of the Cave.",
            36: "Known as the Heart of the Quran.",
            55: "Repeating verse: 'Which of the favors of your Lord will you deny?'",
            67: "Protects from the punishment of the grave.",
            112: "Equal to one-third of the Quran in reward.",
        }
        if num in notes:
            text += f"💡 *Note:* _{notes[num]}_\n"

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📖 Read", callback_data=f"read:{num}:0"),
                    InlineKeyboardButton("🎧 Audio", callback_data=f"audio_menu:{num}"),
                ],
                [InlineKeyboardButton("↩️ Back", callback_data=f"surah:{num}")]
            ])
        )
        return

    # ── audio menu
    if data.startswith("audio_menu:"):
        surah_num = int(data.split(":")[1])
        surah = SURAH_BY_NUMBER[surah_num]
        text = (
            f"🎧 *Audio Recitation*\n"
            f"_Surah {surah_num}: {surah[1]} ({surah[2]})_\n\n"
            f"🎙️ *{len(RECITERS)} Reciters available*\n"
            f"Browse the list or search by name:"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Search Reciter by Name", callback_data=f"reciter_search_prompt:{surah_num}")],
                [InlineKeyboardButton("📋 Browse All Reciters", callback_data=f"audio_page:{surah_num}:0")],
                [InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")],
            ])
        )
        return

    # ── audio page navigation (browse list)
    if data.startswith("audio_page:"):
        _, surah_num, page = data.split(":")
        surah_num = int(surah_num)
        page = int(page)
        surah = SURAH_BY_NUMBER[surah_num]
        text = (
            f"🎧 *Audio Recitation*\n"
            f"_Surah {surah_num}: {surah[1]} ({surah[2]})_\n\n"
            f"Choose a Qari — {len(RECITERS)} reciters available:\n"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reciter_keyboard(surah_num, page)
        )
        return

    # ── recite (send audio)
    if data.startswith("recite:"):
        parts = data.split(":")
        surah_num = int(parts[1])
        reciter_slug = parts[2]
        reciter = RECITER_BY_SLUG.get(reciter_slug)
        surah = SURAH_BY_NUMBER[surah_num]

        if not reciter:
            await query.edit_message_text("❌ Reciter not found.")
            return

        slug, name, country, folder = reciter
        surah_str = str(surah_num).zfill(3)

        # EveryAyah full surah URL pattern
        audio_url = f"{EVERYAYAH}/{folder}/{surah_str}001.mp3"

        await query.edit_message_text(
            f"🎧 *Fetching Audio...*\n\n"
            f"📿 *Surah {surah_num}: {surah[1]}*\n"
            f"🎙️ Reciter: _{name}_\n"
            f"{country}\n\n"
            f"_Please wait..._",
            parse_mode=ParseMode.MARKDOWN
        )

        # Try to send audio via URL directly (Telegram can handle direct MP3 URLs)
        try:
            caption = (
                f"🌿 *{surah[2]}*\n"
                f"*Surah {surah_num}: {surah[1]}*\n"
                f"🎙️ {name} {country}\n\n"
                f"_{BISMILLAH}_\n\n"
                f"🤍 Nur Al-Quran Bot"
            )
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                title=f"Surah {surah[1]} — {name}",
                performer=name,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Back to Surah", callback_data=f"surah:{surah_num}")]
                ])
            )
            await query.edit_message_text(
                f"✅ *Audio sent!*\n\n"
                f"📿 Surah {surah_num}: {surah[1]}\n"
                f"🎙️ {name} {country}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎧 Other Reciters", callback_data=f"audio_menu:{surah_num}"),
                        InlineKeyboardButton("↩️ Surah", callback_data=f"surah:{surah_num}"),
                    ]
                ])
            )
        except Exception as e:
            logger.error(f"Audio send error: {e}")
            # Fallback: send as link
            await query.edit_message_text(
                f"🎧 *Audio Link*\n\n"
                f"📿 Surah {surah_num}: {surah[1]}\n"
                f"🎙️ {name} {country}\n\n"
                f"🔗 [Listen / Download]({audio_url})\n\n"
                f"_Tap the link to play or download the MP3_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔊 Open Audio", url=audio_url)],
                    [
                        InlineKeyboardButton("🎧 Other Reciters", callback_data=f"audio_menu:{surah_num}"),
                        InlineKeyboardButton("↩️ Surah", callback_data=f"surah:{surah_num}"),
                    ]
                ])
            )
        return

    # ── translation language menu
    if data.startswith("trans_menu:"):
        parts = data.split(":")
        surah_num = int(parts[1])
        page = int(parts[2])
        user_id = query.from_user.id
        surah = SURAH_BY_NUMBER[surah_num]
        await query.edit_message_text(
            f"🌍 *Translation Language*\n"
            f"_Surah {surah_num}: {surah[1]}_\n\n"
            f"Current: *{translation_label(user_id)}*\n"
            f"{len(TRANSLATIONS)} languages available — select one:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=translation_keyboard(surah_num, page, user_id)
        )
        return

    # ── set translation
    if data.startswith("set_trans:"):
        parts = data.split(":")
        surah_num = int(parts[1])
        trans_id = int(parts[2])
        user_id = query.from_user.id
        set_translation(user_id, trans_id)
        t = TRANSLATION_BY_ID.get(trans_id)
        label = f"{t[2]} {t[1]}" if t else "English"
        surah = SURAH_BY_NUMBER[surah_num]
        num, name_en, name_ar, ayahs, rev = surah
        badge = "🕌 Meccan" if rev == "Meccan" else "🌙 Medinan"
        await query.edit_message_text(
            f"🌿 *{name_ar}*\n"
            f"✨ *Surah {num} — {name_en}*\n"
            f"`{badge}` · `{ayahs} Ayahs`\n\n"
            f"_{BISMILLAH}_\n\n"
            f"Translation: *{label}* ✅\n"
            f"Script: _{script_label(user_id)}_\n"
            f"What would you like to do?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=surah_action_keyboard(num, user_id)
        )
        await query.answer(f"✅ {label} selected!", show_alert=False)
        return

    # ── reciter search prompt
    if data.startswith("reciter_search_prompt:"):
        surah_num = int(data.split(":")[1])
        user_id = query.from_user.id
        USER_RECITER_SEARCH[user_id] = surah_num
        surah = SURAH_BY_NUMBER[surah_num]
        await query.edit_message_text(
            f"🔍 *Search Reciter*\n"
            f"_Surah {surah_num}: {surah[1]}_\n\n"
            f"Type part of the reciter's name:\n"
            f"e.g. `mishary`, `basit`, `minshawi`, `luhaidan`\n\n"
            f"_Send your search as a message now_ 👇",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data=f"audio_menu:{surah_num}")]
            ])
        )
        return

    # ── PDF download
    if data.startswith("pdf:"):
        surah_num = int(data.split(":")[1])
        surah = SURAH_BY_NUMBER[surah_num]

        # Quran.com PDF link
        pdf_url = f"https://quran.com/surah/{surah_num}/download-surah-as-pdf"
        # Alternative: King Fahad complex PDFs
        kf_url = f"https://qurancomplex.gov.sa/Quran/En/surah/{str(surah_num).zfill(3)}.pdf"

        await query.edit_message_text(
            f"📥 *Download PDF*\n\n"
            f"📿 *Surah {surah_num}: {surah[1]}*\n"
            f"_{surah[2]}_\n\n"
            f"Choose your preferred source:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📥 Quran.com PDF",
                    url=f"https://quran.com/{surah_num}"
                )],
                [InlineKeyboardButton(
                    "📖 Read Online (quran.com)",
                    url=f"https://quran.com/{surah_num}"
                )],
                [InlineKeyboardButton(
                    "🌐 Global Quran (globalquran.com)",
                    url=f"https://globalquran.com/quran/{surah_num}"
                )],
                [InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")]
            ])
        )
        return

    # ── transliteration
    if data.startswith("translit:"):
        surah_num = int(data.split(":")[1])
        surah = SURAH_BY_NUMBER[surah_num]

        await query.edit_message_text(
            f"🔤 *Transliteration*\n\n"
            f"For *Surah {surah_num}: {surah[1]}*,\n"
            f"visit the link below for the full transliteration:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔤 Transliteration (quranwow.com)",
                    url=f"https://quranwow.com/#/ch/{surah_num}/t2"
                )],
                [InlineKeyboardButton(
                    "📖 Quran.com",
                    url=f"https://quran.com/{surah_num}"
                )],
                [InlineKeyboardButton("↩️ Back", callback_data=f"surah:{surah_num}")]
            ])
        )
        return

# ─────────────────────────────────────────────
#  BOT SETUP & RUN
# ─────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start",  "Welcome to Nur Al-Quran 🌿"),
        BotCommand("list",   "Browse all 114 Surahs 📚"),
        BotCommand("search", "Search a Surah by name or number 🔍"),
        BotCommand("random", "Open a random Surah 🎲"),
        BotCommand("lang",   "Change translation language 🌍"),
        BotCommand("juz",    "Juz (Para) guide 📖"),
        BotCommand("help",   "Help & commands ❓"),
    ])
    logger.info("✅ Nur Al-Quran Bot is running!")

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("list",   cmd_list))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("random", cmd_random))
    app.add_handler(CommandHandler("lang",   cmd_lang))
    app.add_handler(CommandHandler("juz",    cmd_juz))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🌿 Starting Nur Al-Quran Bot...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
