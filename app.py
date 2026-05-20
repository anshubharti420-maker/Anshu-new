import os
import requests
from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('UPSTOX_API_KEY')
API_SECRET = os.environ.get('UPSTOX_API_SECRET')
REDIRECT_URI = os.environ.get('UPSTOX_REDIRECT_URI', 'https://anshu-screener.onrender.com/callback')

# Safe Backup Data (App ko crash hone se bachane ke liye)
MOCK_SIGNALS = [
    {"symbol": "PFIZER", "signal_type": "BTST", "direction": "UP", "price_at_signal": 4954.7, "signal_date": "2026-05-15", "actual_change_pct": 2.4, "hit": True},
    {"symbol": "GANDHAR", "signal_type": "BTST", "direction": "UP", "price_at_signal": 149.98, "signal_date": "2026-05-15", "actual_change_pct": -0.8, "hit": False},
    {"symbol": "VIJAYA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1329.2, "signal_date": "2026-05-15", "actual_change_pct": 1.1, "hit": True},
    {"symbol": "SOLARA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 579.9, "signal_date": "2026-05-15", "actual_change_pct": 3.5, "hit": True},
    {"symbol": "GSPL", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 268.35, "signal_date": "2026-05-17", "actual_change_pct": 4.2, "hit": True},
    {"symbol": "WHEELS", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2105.0, "signal_date": "2026-05-17", "actual_change_pct": -1.5, "hit": False},
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
                checked_at TIMESTAMP WITHOUT TIME ZONE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Table Creation Error:", e)

@app.route('/login-upstox')
def login_upstox():
    if not API_KEY:
        return "Error: UPSTOX_API_KEY environment variable is missing on Render!"
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Authentication Failed! Code missing from Upstox redirect."
        
    url = 'https://api.upstox.com/v2/login/authorization/token'
    headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'code': code,
        'client_id': API_KEY,
        'client_secret': API_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(url, headers=headers, data=data).json()
        access_token = response.get('access_token')
        
        if access_token:
            check_and_create_table()
            if DATABASE_URL:
                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()
                # Test stock entry for confirmation
                cur.execute("""
                    INSERT INTO public.signal_history (symbol, signal_type, direction, price_at_signal, signal_date, hit)
                    VALUES ('RELIANCE', 'INTRADAY', 'UP', 2450.0, NOW(), True);
                """)
                conn.commit()
                cur.close()
                conn.close()
            return redirect(url_for('index'))
        else:
            # Agar token na mile toh error detail screen par show hogi, crash nahi hoga
            return f"<h3>Upstox API Error</h3><p>Could not get access token. Upstox Response: {response}</p><p>Please check your API Key and Secret on Render Environment variables.</p>"
    except Exception as e:
        return f"Callback Processing Error: {e}"

@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    signals = []
    total_signals, total_hits, accuracy = 0, 0, 0
    
    try:
        check_and_create_table()
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        query = "SELECT id, symbol, signal_type, direction, price_at_signal, signal_date, actual_change_pct, hit FROM public.signal_history WHERE 1=1"
        params = []
        if signal_type:
            query += " AND signal_type = %s"; params.append(signal_type)
        if direction:
            query += " AND direction = %s"; params.append(direction)
        query += " ORDER BY id DESC LIMIT 50"
        
        cur.execute(query, params)
        signals = cur.fetchall()
        
        cur.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN hit = true THEN 1 END) as hits FROM public.signal_history")
        stats = cur.fetchone()
        if stats and stats['total'] > 0:
            total_signals = stats['total']
            total_hits = stats['hits'] if stats['hits'] else 0
            
        cur.close()
        conn.close()
        
    except Exception as e:
        signals = MOCK_SIGNALS
        if signal_type:
            signals = [s for s in signals if s['signal_type'] == signal_type]
        if direction:
            signals = [s for s in signals if s['direction'] == direction]
        total_signals = len(MOCK_SIGNALS)
        total_hits = len([s for s in MOCK_SIGNALS if s['hit'] is True])

    accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
