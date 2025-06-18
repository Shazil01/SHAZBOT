import time
import requests
import pandas as pd
import numpy as np
import talib
from quotexapi import QuotexAPI  # (Use a Quotex API wrapper)

# ======================
# BOT CONFIGURATION
# ======================
PAIR = "EUR/USD"  # Default pair (can be BTC/USD, GOLD, etc.)
TIMEFRAME = 1  # 1-minute candles
RISK_PER_TRADE = 1.0  # 1% risk per trade
API_KEY = "YOUR_QUOTEX_API_KEY"

# ======================
# INITIALIZE BOT
# ======================
client = QuotexAPI(API_KEY)
client.connect()  # Connect to Quotex

# ======================
# TRADING STRATEGIES
# ======================
def calculate_indicators(df):
    # EMA for trend
    df['EMA9'] = talib.EMA(df['close'], timeperiod=9)
    
    # RSI for overbought/oversold
    df['RSI3'] = talib.RSI(df['close'], timeperiod=3)
    
    # Support/Resistance (Fractals)
    df['SwingHigh'] = talib.MAX(df['high'], timeperiod=5)
    df['SwingLow'] = talib.MIN(df['low'], timeperiod=5)
    
    return df

def check_sr_bounce(df):
    last_close = df['close'].iloc[-1]
    support = df['SwingLow'].iloc[-1]
    resistance = df['SwingHigh'].iloc[-1]
    
    # Buy if price bounces near support with RSI oversold
    if (abs(last_close - support) / support) < 0.0005 and df['RSI3'].iloc[-1] < 30:
        return "BUY", support, resistance
    
    # Sell if price rejects resistance with RSI overbought
    elif (abs(last_close - resistance) / resistance) < 0.0005 and df['RSI3'].iloc[-1] > 70:
        return "SELL", support, resistance
    
    return None, None, None

def check_trend_pullback(df):
    # Buy if price pulls back to EMA9 in uptrend
    if df['close'].iloc[-1] > df['EMA9'].iloc[-1] and df['RSI3'].iloc[-1] > 50:
        return "BUY"
    
    # Sell if price rejects EMA9 in downtrend
    elif df['close'].iloc[-1] < df['EMA9'].iloc[-1] and df['RSI3'].iloc[-1] < 50:
        return "SELL"
    
    return None

# ======================
# RISK MANAGEMENT
# ======================
def calculate_position_size(balance, risk_percent, sl_distance):
    risk_amount = balance * (risk_percent / 100)
    lot_size = risk_amount / sl_distance
    return round(lot_size, 2)

# ======================
# TRADE EXECUTION
# ======================
def place_trade(signal, entry, tp, sl):
    balance = client.get_balance()
    sl_distance = abs(entry - sl)
    lot_size = calculate_position_size(balance, RISK_PER_TRADE, sl_distance)
    
    if signal == "BUY":
        print(f"📈 BUY at {entry}, TP: {tp}, SL: {sl}")
        client.buy(PAIR, lot_size, "call", TIMEFRAME)
    elif signal == "SELL":
        print(f"📉 SELL at {entry}, TP: {tp}, SL: {sl}")
        client.buy(PAIR, lot_size, "put", TIMEFRAME)

# ======================
# MAIN TRADING LOOP
# ======================
def run_bot():
    print("🚀 SHAZ BOT STARTED - 1-MIN SCALPING MODE")
    
    while True:
        try:
            # Get latest candle data
            candles = client.get_candles(PAIR, TIMEFRAME, 100)
            df = pd.DataFrame(candles)
            df = calculate_indicators(df)
            
            # Check strategies
            signal, support, resistance = check_sr_bounce(df)
            
            if signal:
                if signal == "BUY":
                    entry = df['close'].iloc[-1] + 0.0002  # Add 2 pips
                    tp = resistance
                    sl = support - 0.0005
                else:
                    entry = df['close'].iloc[-1] - 0.0002  # Subtract 2 pips
                    tp = support
                    sl = resistance + 0.0005
                
                place_trade(signal, entry, tp, sl)
            
            # Also check trend pullback
            trend_signal = check_trend_pullback(df)
            if trend_signal:
                if trend_signal == "BUY":
                    entry = df['close'].iloc[-1] + 0.0002
                    tp = entry + 0.0010  # 10 pips TP
                    sl = entry - 0.0005  # 5 pips SL
                else:
                    entry = df['close'].iloc[-1] - 0.0002
                    tp = entry - 0.0010
                    sl = entry + 0.0005
                
                place_trade(trend_signal, entry, tp, sl)
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"⚠️ ERROR: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()