from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# Ortak AI servis kulanımı için import
from ai_service import MarketAIAnalyst

# ==========================================
# 1. CREDENTIALS MANAGEMENT
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if TOKEN is None or CHAT_ID is None:
    try:
        import config
        TOKEN = config.TELEGRAM_TOKEN
        CHAT_ID = config.TELEGRAM_CHAT_ID
    except:
        print("Error: Credentials not found!")

# ==========================================
# 2. DATA FETCHING & CALCULATIONS
# ==========================================

def get_ideal_indicators(data):
    d = data.copy()
    n = 14
    # ADX Calculation
    d["H-L"] = d["High"] - d["Low"]
    d["TR"] = np.maximum(
        d["H-L"],
        np.maximum(
            abs(d["High"] - d["Close"].shift(1)),
            abs(d["Low"] - d["Close"].shift(1)),
        ),
    )
    d["+DM"] = np.where(
        (d["High"] - d["High"].shift(1)) > (d["Low"].shift(1) - d["Low"]),
        np.maximum(d["High"] - d["High"].shift(1), 0),
        0,
    )
    d["-DM"] = np.where(
        (d["Low"].shift(1) - d["Low"]) > (d["High"] - d["High"].shift(1)),
        np.maximum(d["Low"].shift(1) - d["Low"], 0),
        0,
    )
    d["TRn"] = d["TR"].rolling(n).sum()
    d["+DMn"] = d["+DM"].rolling(n).sum()
    d["-DMn"] = d["-DM"].rolling(n).sum()
    d["ADX"] = (
        100
        * (
            abs(
                (d["+DMn"] - d["-DMn"]) / (d["+DMn"] + d["-DMn"] + 0.001)
            )
        ).rolling(n)
        .mean()
    )
    
    # RSI & Bollinger Bands
    d["EMA20"] = d["Close"].ewm(span=20, adjust=False).mean()
    delta = d["Close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["RSI"] = 100 - (100 / (1 + (gain / (loss + 0.001))))
    d["STD"] = d["Close"].rolling(20).std()
    d["Upper"] = d["EMA20"] + (d["STD"] * 2.1)
    d["Lower"] = d["EMA20"] - (d["STD"] * 2.1)
    
    # Signals (Duyarlı ve esnek koşullar)
    d["buy"] = (d["Close"] <= d["Lower"]) | ((d["RSI"] < 40) & (d["Close"] <= d["EMA20"] * 1.02))
    d["sell"] = (d["Close"] >= d["Upper"]) | (d["RSI"] > 75)
    return d


df = yf.download("BTC-USD", period="1y", interval="1d", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# (İndikatör hesaplama fonksiyonun aynı kalıyor...)
full_df = get_ideal_indicators(df)
last = full_df.iloc[-1]


# ==========================================
# 3. AI STRATEGIST COMMENTARY (ORTAK SERVİS ÇAĞRISI)
# ==========================================
status_emoji = "⚪️"
if last["buy"]:
    status_emoji = "🟢"
elif last["sell"]:
    status_emoji = "🔴"
elif last["ADX"] > 30:
    status_emoji = "🌪"
else:
    status_emoji = "⚖️"

# Metrikleri ortak servise göndermek için bir sözlükte topluyoruz
metrics_data = {
    "Close Price": float(last['Close']),
    "RSI": float(last['RSI']),
    "ADX": float(last['ADX']),
    "EMA20 (BB Middle)": float(last['EMA20']),
    "Upper Band": float(last['Upper']),
    "Lower Band": float(last['Lower']),
    "Buy Signal Triggered": bool(last['buy']),
    "Sell Signal Triggered": bool(last['sell'])
}

# Ortak servisi başlat ve yorumu al
ai_analyst = MarketAIAnalyst()
bot_comment = ai_analyst.generate_commentary("Bitcoin (BTC)", metrics_data)

telegram_msg = f"""
{status_emoji} <b>BITCOIN DAILY REPORT</b> ({full_df.index[-1].strftime('%d.%m.%Y')})

💰 <b>Price:</b> ${last['Close']:,.0f}
📊 <b>RSI:</b> {last['RSI']:.1f}
📉 <b>ADX:</b> {last['ADX']:.1f}
📏 <b>BB Middle:</b> ${last['EMA20']:,.0f}

🧠 <b>AI Strategist Commentary:</b>
<i>{bot_comment}</i>
"""

# (Grafik çizme ve telegram_dispatch kısıtları aynı kalıyor...)