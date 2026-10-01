import os
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
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
    except ImportError:
        print("Error: Telegram credentials not found!")

# ==========================================
# 2. WATCHLIST & STRATEGY CALCULATIONS
# ==========================================
# 5-Asset Global Macro Universe
TICKERS = ["SPY", "GLD", "TLT", "BTC-USD", "USO"]

print("--------------------------------------------------")
print(f"Fetching financial data for macro universe: {TICKERS}")
print("--------------------------------------------------\n")

# Download 1-year data for daily calculations
df_all = yf.download(TICKERS, period="1y", progress=False)

close_df = df_all["Close"].dropna()
open_df = df_all["Open"].dropna()

df = pd.DataFrame(index=close_df.index)

# Calculate indicators for each Asset
for ticker in TICKERS:
    df[ticker] = close_df[ticker]
    df[f"{ticker}_Open"] = open_df[ticker]
    df[f"{ticker}_SMA50"] = df[ticker].rolling(50).mean()
    df[f"{ticker}_ROC20"] = df[ticker].pct_change(20) * 100
    # Bull condition: Price > 50-day SMA AND 20-day momentum > +3.0%
    df[f"{ticker}_Bull"] = (df[ticker] > df[f"{ticker}_SMA50"]) & (
        df[f"{ticker}_ROC20"] > 3.0
    )

# Target Position Decision (Select strongest ROC20 bull asset, else CASH)
target_positions = []
for i in range(len(df)):
    bull_candidates = []
    for ticker in TICKERS:
        if df[f"{ticker}_Bull"].iloc[i]:
            roc_val = df[f"{ticker}_ROC20"].iloc[i]
            bull_candidates.append((ticker, roc_val))

    if bull_candidates:
        bull_candidates.sort(key=lambda x: x[1], reverse=True)
        target_positions.append(bull_candidates[0][0])
    else:
        target_positions.append("CASH")

df["Target_Position"] = target_positions
# Executed Position takes place on Next Open / Shifted by 1 day
df["Executed_Position"] = df["Target_Position"].shift(1).fillna("CASH")

# Dynamic Strategy Return Calculation
strat_ret = np.zeros(len(df))
for i in range(1, len(df)):
    exec_pos = df["Executed_Position"].iloc[i]
    if exec_pos in TICKERS:
        strat_ret[i] = df[exec_pos].pct_change().iloc[i]
    else:
        strat_ret[i] = 0.0

df["Strategy_Cum"] = (1 + pd.Series(strat_ret, index=df.index)).cumprod()

# ==========================================
# 3. CONSOLE DISPLAY
# ==========================================
last_row = df.iloc[-1]
today_signal = last_row["Target_Position"]
active_pos = last_row["Executed_Position"]
latest_date = df.index[-1].strftime("%Y-%m-%d")

print("==================================================")
print(f"       MACRO MOMENTUM ROTATION STATUS ({latest_date})")
print("==================================================")

if today_signal == active_pos:
    print(f"ACTION: HOLD {active_pos} POSITION 🟢")
else:
    print(
        f"ACTION: ROTATE CAPITAL FROM {active_pos} ➔ {today_signal} AT NEXT OPEN 🚨"
    )

print(f"\nActive Allocation : {active_pos}")
print(f"Target Allocation : {today_signal}")
print("--------------------------------------------------")
print("UNIVERSE METRICS:")

for ticker in TICKERS:
    price = last_row[ticker]
    sma = last_row[f"{ticker}_SMA50"]
    roc = last_row[f"{ticker}_ROC20"]
    is_bull = last_row[f"{ticker}_Bull"]
    bull_str = "YES" if is_bull else "NO"
    print(
        f"  • {ticker:9s} | Price: ${price:8.2f} | SMA50: ${sma:8.2f} | 20D Mom: {roc:6.1f}% | Bull: {bull_str}"
    )

print("--------------------------------------------------")
print(
    f"Strategy Cumulative Growth (1Y): {df['Strategy_Cum'].iloc[-1]:.2f}x ({(df['Strategy_Cum'].iloc[-1]-1)*100:.1f}%)"
)
print("==================================================\n")

# ==========================================
# 4. VISUALIZATION (3-PANEL DASHBOARD)
# ==========================================
plt.style.use("dark_background")
fig, (ax1, ax2, ax3) = plt.subplots(
    3, 1, figsize=(16, 11), sharex=True, gridspec_kw={"height_ratios": [2, 2, 1]}
)
fig.patch.set_facecolor("#0B0E11")
ax1.set_facecolor("#0B0E11")
ax2.set_facecolor("#0B0E11")
ax3.set_facecolor("#0B0E11")

# Color mapping for Macro Universe
color_map = {
    "SPY": "#00F2FF",      # Cyan (US Equities)
    "GLD": "#FFD700",      # Gold (Gold)
    "TLT": "#00FF7F",      # Spring Green (Treasuries)
    "BTC-USD": "#FF00FF",  # Magenta (Bitcoin)
    "USO": "#FF9900",      # Orange (Crude Oil)
    "CASH": "#FF0055",     # Neon Pink/Red (Cash)
}

# --- Panel 1: Strategy Equity Curve ---
ax1.plot(
    df.index,
    df["Strategy_Cum"],
    color="#00FF7F",
    lw=2.5,
    label="Macro Rotation Strategy Cumulative Return",
)
ax1.set_title(
    "1. STRATEGY EQUITY CURVE (PORTFOLIO GROWTH)",
    fontsize=11,
    pad=10,
    color="#00FF7F",
    loc="left",
    fontweight="bold",
)
ax1.grid(color="#1E222D", alpha=0.4, linestyle="--")
ax1.legend(loc="upper left")

# --- Panel 2: Asset Price Movements (Normalized to 100 for Comparison) ---
for ticker in TICKERS:
    norm_series = (df[ticker] / df[ticker].iloc[0]) * 100
    ax2.plot(
        df.index,
        norm_series,
        color=color_map[ticker],
        lw=1.3,
        alpha=0.85,
        label=f"{ticker} (Rebased to 100)",
    )
ax2.set_title(
    "2. RELATIVE ASSET PERFORMANCE (REBASED TO 100)",
    fontsize=11,
    pad=10,
    color="white",
    loc="left",
    fontweight="bold",
)
ax2.grid(color="#1E222D", alpha=0.4, linestyle="--")
ax2.legend(loc="upper left")

# --- Panel 3: Position Timeline (Rotation Map) ---
for ticker in TICKERS + ["CASH"]:
    mask = df["Executed_Position"] == ticker
    ax3.fill_between(
        df.index,
        0,
        1,
        where=mask,
        color=color_map[ticker],
        alpha=0.6,
        label=f"{ticker}",
    )

ax3.set_title(
    "3. HISTORICAL ASSET ALLOCATION TIMELINE (MACRO ROTATION MAP)",
    fontsize=11,
    pad=10,
    color="gray",
    loc="left",
    fontweight="bold",
)
ax3.set_yticks([])
ax3.grid(color="#1E222D", alpha=0.3, linestyle="--")
ax3.legend(loc="upper left", ncol=6)

ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

plt.tight_layout()

output_file = "macro_rotation.png"
plt.savefig(output_file, facecolor=fig.get_facecolor(), dpi=150)
plt.close()


# ==========================================
# 5. TELEGRAM DISPATCH
# ==========================================
def send_telegram_message(message, file_path=None):
    if not TOKEN or not CHAT_ID:
        print("Telegram credentials missing, skipping message dispatch...")
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
        print("Telegram notification successfully sent.")
    except Exception as e:
        print(f"Telegram Error: {e}")


# Construct Telegram Notification Text
if today_signal == active_pos:
    action_text = f"<b>ACTION:</b> HOLD {active_pos} POSITION 🟢"
    description = (
        f"Momentum leadership maintained. Capital stays 100% in {active_pos}."
        if active_pos != "CASH"
        else "No bull criteria met across macro universe. Capital stays 100% in CASH."
    )
else:
    action_text = f"<b>ACTION:</b> ROTATE CAPITAL FROM {active_pos} ➔ {today_signal} AT NEXT OPEN 🚨"
    description = f"Macro leader shift detected! Rebalance capital to {today_signal} at the next market open."

metrics_text = ""
for ticker in TICKERS:
    price = last_row[ticker]
    sma = last_row[f"{ticker}_SMA50"]
    roc = last_row[f"{ticker}_ROC20"]
    is_bull = last_row[f"{ticker}_Bull"]
    status_str = "YES 🟢" if is_bull else "NO 🔴"
    metrics_text += f"• <b>{ticker}:</b> ${price:.2f} | SMA50: ${sma:.2f} | 20D Mom: {roc:.1f}% | Bull: {status_str}\n"

message = (
    f"🌍 <b>GLOBAL MACRO MOMENTUM ROTATION SIGNAL</b>\n\n"
    f"{action_text}\n"
    f"<b>Description:</b> {description}\n\n"
    f"📌 <b>Active Allocation:</b> {active_pos}\n"
    f"🎯 <b>Target Allocation:</b> {today_signal}\n\n"
    f"📋 <b>UNIVERSE METRICS:</b>\n"
    f"{metrics_text}\n"
    f"📈 <b>1Y Strategy Performance:</b> {df['Strategy_Cum'].iloc[-1]:.2f}x ({(df['Strategy_Cum'].iloc[-1]-1)*100:.1f}%)"
)

send_telegram_message(message, output_file)