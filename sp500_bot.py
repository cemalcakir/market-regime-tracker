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
    except:
        print("Error: Telegram credentials not found!")

# ==========================================
# 2. DATASET & CALCULATIONS
# ==========================================
symbol = "^GSPC"
df = yf.download(symbol, start="2024-01-01", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df.dropna(inplace=True)

# Indicators
df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / 14, adjust=False).mean()
df["RSI"] = 100 - (100 / (1 + (gain / loss)))

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

# Signal Columns
df["dip_buy"] = df["RSI"] < 25
df["strong_buy"] = (
    (df["Close"] > df["EMA200"])
    & (df["RSI"] < 45)
    & (df["Close"] <= df["EMA20"] * 1.01)
    & (df["ADX"] > 20)
)
df["strong_sell"] = df["RSI"] > 75

# Latest Data
last_price = df["Close"].iloc[-1]
last_rsi = df["RSI"].iloc[-1]
last_adx = df["ADX"].iloc[-1]
last_ema200 = df["EMA200"].iloc[-1]

# Color Logic for Dashboard
if last_rsi > 70 or last_rsi < 30:
    rsi_color = "#FF4444"
elif 60 <= last_rsi <= 70 or 30 <= last_rsi <= 40:
    rsi_color = "#FFCC00"
else:
    rsi_color = "#AAAAAA"

if last_adx > 30:
    adx_color = "#FF4444"
elif 20 <= last_adx <= 30:
    adx_color = "#FFCC00"
else:
    adx_color = "#AAAAAA"

# ==========================================
# 3. VISUALIZATION (CLEAN & VIBRANT)
# ==========================================
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(16, 9), facecolor="#0B0E11")
ax.set_facecolor("#0B0E11")

d_plot = df.tail(250).copy()

# 1. Lines: Neon Effect
ax.plot(d_plot.index, d_plot["EMA20"], color="#00F2FF", lw=1.5, alpha=0.8)
ax.plot(d_plot.index, d_plot["EMA50"], color="#FFCC00", lw=1.5, alpha=0.8)
ax.plot(d_plot.index, d_plot["EMA200"], color="#FF00FF", lw=2.0, alpha=0.8)
price_line = ax.plot(
    d_plot.index, d_plot["Close"], color="#FFFFFF", lw=2.2, zorder=5
)[0]
price_line.set_path_effects(
    [
        path_effects.Stroke(linewidth=4, foreground="white", alpha=0.3),
        path_effects.Normal(),
    ]
)

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

# --- DASHBOARD ---
x_pos = 0.02
y_start = 0.95
gap = 0.035

ax.text(
    x_pos,
    y_start,
    f"PRICE: {last_price:.2f}",
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
ax.text(
    x_pos,
    y_start - gap * 2,
    f"ADX: {last_adx:.2f}",
    transform=ax.transAxes,
    color=adx_color,
    fontweight="bold",
    fontsize=12,
)

guide_y_start = y_start - gap * 4
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
    "▲ RISKY DIP",
    transform=ax.transAxes,
    color="#BC13FE",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap * 4.5,
    "▲ SECURE BUY",
    transform=ax.transAxes,
    color="#00FF41",
    fontweight="bold",
    fontsize=10,
)
ax.text(
    x_pos,
    guide_y_start - gap * 5.5,
    "● STRONG SELL",
    transform=ax.transAxes,
    color="#FF4444",
    fontweight="bold",
    fontsize=10,
)

ax.grid(color="#1E222D", alpha=0.4, linestyle="--")
plt.tight_layout()
output_file = "analiz_vurgulu.png"
plt.savefig(output_file, facecolor=fig.get_facecolor())
plt.close()

# ==========================================
# 4. TELEGRAM DISPATCH
# ==========================================
def telegram_dispatch(mesaj, dosya_yolu=None):
    if not TOKEN or not CHAT_ID:
        return
    base_url = f"https://api.telegram.org/bot{TOKEN}"
    try:
        requests.post(
            f"{base_url}/sendMessage",
            data={"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "HTML"},
        )
        if dosya_yolu and os.path.exists(dosya_yolu):
            with open(dosya_yolu, "rb") as f:
                requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": CHAT_ID},
                    files={"photo": f},
                )
    except Exception as e:
        print(f"Telegram Error: {e}")


# Dynamic Variables for Message
status = (
    "STRATEGIC BUY"
    if (df["strong_buy"].iloc[-1] or df["dip_buy"].iloc[-1])
    else ("FULL EXIT" if df["strong_sell"].iloc[-1] else "HOLD / MONITOR")
)
regime = "Bull Regime 🟢" if last_price > last_ema200 else "Bear Regime 🔴"
description = (
    "No new signal triggered. Current trend is being tracked."
    if status == "HOLD / MONITOR"
    else "Signal conditions met."
)

rsi_note = (
    "weak rsi (room for entry)"
    if last_rsi < 50
    else "strong rsi (cooling expected)"
)
adx_note = (
    "strong index (trend is steady)"
    if last_adx > 20
    else "weak index (market undecided)"
)

mesaj = (
    f"🇺🇸 <b>S&P 500 (SPX) ANALYSIS REPORT</b>\n\n"
    f"<b>Status:</b>  {status}\n"
    f"<b>Market Regime:</b>  {regime}\n\n"
    f"{description}\n\n"
    f"💰 <b>Price:</b>  ${last_price:.2f}\n"
    f"📊 <b>RSI:</b>  {last_rsi:.1f} : {rsi_note}\n"
    f"📈 <b>ADX:</b>  {last_adx:.1f} : {adx_note}"
)

telegram_dispatch(mesaj, output_file)
