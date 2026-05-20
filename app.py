import os
import json
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# 1. DATABASE URL Render se automatically load hoga
DATABASE_URL = os.environ.get('DATABASE_URL')

# 2. AAPKI LATEST FIXED UPSTOX KEYS
API_KEY = '878a60c5-afcc-4e01-8213-f03758ee3722'
API_SECRET = 'i1j86ouh44'  # <-- Aapki naye Secret Key yahan lock kar di hai
REDIRECT_URI = 'https://anshu-new-1.onrender.com/callback'

# Premium Segmented Cards Mock Model (BTST aur INTRADAY proper alignment ke sath)
MOCK_SIGNALS = [
    {"symbol": "TIRUMALCHM", "signal_type": "BTST", "timeframe": "DAILY", "strategy": "High Vol Breakout", "direction": "BUY", "price_at_signal": 212.08, "ltp": 214.50, "target1": 222.68, "stop_loss": 207.84},
    {"symbol": "TEMBO", "signal_type": "BTST", "timeframe": "DAILY", "strategy": "Institutional Flow", "direction": "BUY", "price_at_signal": 592.95, "ltp": 596.10, "target1": 622.60, "stop_loss": 581.09},
    {"symbol": "IOLCP", "signal_type": "BTST", "timeframe": "DAILY", "strategy": "Delivery Spike", "direction": "BUY", "price_at_signal": 119.54, "ltp": 121.20, "target1": 125.52, "stop_loss": 117.15},
    {"symbol": "ASTRAMICRO", "signal_type": "INTRADAY", "timeframe": "15 MIN", "strategy": "CPR Breakout", "direction": "BUY", "price_at_signal": 1154.10, "ltp": 1159.00, "target1": 1177.18, "stop_loss": 1142.56},
    {"symbol": "ABB", "signal_type": "INTRADAY", "timeframe": "5 MIN", "strategy": "EMA Cross Spike", "direction": "BUY", "price_at_signal": 6605.00, "ltp": 6624.00, "target1": 6737.10, "stop_loss": 6538.95},
    {"symbol": "ERIS", "signal_type": "INTRADAY", "timeframe": "15 MIN", "strategy": "VWAP Rejection", "direction": "BUY", "price_at_signal": 1458.20, "ltp": 1462.00, "target1": 1487.36, "stop_loss": 1443.62}
]

def check_and_create_table():
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.signal_history (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                timeframe TEXT DEFAULT '15 MIN',
                strategy TEXT DEFAULT 'Algo Scanner',
                direction TEXT NOT NULL,
                price_at_signal NUMERIC NOT NULL,
                ltp NUMERIC,
                target1 NUMERIC,
                stop_loss NUMERIC,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Table structure check error:", e)

@app.route('/login-upstox')
def login_upstox():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
        
    token_url = 'https://api.upstox.com/v2/login/authorization/token'
    data = {
        'code': code,
        'client_id': API_KEY,
        'client_secret': API_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    try:
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(token_url, data=encoded_data, headers={'accept': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            access_token = res.get('access_token')
            
            if access_token:
                check_and_create_table()
                stock_instruments = "NSE_EQ|INE002A01018,NSE_EQ|INE040A01034"
                quote_url = f'https://api.upstox.com/v2/market-quote/quotes?instrument_key={stock_instruments}'
                
                quote_req = urllib.request.Request(quote_url, headers={
                    'accept': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                })
                
                with urllib.request.urlopen(quote_req) as quote_response:
                    market_data = json.loads(quote_response.read().decode('utf-8'))
                    if market_data.get('status') == 'success' and DATABASE_URL:
                        data_body = market_data.get('data', {})
                        conn = psycopg2.connect(DATABASE_URL)
                        cur = conn.cursor()
                        
                        for key, val in data_body.items():
                            symbol_name = val.get('symbol')
                            last_price = val.get('last_price')
                            
                            # Live server entry saving logic categorised as Intraday
                            cur.execute("""
                                INSERT INTO public.signal_history (symbol, signal_type, timeframe, strategy, direction, price_at_signal, ltp, target1, stop_loss)
                                VALUES (%s, 'INTRADAY', '15 MIN', 'Upstox Active Flow', 'BUY', %s, %s, %s, %s);
                            """, (symbol_name, last_price, last_price, last_price*1.01, last_price*0.995))
                        conn.commit()
                        cur.close()
                        conn.close()
    except Exception as e:
        print("Upstox connection failed:", e)
    return redirect(url_for('index'))

@app.route('/api/refresh')
def api_refresh():
    try:
        check_and_create_table()
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT symbol, signal_type, timeframe, strategy, direction, price_at_signal, ltp, target1, stop_loss FROM public.signal_history ORDER BY id DESC LIMIT 50")
        signals = cur.fetchall()
        cur.close()
        conn.close()
        if not signals:
            return jsonify({"status": "success", "signals": MOCK_SIGNALS})
        return jsonify({"status": "success", "signals": signals})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "signals": MOCK_SIGNALS})

@app.route('/')
def index():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run()
