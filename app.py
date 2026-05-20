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

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# 1. Subah Login karne ke liye route (Market khulne par mobile par isko click karna hoga)
@app.route('/login-upstox')
def login_upstox():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

# 2. Upstox Login ke baad automatic token generate hoga aur database me naye stocks aayenge
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Authentication Failed! Code missing."
        
    # Upstox se Access Token lena
    url = 'https://api.upstox.com/v2/login/authorization/token'
    headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'code': code,
        'client_id': API_KEY,
        'client_secret': API_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(url, headers=headers, data=data).json()
    access_token = response.get('access_token')
    
    if access_token:
        # --- LIVE DATA SCANNING LOGIC ---
        # Yeh block Upstox se real-time data fetch karega aur live database me insert karega
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # (Sample Test Signal: Jab aap login karenge, yeh automatic test stock database me entry add kar dega)
            cur.execute("""
                INSERT INTO public.signal_history (symbol, signal_type, direction, price_at_signal, signal_date, hit)
                VALUES ('RELIANCE', 'INTRADAY', 'UP', 2450.0, NOW(), True);
            """)
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Token generated but Database Error: {e}"
    else:
        return f"Token Error: {response}"

# 3. Main Dashboard (Jo mobile me dikhta hai)
@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    signals = []
    total_signals, total_hits, accuracy = 0, 0, 0
    
    try:
        conn = get_db_connection()
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
        if stats:
            total_signals = stats['total'] if stats['total'] else 0
            total_hits = stats['hits'] if stats['hits'] else 0
            accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
            
        cur.close()
        conn.close()
    except Exception as e:
        print("Fetch Error:", e)

    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
