from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import pandas as pd
import requests
import yfinance as yf

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
        print("Error: Telegram credentials not found!")

# ==========================================
# 2. DATA FETCHING & CALCULATIONS
# ==========================================
df = yf.download("BTC-USD", period="1y", interval="1d", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)


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
    # Signals
    d["buy"] = (d["ADX"] < 30) & (d["Close"] < d["Lower"]) & (d["RSI"] < 35)
    d["sell"] = (d["ADX"] < 30) & (d["Close"] > d["Upper"]) & (d["RSI"] > 70)
    return d


full_df = get_ideal_indicators(df)
last = full_df.iloc[-1]

# ==========================================
# 3. MESSAGE & VISUALIZATION
# ==========================================
status_emoji = "⚪️"
bot_comment = ""

if last["buy"]:
    status_emoji = "🟢"
    bot_comment = (
        "SIGNAL: BUY! The market is in a 'capitulation' (dip) zone. "
        "The bot enters the game while everyone is panicking."
    )
elif last["sell"]:
    status_emoji = "🔴"
    bot_comment = (
        "SIGNAL: SELL! The market has reached 'euphoria' (peak) levels. "
        "Time to realize profits."
    )
elif last["ADX"] > 30:
    status_emoji = "🌪"
    bot_comment = (
        f"COMMENT: Strong trend in play (ADX: {last['ADX']:.1f}). "
        "Do not swim against the current. Stay on monitor mode."
    )
else:
    status_emoji = "⚖️"
    bot_comment = (
        "COMMENT: Neither capitulation nor euphoria. "
        "The market is trying to decide on a direction. Avoid the noise."
    )

telegram_msg = f"""
{status_emoji} <b>BITCOIN DAILY REPORT</b> ({full_df.index[-1].strftime('%d.%m.%Y')})

💰 <b>Price:</b> ${last['Close']:,.0f}
📊 <b>RSI:</b> {last['RSI']:.1f}
📉 <b>ADX:</b> {last['ADX']:.1f}
📏 <b>BB Middle:</b> ${last['EMA20']:,.0f}

📝 <b>Bot Comment:</b>
<i>{bot_comment}</i>
"""

# Plotting
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(16, 8), facecolor="#0B0E11")
ax.set_facecolor("#0B0E11")

ax.plot(
    full_df.index, full_df["Close"], color="#F7931A", lw=2, label="Bitcoin"
)
ax.fill_between(
    full_df.index,
    full_df["Lower"],
    full_df["Upper"],
    color="#00F2FF",
    alpha=0.07,
    label="Vapor Band",
)
ax.plot(
    full_df.index,
    full_df["EMA20"],
    color="white",
    lw=1,
    ls="--",
    alpha=0.3,
    label="BB Middle (EMA20)",
)

buys = full_df[full_df["buy"]]
sells = full_df[full_df["sell"]]
ax.scatter(
    buys.index,
    buys["Close"],
    marker="^",
    color="#00FF41",
    s=200,
    zorder=5,
    label="BUY Signal",
)
ax.scatter(
    sells.index,
    sells["Close"],
    marker="v",
    color="#FF4444",
    s=200,
    zorder=5,
    label="SELL Signal",
)

ax.set_yscale("log")
ax.yaxis.set_major_formatter(ScalarFormatter())
ax.set_title(
    f"Bitcoin Analysis Terminal - {full_df.index[-1].strftime('%d %B %Y')}",
    fontsize=16,
    fontweight="bold",
)
ax.legend(loc="upper left")
ax.grid(alpha=0.1)
plt.tight_layout()

output_file = "btc_analysis.png"
plt.savefig(output_file, facecolor=fig.get_facecolor())
plt.close()


# ==========================================
# 4. TELEGRAM DISPATCH
# ==========================================
def telegram_dispatch(message, file_path=None):
    if not TOKEN or not CHAT_ID:
        print("Error: Credentials missing!")
        return

    base_url = f"https://api.telegram.org/bot{TOKEN}"
    try:
        requests.post(
            f"{base_url}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
        )
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": CHAT_ID},
                    files={"photo": f},
                )
    except Exception as e:
        print(f"Dispatch error: {e}")


# Run
telegram_dispatch(telegram_msg, output_file)
