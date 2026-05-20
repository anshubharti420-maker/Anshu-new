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

# 2. AAPKI ASLI LIVE UPSTOX KEYS DIRECTLY CONNECTED
API_KEY = '878a60c5-afcc-4e01-8213-f03758ee3722'
API_SECRET = '878a60c5-afcc-4e01-8213-f03758ee3272'  # <-- Aapki Secret Key yahan fix kar di hai
REDIRECT_URI = 'https://anshu-new-1.onrender.com/callback'

# Safe Backup Data (Agar database khali ho toh dashboard crash na ho)
MOCK_SIGNALS = [
    {"symbol": "RELIANCE", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2450.0, "signal_date": "2026-05-21", "actual_change_pct": 1.5, "hit": True},
    {"symbol": "TATASTEEL", "signal_type": "BTST", "direction": "UP", "price_at_signal": 164.2, "signal_date": "2026-05-21", "actual_change_pct": 2.1, "hit": True},
    {"symbol": "HDFCBANK", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 1510.5, "signal_date": "2026-05-21", "actual_change_pct": -0.4, "hit": False},
    {"symbol": "SBIN", "signal_type": "BTST", "direction": "UP", "price_at_signal": 825.0, "signal_date": "2026-05-21", "actual_change_pct": 0.0, "hit": None}
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
                direction TEXT NOT NULL,
                price_at_signal NUMERIC NOT NULL,
                signal_date DATE NOT NULL,
                actual_change_pct NUMERIC,
                hit BOOLEAN,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Table Creation Error:", e)

# ➡️ UPSTOX LOGIN ROUTE
@app.route('/login-upstox')
def login_upstox():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

# ➡️ UPSTOX CALLBACK ROUTE (Token lekar live data insert karega)
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
                
                # Upstox API se live market price fetch karna
                stock_instruments = "NSE_EQ|INE002A01018,NSE_EQ|INE040A01034" # Reliance & HDFC Bank
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
                            
                            # Database me live entry push ho rahi hai
                            cur.execute("""
                                INSERT INTO public.signal_history (symbol, signal_type, direction, price_at_signal, signal_date, hit)
                                VALUES (%s, 'INTRADAY', 'UP', %s, NOW(), True);
                            """, (symbol_name, last_price))
                        conn.commit()
                        cur.close()
                        conn.close()
    except Exception as e:
        print("Error processing live data via Upstox:", e)
    return redirect(url_for('index'))

# 🔄 REFRESH BUTTON API LINK
@app.route('/api/refresh')
def api_refresh():
    try:
        check_and_create_table()
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT symbol, signal_type, direction, price_at_signal, signal_date, actual_change_pct, hit FROM public.signal_history ORDER BY id DESC LIMIT 50")
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
