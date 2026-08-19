import os
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
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
# 2. DATASET & RATIO CALCULATIONS
# ==========================================
symbol_a = "XLI"
symbol_b = "XLU"

print("Fetching financial data...")
df_a = yf.download(symbol_a, start="2024-01-01", progress=False)
df_b = yf.download(symbol_b, start="2024-01-01", progress=False)

if isinstance(df_a.columns, pd.MultiIndex):
    df_a.columns = df_a.columns.get_level_values(0)
if isinstance(df_b.columns, pd.MultiIndex):
    df_b.columns = df_b.columns.get_level_values(0)

df = pd.DataFrame(index=df_a.index)
df["Close"] = df_a["Close"] / df_b["Close"]
df.dropna(inplace=True)

# Technical Indicators (EMAs, RSI, and Bollinger Bands)
df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

# RSI Calculation
delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
df["RSI"] = 100 - (100 / (1 + (gain / loss)))

# Bollinger Bands
df["BB_Middle"] = df["Close"].rolling(window=20).mean()
df["BB_Std"] = df["Close"].rolling(window=20).std()
df["BB_Upper"] = df["BB_Middle"] + (df["BB_Std"] * 2.0)
df["BB_Lower"] = df["BB_Middle"] - (df["BB_Std"] * 2.0)

# Signal Columns
df["strong_sell"] = (df["Close"] >= df["BB_Upper"]) & (df["RSI"] > 70)
df["strong_buy"] = (df["Close"] <= df["BB_Lower"]) & (df["RSI"] < 30)
df["dip_buy"] = df["RSI"] < 25

# Latest Data Points
last_ratio = df["Close"].iloc[-1]
last_rsi = df["RSI"].iloc[-1]
last_ema200 = df["EMA200"].iloc[-1]
last_bb_upper = df["BB_Upper"].iloc[-1]
last_bb_lower = df["BB_Lower"].iloc[-1]

# Color Logic for RSI
if last_rsi > 70 or last_rsi < 30:
    rsi_color = "#FF4444"
elif 60 <= last_rsi <= 70 or 30 <= last_rsi <= 40:
    rsi_color = "#FFCC00"
else:
    rsi_color = "#AAAAAA"

# ==========================================
# 3. VISUALIZATION (NEON STYLE DASHBOARD)
# ==========================================
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(16, 9), facecolor="#0B0E11")
ax.set_facecolor("#0B0E11")

d_plot = df.tail(250).copy()

# 1. Lines and Bands
ax.plot(d_plot.index, d_plot["EMA20"], color="#00F2FF", lw=1.5, alpha=0.8)
ax.plot(d_plot.index, d_plot["EMA50"], color="#FFCC00", lw=1.5, alpha=0.8)
ax.plot(d_plot.index, d_plot["EMA200"], color="#FF00FF", lw=2.0, alpha=0.8)

# Bollinger Bands Plotting
ax.plot(
    d_plot.index,
    d_plot["BB_Upper"],
    color="#FF4444",
    lw=1.0,
    ls="--",
    alpha=0.5,
)
ax.plot(
    d_plot.index,
    d_plot["BB_Lower"],
    color="#00FF41",
    lw=1.0,
    ls="--",
    alpha=0.5,
)
ax.fill_between(
    d_plot.index,
    d_plot["BB_Upper"],
    d_plot["BB_Lower"],
    color="#1E222D",
    alpha=0.3,
)

# Main Ratio Line
ratio_line = ax.plot(
    d_plot.index, d_plot["Close"], color="#FFFFFF", lw=2.2, zorder=5
)[0]
ratio_line.set_path_effects([
    path_effects.Stroke(linewidth=4, foreground="white", alpha=0.3),
    path_effects.Normal(),
])

# 2. Signals
ax.scatter(
    d_plot.index[d_plot["dip_buy"]],
    d_plot.loc[d_plot["dip_buy"], "Close"],
    marker="^",
    color="#BC13FE",
    s=200,
    edgecolors="white",
    linewidth=1.5,
    zorder=6,
)
ax.scatter(
    d_plot.index[d_plot["strong_buy"]],
    d_plot.loc[d_plot["strong_buy"], "Close"],
    marker="^",
    color="#00FF41",
    s=180,
    edgecolors="white",
    linewidth=1.5,
    zorder=6,
)
ax.scatter(
    d_plot.index[d_plot["strong_sell"]],
    d_plot.loc[d_plot["strong_sell"], "Close"],
    marker="o",
    color="#FF4444",
    s=180,
    edgecolors="white",
    linewidth=1.5,
    zorder=6,
)

# --- DASHBOARD OVERLAY ---
x_pos = 0.02
y_start = 0.95
gap = 0.035

ax.text(
    x_pos,
    y_start,
    f"XLI/XLU RATIO: {last_ratio:.3f}",
    transform=ax.transAxes,
    color="#FFFFFF",
    fontweight="bold",
    fontsize=13,
)
ax.text(
    x_pos,
    y_start - gap,
    f"RSI: {last_rsi:.2f}",
    transform=ax.transAxes,
    color=rsi_color,
    fontweight="bold",
    fontsize=12,
)

guide_y_start = y_start - gap * 3
ax.text(
    x_pos,
    guide_y_start,
    "EMA20 (SHORT)",
    transform=ax.transAxes,
    color="#00F2FF",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap,
    "EMA50 (MID)",
    transform=ax.transAxes,
    color="#FFCC00",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap * 2,
    "EMA200 (MAIN)",
    transform=ax.transAxes,
    color="#FF00FF",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap * 3.5,
    "▲ DIP (XLI ROTATION)",
    transform=ax.transAxes,
    color="#00FF41",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap * 4.5,
    "● PEAK (XLU ROTATION)",
    transform=ax.transAxes,
    color="#FF4444",
    fontweight="bold",
    fontsize=10,
)

ax.grid(color="#1E222D", alpha=0.4, linestyle="--")
plt.tight_layout()

output_file = "ratio_analysis.png"
plt.savefig(output_file, facecolor=fig.get_facecolor())
plt.close()


# ==========================================
# 4. TELEGRAM DISPATCH
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


# Dynamic Text Management
if df["strong_sell"].iloc[-1]:
    status = "ROTATION TO XLU (Peak Saturation)"
    description = (
        "Ratio is at the upper Bollinger band and RSI is overbought. "
        "Consider taking profits on XLI and shifting to defensive XLU."
    )
elif df["strong_buy"].iloc[-1] or df["dip_buy"].iloc[-1]:
    status = "ROTATION TO XLI (Dip Opportunity)"
    description = (
        "Ratio is at the lower Bollinger band and RSI is oversold. "
        "An opportunity to rotate into Industrials (XLI) may arise."
    )
else:
    status = "HOLD / MONITOR"
    description = (
        "No overbought or oversold signals triggered. Current intermarket trend remains intact."
    )

regime = (
    "Risk-On (Industrial Leadership) 🟢"
    if last_ratio > last_ema200
    else "Risk-Off (Utilities Leadership) 🔴"
)
rsi_note = (
    "overbought (industrials saturated)"
    if last_rsi > 70
    else (
        "oversold (utilities saturated)"
        if last_rsi < 30
        else "neutral zone"
    )
)

message = (
    f"🇺🇸 <b>SECTOR ROTATION (XLI / XLU) ANALYSIS</b>\n\n"
    f"<b>Status:</b>  {status}\n"
    f"<b>Market Regime:</b>  {regime}\n\n"
    f"{description}\n\n"
    f"💰 <b>Current Ratio:</b>  {last_ratio:.4f}\n"
    f"📊 <b>RSI (14):</b>  {last_rsi:.1f} : {rsi_note}\n"
    f"🎯 <b>Bollinger Upper / Lower:</b>  {last_bb_upper:.3f} / {last_bb_lower:.3f}"
)

send_telegram_message(message, output_file)
