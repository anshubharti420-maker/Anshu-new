import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Mock Data jo bina kisi library crash ke turant load hoga
MOCK_SIGNALS = [
    {"symbol": "PFIZER", "signal_type": "BTST", "direction": "UP", "price_at_signal": 4954.7, "signal_date": "2026-05-20", "actual_change_pct": 2.4, "hit": True},
    {"symbol": "GANDHAR", "signal_type": "BTST", "direction": "UP", "price_at_signal": 149.98, "signal_date": "2026-05-20", "actual_change_pct": -0.8, "hit": False},
    {"symbol": "VIJAYA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1329.2, "signal_date": "2026-05-20", "actual_change_pct": 1.1, "hit": True},
    {"symbol": "SOLARA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 579.9, "signal_date": "2026-05-20", "actual_change_pct": 3.5, "hit": True},
    {"symbol": "GSPL", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 268.35, "signal_date": "2026-05-21", "actual_change_pct": 4.2, "hit": True},
    {"symbol": "WHEELS", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2105.0, "signal_date": "2026-05-21", "actual_change_pct": -1.5, "hit": False},
]

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

@app.route('/login-upstox')
def login_upstox():
    # Jab aapko Upstox live chalana hoga, hum import ko function ke andar rakhenge taki app crash na ho
    import requests
    API_KEY = os.environ.get('UPSTOX_API_KEY', '')
    REDIRECT_URI = os.environ.get('UPSTOX_REDIRECT_URI', 'https://anshu-new-1.onrender.com/callback')
    url = f"https://api.upstox.com/v2/login/authorization/dialog?client_id={API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code"
    return redirect(url)

@app.route('/callback')
def callback():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
