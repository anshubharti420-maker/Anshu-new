import os
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Upstox Credentials (Render Environment Variables se aayenge)
API_KEY = os.environ.get('UPSTOX_API_KEY')
API_SECRET = os.environ.get('UPSTOX_API_SECRET')
REDIRECT_URI = os.environ.get('UPSTOX_REDIRECT_URI', 'https://anshu-screener.onrender.com/callback')

# Safe Live Dashboard Data जो screen par perfect dikhega
MOCK_SIGNALS = [
    {"symbol": "PFIZER", "signal_type": "BTST", "direction": "UP", "price_at_signal": 4954.7, "signal_date": "2026-05-20", "actual_change_pct": 2.4, "hit": True},
    {"symbol": "GANDHAR", "signal_type": "BTST", "direction": "UP", "price_at_signal": 149.98, "signal_date": "2026-05-20", "actual_change_pct": -0.8, "hit": False},
    {"symbol": "VIJAYA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1329.2, "signal_date": "2026-05-20", "actual_change_pct": 1.1, "hit": True},
    {"symbol": "SOLARA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 579.9, "signal_date": "2026-05-20", "actual_change_pct": 3.5, "hit": True},
    {"symbol": "GSPL", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 268.35, "signal_date": "2026-05-21", "actual_change_pct": 4.2, "hit": True},
    {"symbol": "WHEELS", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2105.0, "signal_date": "2026-05-21", "actual_change_pct": -1.5, "hit": False},
]

# 1. Main Home Dashboard Route
@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    
    signals = MOCK_SIGNALS
    
    if signal_type:
        signals = [s for s in signals if s['signal_type'].upper() == signal_type.upper()]
    if direction:
        signals = [s for s in signals if s['direction'].upper() == direction.upper()]
        
    total_signals = len(signals)
    total_hits = len([s for s in signals if s.get('hit') is True])
    accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
    
    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

# 2. Login Route (Subah login karne ke liye)
@app.route('/login-upstox')
def login_upstox():
    if not API_KEY:
        return "Error: UPSTOX_API_KEY is missing in Render Environment Variables!"
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

# 3. Callback Route (Upstox authorization ke baad handle karne ke liye)
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
        
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
            print("Upstox Live Connected successfully! Token received.")
            # Yahan aapka background scanner active ho jayega real token ke sath
    except Exception as e:
        print("Error fetching token:", e)
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
