import os
from flask import Flask, render_template, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Render ka PostgreSQL database URL automatic uthayega
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    
    signals = []
    total_signals = 0
    total_hits = 0
    accuracy = 0
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Live Table se data uthana
        query = "SELECT id, symbol, signal_type, direction, price_at_signal, signal_date, actual_change_pct, hit FROM public.signal_history WHERE 1=1"
        params = []
        
        if signal_type:
            query += " AND signal_type = %s"; params.append(signal_type)
        if direction:
            query += " AND direction = %s"; params.append(direction)
            
        query += " ORDER BY id DESC LIMIT 50"
        
        cur.execute(query, params)
        signals = cur.fetchall()
        
        # Live Stats calculate karna
        cur.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN hit = true THEN 1 END) as hits FROM public.signal_history")
        stats = cur.fetchone()
        
        if stats:
            total_signals = stats['total'] if stats['total'] else 0
            total_hits = stats['hits'] if stats['hits'] else 0
            accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
            
        cur.close()
        conn.close()
    except Exception as e:
        print("Database Error:", e)
        # Agar koi temporary error ho toh khali list dikhaye crash na ho
        signals = []

    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
