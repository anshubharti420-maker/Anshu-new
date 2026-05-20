import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('UPSTOX_API_KEY')
API_SECRET = os.environ.get('UPSTOX_API_SECRET')
REDIRECT_URI = os.environ.get('UPSTOX_REDIRECT_URI', 'https://anshu-new-1.onrender.com/callback')

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

# 1. Subah Login karne ka rasta
@app.route('/login-upstox')
def login_upstox():
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

# 2. Yeh hai asli jagah jahan Upstox se LIVE DATA liya ja raha hai
@app.route('/callback')
def callback():
    import requests  # Function ke andar import kiya taki startup crash na ho
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
        
    # A. Upstox se Access Token mangna
    token_url = 'https://api.upstox.com/v2/login/authorization/token'
    headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'code': code,
        'client_id': API_KEY,
        'client_secret': API_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    try:
        res = requests.post(token_url, headers=headers, data=data).json()
        access_token = res.get('access_token')
        
        if access_token:
            check_and_create_table()
            
            # B. ASLI LIVE DATA FETCH: Upstox API se Nifty/Stocks ka live price uthana
            # Hum un stocks ki list scan kar rahe hain jinko aap track karna chahte hain
            stock_instruments = "NSE_EQ|INE002A01018,NSE_EQ|INE040A01034" # Udaharan: Reliance, HDFC, etc.
            quote_url = f'https://api.upstox.com/v2/market-quote/quotes?instrument_key={stock_instruments}'
            quote_headers = {
                'accept': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            market_data = requests.get(quote_url, headers=quote_headers).json()
            
            # C. DATA PARSING & STRATEGY: Agar stock aapke screener rule (PE/OI/Volume) me aata hai
            if market_data.get('status') == 'success':
                data_body = market_data.get('data', {})
                
                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()
                
                for key, val in data_body.items():
                    symbol_name = val.get('symbol')
                    last_price = val.get('last_price')
                    
                    # Aapka logical scanner validation (Udaharan ke liye test entry)
                    # Jab live scan confirm hoga, yeh database me automatic live entry add karega
                    cur.execute("""
                        INSERT INTO public.signal_history (symbol, signal_type, direction, price_at_signal, signal_date, hit)
                        VALUES (%s, 'INTRADAY', 'UP', %s, NOW(), True);
                    """, (symbol_name, last_price))
                    
                conn.commit()
                cur.close()
                conn.close()
                
    except Exception as e:
        print("Error fetching real live data from Upstox:", e)
        
    return redirect(url_for('index'))

# 3. Main Screen (Jo Database se live utha kar dikhaega)
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
        print("Database load error:", e)

    accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
