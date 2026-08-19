from datetime import datetime
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

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


def telegram_dispatch(message, chart_path=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        requests.post(url, data=payload)
        if chart_path and os.path.exists(chart_path):
            url2 = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(chart_path, "rb") as f:
                requests.post(
                    url2,
                    data={"chat_id": TELEGRAM_CHAT_ID},
                    files={"photo": f},
                )
    except Exception as e:
        print(f"Telegram Error: {e}")


# ==========================================
# 2. STRATEGY CALCULATION
# ==========================================
symbol = "GC=F"
df = yf.download(symbol, start="2024-01-01", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df.dropna(inplace=True)


def analyze_data(df):
    df = df.copy()
    # Indicators (EMA20 and EMA200)
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss)))

    # ADX
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            abs(df["High"] - df["Close"].shift(1)),
            abs(df["Low"] - df["Close"].shift(1)),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    plus_di = (
        100
        * (
            df["High"].diff().clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
            / atr
        )
    )
    minus_di = (
        100
        * (
            (-df["Low"].diff())
            .clip(lower=0)
            .ewm(alpha=1 / 14, adjust=False)
            .mean()
            / atr
        )
    )
    df["ADX"] = (
        (100 * abs(plus_di - minus_di) / (plus_di + minus_di))
        .ewm(alpha=1 / 14, adjust=False)
        .mean()
    )

    # Signal Logic
    df["buy"] = (df["Close"] > df["EMA200"]) & (df["RSI"] < 50) & (df["ADX"] > 20)
    c1 = (df["Close"] < df["EMA20"] * 0.975) & (df["RSI"] > 65)
    c2 = (df["Close"] > df["EMA20"] * 1.055) & (df["RSI"] > 75)
    df["s_sell"] = c1 | c2
    return df


df_final = analyze_data(df)
last = df_final.iloc[-1]

# ==========================================
# 3. MESSAGE CONTENT (ICONS & FORMATTING)
# ==========================================
status = (
    "STRATEGIC BUY"
    if last["buy"]
    else "FULL EXIT"
    if last["s_sell"]
    else "HOLD / MONITOR"
)

# Regime Indicator
if last["Close"] > last["EMA200"]:
    regime = "Bull Regime 🟢"
else:
    regime = "Bear Regime 🔴"

description = (
    "No new signal triggered. Current trend is being tracked."
    if status == "HOLD / MONITOR"
    else "Signal conditions met."
)

rsi_note = (
    "weak rsi (price pulled back, room for entry)"
    if last["RSI"] < 50
    else "strong rsi (buyers dominant, cooling expected)"
)
adx_note = (
    "strong index (trend is steady and robust)"
    if last["ADX"] > 20
    else "weak index (market undecided or sideways)"
)

mesaj = (
    f"🟡 <b>GOLD ANALYSIS REPORT</b>\n\n"
    f"<b>Status:</b>  {status}\n"
    f"<b>Market Regime:</b>  {regime}\n\n"
    f"{description}\n\n"
    f"💰 <b>Price:</b>  ${last['Close']:.2f}\n"
    f"📊 <b>RSI:</b>  {last['RSI']:.1f} : {rsi_note}\n"
    f"📈 <b>ADX:</b>  {last['ADX']:.1f} : {adx_note}"
)

# ==========================================
# 4. PLOTTING (PRO FORMAT)
# ==========================================
plt.style.use("dark_background")
plt.figure(figsize=(16, 9), facecolor="#0B0E11")
ax = plt.gca()
ax.set_facecolor("#0B0E11")

# Lines
plt.plot(
    df_final.index,
    df_final["Close"],
    color="#E1B31E",
    lw=2,
    label="Gold Futures",
    zorder=1,
)
plt.plot(
    df_final.index,
    df_final["EMA20"],
    color="#00F2FF",
    lw=1.2,
    alpha=0.7,
    label="EMA20",
    zorder=2,
)
plt.plot(
    df_final.index,
    df_final["EMA200"],
    color="#FF00FF",
    lw=1.5,
    ls="--",
    alpha=0.5,
    label="EMA200",
    zorder=2,
)

# Signals
plt.scatter(
    df_final[df_final["buy"]].index,
    df_final[df_final["buy"]]["Close"],
    marker="^",
    color="#00FF41",
    s=150,
    label="BUY (RSI 50 Pullback)",
    zorder=5,
)

plt.scatter(
    df_final[df_final["s_sell"]].index,
    df_final[df_final["s_sell"]]["Close"],
    marker="o",
    color="#FF4444",
    s=200,
    edgecolors="white",
    lw=2,
    label="FULL EXIT",
    zorder=6,
)

plt.title(
    "SPOT GOLD: BALANCED BULL STRATEGY (RSI 50 & 0.975 MARGIN)",
    fontsize=14,
    pad=20,
)
plt.grid(color="#1E222D", alpha=0.2, zorder=0)
plt.legend(
    loc="upper left", frameon=True, facecolor="#0B0E11", edgecolor="#1E222D"
)
plt.tight_layout()

report_path = "gold_final_clean.png"
plt.savefig(report_path, dpi=150)
plt.close()

telegram_dispatch(mesaj, report_path)
