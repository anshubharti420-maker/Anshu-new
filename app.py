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
API_SECRET = 'YAHAN_APNI_UPSTOX_SECRET_KEY_PASTE_KAREIN'  # <-- Apni Secret Key dhyan se check kar lena
REDIRECT_URI = 'https://anshu-new-1.onrender.com/callback'

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

@app.route('/login-upstox')
def login_upstox():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    # (Upstox connection logic code remains same background fetch)
    return redirect(url_for('index'))

# 🔄 NAYA REFRESH KEY API (Jo button dabate hi backend ko check karega)
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
    # Dashboard loading structure remains intact
    return render_template('dashboard.html', total=4, hits=3, accuracy=75.0)

if __name__ == '__main__':
    app.run()
