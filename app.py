import os
import json
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = '878a60c5-afcc-4e01-8213-f03758ee3272'
API_SECRET = '878a60c5-afcc-4e01-8213-f93758ee3272'
REDIRECT_URI = 'https://anshu-new-1.onrender.com/callback'

# PREMIUM MOCK DATA: Jab tak real cloud database me entry push nahi hoti, ye automatic pro table columns fill rakhega
MOCK_SIGNALS = [
    {"symbol": "RELIANCE", "timeframe": "15 MIN", "strategy": "CPR Breakout", "direction": "BUY", "price_at_signal": 2450.0, "ltp": 2478.5, "target1": 2475.0, "target2": 2500.0, "stop_loss": 2435.0, "hit": True},
    {"symbol": "TATASTEEL", "timeframe": "5 MIN", "strategy": "EMA Crossover", "direction": "BUY", "price_at_signal": 164.2, "ltp": 168.5, "target1": 166.0, "target2": 170.0, "stop_loss": 162.5, "hit": True},
    {"symbol": "HDFCBANK", "timeframe": "15 MIN", "strategy": "VWAP Rejection", "direction": "SELL", "price_at_signal": 1510.5, "ltp": 1515.0, "target1": 1495.0, "target2": 1480.0, "stop_loss": 1522.0, "hit": False},
    {"symbol": "SBIN", "timeframe": "30 MIN", "strategy": "Inside Bar Pattern", "direction": "BUY", "price_at_signal": 825.0, "ltp": 826.4, "target1": 835.0, "target2": 845.0, "stop_loss": 818.0, "hit": None}
]

def check_and_create_table():
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Custom Advanced Database Schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.signal_history (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT DEFAULT '15 MIN',
                strategy TEXT DEFAULT 'Algo Scanner',
                direction TEXT NOT NULL,
                price_at_signal NUMERIC NOT NULL,
                ltp NUMERIC,
                target1 NUMERIC,
                target2 NUMERIC,
                stop_loss NUMERIC,
                signal_date DATE DEFAULT NOW(),
                hit BOOLEAN,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Table Structure Upgrade Error:", e)

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
                            
                            # Advanced data insert matching our beautiful UI
                            cur.execute("""
                                INSERT INTO public.signal_history (symbol, timeframe, strategy, direction, price_at_signal, ltp, target1, target2, stop_loss, hit)
                                VALUES (%s, '15 MIN', 'Upstox Live Engine', 'BUY', %s, %s, %s, %s, %s, null);
                            """, (symbol_name, last_price, last_price, last_price*1.01, last_price*1.02, last_price*0.995))
                        conn.commit()
                        cur.close()
                        conn.close()
    except Exception as e:
        print("Live Upstox Streaming Error:", e)
    return redirect(url_for('index'))

@app.route('/api/refresh')
def api_refresh():
    try:
        check_and_create_table()
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT symbol, timeframe, strategy, direction, price_at_signal, ltp, target1, target2, stop_loss, hit FROM public.signal_history ORDER BY id DESC LIMIT 50")
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
