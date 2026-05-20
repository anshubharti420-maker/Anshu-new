import os
from flask import Flask, render_template, request

app = Flask(__name__)

# Backup static data jo aapki file me tha, agar database khali ho toh yeh chalega
MOCK_SIGNALS = [
    {"symbol": "PFIZER", "signal_type": "BTST", "direction": "UP", "price_at_signal": 4954.7, "signal_date": "2026-05-15", "actual_change_pct": 2.4, "hit": True},
    {"symbol": "GANDHAR", "signal_type": "BTST", "direction": "UP", "price_at_signal": 149.98, "signal_date": "2026-05-15", "actual_change_pct": -0.8, "hit": False},
    {"symbol": "TATVA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1316.3, "signal_date": "2026-05-15", "actual_change_pct": None, "hit": None},
    {"symbol": "VIJAYA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 1329.2, "signal_date": "2026-05-15", "actual_change_pct": 1.1, "hit": True},
    {"symbol": "SOLARA", "signal_type": "BTST", "direction": "UP", "price_at_signal": 579.9, "signal_date": "2026-05-15", "actual_change_pct": 3.5, "hit": True},
    {"symbol": "HIRECT", "signal_type": "BTST", "direction": "UP", "price_at_signal": 946.35, "signal_date": "2026-05-15", "actual_change_pct": None, "hit": None},
    {"symbol": "GSPL", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 268.35, "signal_date": "2026-05-17", "actual_change_pct": 4.2, "hit": True},
    {"symbol": "WHEELS", "signal_type": "INTRADAY", "direction": "UP", "price_at_signal": 2105.0, "signal_date": "2026-05-17", "actual_change_pct": -1.5, "hit": False},
]

@app.route('/')
def index():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    signals = []
    total_signals = len(MOCK_SIGNALS)
    total_hits = len([s for s in MOCK_SIGNALS if s['hit'] is True])
    
    try:
        # Pehle check karega agar cloud database me tables milte hain
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        query = "SELECT id, symbol, signal_type, direction, price_at_signal, signal_date, actual_change_pct, hit FROM public.signal_history WHERE 1=1"
        params = []
        if signal_type:
            query += " AND signal_type = %s"; params.append(signal_type)
        if direction:
            query += " AND direction = %s"; params.append(direction)
        query += " ORDER BY signal_date DESC LIMIT 50"
        
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
        # Agar table nahi mila toh safe backup data use karega taki app crash na ho
        signals = MOCK_SIGNALS
        if signal_type:
            signals = [s for s in signals if s['signal_type'] == signal_type]
        if direction:
            signals = [s for s in signals if s['direction'] == direction]

    accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
