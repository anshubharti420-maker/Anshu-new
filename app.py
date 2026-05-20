import os
from flask import Flask, render_template, request

app = Flask(__name__)

# Aapka live stock data jo aapke dashboard par dikhega
MOCK_SIGNALS = [
    {"symbol": "PFIZER", "signal_type": "BTST", "direction": "UP", "price_at_signal": 4954.7, "signal_date": "2026-05-15", "actual_change_pct": 2.4, "hit": True},
    {"symbol": "GANDHAR", "signal_type": "BTST", "direction": "UP", "price_at_signal": 149.98, "signal_date": "2026-05-15", "actual_change_pct": -0.8, "hit": False},
    {"symbol": "TATVA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1316.3, "signal_date": "2026-05-15", "actual_change_pct": 0.0, "hit": None},
    {"symbol": "VIJAYA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1329.2, "signal_date": "2026-05-15", "actual_change_pct": 1.1, "hit": True},
    {"symbol": "SOLARA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 579.9, "signal_date": "2026-05-15", "actual_change_pct": 3.5, "hit": True},
    {"symbol": "HIRECT", "signal_type": "BTST", "direction": "UP", "price_at_signal": 946.35, "signal_date": "2026-05-15", "actual_change_pct": 0.0, "hit": None},
    {"symbol": "GSPL", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 268.35, "signal_date": "2026-05-17", "actual_change_pct": 4.2, "hit": True},
    {"symbol": "WHEELS", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2105.0, "signal_date": "2026-05-17", "actual_change_pct": -1.5, "hit": False},
]

@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    
    signals = MOCK_SIGNALS
    
    # Dropdown filters apply karna
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
