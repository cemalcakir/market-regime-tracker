from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# GRAFİK PENCERESİ AÇILMASINI ENGELLER
plt.switch_backend('Agg')

# ==========================================
# 1. KİMLİK VE ZAMAN AYARLARI
# ==========================================
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TOKEN or not CHAT_ID:
    try:
        import config
        TOKEN = config.TELEGRAM_TOKEN
        CHAT_ID = config.TELEGRAM_CHAT_ID
    except ImportError:
        pass

ANALYSIS_PERIOD_DAYS = 540
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=ANALYSIS_PERIOD_DAYS)

STOCK_SETTINGS = {
    "TUPRS.IS": {"name": "Tüpraş", "upper_threshold": 0.22, "lower_threshold": -0.05, "rsi_upper": 75, "rsi_lower": 32},
    "ASELS.IS": {"name": "Aselsan", "upper_threshold": 0.45, "lower_threshold": -0.08, "rsi_upper": 85, "rsi_lower": 26},
    "THYAO.IS": {"name": "THY", "upper_threshold": 0.25, "lower_threshold": -0.05, "rsi_upper": 75, "rsi_lower": 30}
}

# ==========================================
# 2. ANALİZ MOTORU
# ==========================================
def determine_status(row, setting, use_emoji=True):
    deviation, rsi = row['Deviation'], row['RSI']
    e = {"gsat": "🚨 " if use_emoji else "", "ksat": "💰 " if use_emoji else "",
         "gal": "💎 " if use_emoji else "", "fal": "🎯 " if use_emoji else "", "izle": "⏳ " if use_emoji else ""}
    
    if deviation > setting['upper_threshold'] and rsi > setting['rsi_upper']: return f"{e['gsat']}STRONG SELL"
    if deviation > (setting['upper_threshold'] * 0.8) or rsi > (setting['rsi_upper'] * 0.9): return f"{e['ksat']}TAKE PROFIT"
    if deviation < setting['lower_threshold'] and rsi < setting['rsi_lower']: return f"{e['gal']}STRONG BUY"
    if rsi < (setting['rsi_lower'] * 1.25): return f"{e['fal']}DIP BUY"
    return f"{e['izle']}MONITOR"

def analyze_and_send(ticker, usd_data, setting):
    try:
        raw = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if raw.empty: return
        if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
        
        common = raw.index.intersection(usd_data.index)
        df = pd.DataFrame(index=common)
        df['Close'] = raw.loc[common, 'Close'] / usd_data.loc[common, 'Close']
        
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['Deviation'] = (df['Close'] / df['EMA200']) - 1
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))

        last_row = df.iloc[-1]
        
        # Signal Points
        df['g_al'] = (df['Deviation'] < setting['lower_threshold']) & (df['RSI'] < setting['rsi_lower'])
        df['f_al'] = (df['RSI'] < (setting['rsi_lower'] * 1.25)) & (~df['g_al'])
        df['g_sat'] = (df['Deviation'] > setting['upper_threshold']) & (df['RSI'] > setting['rsi_upper'])
        df['k_sat'] = (df['Deviation'] > (setting['upper_threshold'] * 0.8)) & (~df['g_sat'])

        current_status_msg = determine_status(last_row, setting, use_emoji=True)
        current_status_plt = determine_status(last_row, setting, use_emoji=False)

        # PLOT PREPARATION
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]}, facecolor='#0B0E11')
        ax1.set_facecolor('#0B0E11')
        ax1.plot(df.index, df['Close'], color='white', alpha=0.8, label='Price (USD)')
        ax1.plot(df.index, df['EMA200'], color='magenta', lw=2.5, ls='--', alpha=0.7, label='EMA 200')
        
        S_SIZE = 130
        ax1.scatter(df[df['g_al']].index, df[df['g_al']]['Close'], marker='^', color='#00FFFF', s=S_SIZE+50, label='STRONG BUY', zorder=5)
        ax1.scatter(df[df['f_al']].index, df[df['f_al']]['Close'], marker='^', color='#00FF41', s=S_SIZE, label='DIP BUY', zorder=4)
        ax1.scatter(df[df['k_sat']].index, df[df['k_sat']]['Close'], marker='v', color='#FFD700', s=S_SIZE, label='TAKE PROFIT', zorder=4)
        ax1.scatter(df[df['g_sat']].index, df[df['g_sat']]['Close'], marker='v', color='#FF3131', s=S_SIZE+50, label='STRONG SELL', zorder=5)
        
        ax1.legend(loc='upper left', frameon=True, facecolor='#151924', edgecolor='gray')
        ax1.set_title(f"{setting['name']} - {current_status_plt}", color='gold', fontsize=16, fontweight='bold')
        
        ax2.set_facecolor('#0B0E11')
        ax2.plot(df.index, df['RSI'], color='cyan', lw=1.2)
        ax2.axhline(setting['rsi_upper'], color='red', ls='--', alpha=0.4)
        ax2.axhline(setting['rsi_lower'], color='green', ls='--', alpha=0.4)
        
        filename = f"{ticker}.png"
        plt.tight_layout()
        plt.savefig(filename, facecolor='#0B0E11')
        plt.close(fig)

        # SINGLE MESSAGE DISPATCH (Text + Image)
        if TOKEN and CHAT_ID:
            clean_ticker = ticker.split('.')[0]
            message = (f"<b>{setting['name']} ({clean_ticker}) Analysis Report</b>\n\n"
                       f"Status: {current_status_msg}\n"
                       f"Price: ${last_row['Close']:.2f}\n"
                       f"EMA200 Deviation: %{last_row['Deviation']*100:+.1f}\n"
                       f"RSI: {last_row['RSI']:.1f}")
            
            with open(filename, 'rb') as photo:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                            data={'chat_id': CHAT_ID, 'caption': message, 'parse_mode': 'HTML', 'show_caption_above_media': True}, 
                            files={'photo': photo})
        
        if os.path.exists(filename): os.remove(filename)
        print(f"Completed: {ticker}")

    except Exception as e:
        print(f"Error {ticker}: {e}")

# ==========================================
# 3. RUNNER
# ==========================================
if __name__ == "__main__":
    usd_raw = yf.download("USDTRY=X", start=START_DATE, end=END_DATE, progress=False)
    if isinstance(usd_raw.columns, pd.MultiIndex): usd_raw.columns = usd_raw.columns.get_level_values(0)

    for ticker, setting in STOCK_SETTINGS.items():
        analyze_and_send(ticker, usd_raw, setting)
