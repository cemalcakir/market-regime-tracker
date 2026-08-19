import datetime
import os
import requests

# ==========================================
# 1. SECURITY AND CONFIGURATION
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN:
    try:
        import config

        TELEGRAM_TOKEN = config.TELEGRAM_TOKEN
        TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
    except ImportError:
        print("Error: Credentials not found!")


def telegram_dispatch(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")


# ==========================================
# 2. ESTHETIC HEADER GENERATION
# ==========================================
import locale

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except:
    pass

date_str = datetime.datetime.now().strftime("%d %B %Y").upper()

separator = "=" * 24

message = (
    f"<code>{separator}</code>\n"
    f"<b>{date_str}</b>\n"
    f"<b>MARKET ANALYSIS BULLETIN</b>\n"
    f"<code>{separator}</code>"
)

# Dispatch
telegram_dispatch(message)
