import os
from flask import Flask, render_template, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Cloud Database URL automatic uthayega
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/heliumdb')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    signal_type = request.args.get('signal_type', '')
    direction = request.args.get('direction', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Live data query
    query = "SELECT id, symbol, signal_type, direction, price_at_signal, signal_date, actual_change_pct, hit FROM public.signal_history WHERE 1=1"
    params = []
    
    if signal_type:
        query += " AND signal_type = %s"
        params.append(signal_type)
    if direction:
        query += " AND direction = %s"
        params.append(direction)
        
    query += " ORDER BY signal_date DESC, id DESC LIMIT 50"
    
    cur.execute(query, params)
    signals = cur.fetchall()
    
    # Stats Calculation
    cur.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN hit = true THEN 1 END) as hits FROM public.signal_history")
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    total_signals = stats['total'] if stats['total'] else 0
    total_hits = stats['hits'] if stats['hits'] else 0
    accuracy = round((total_hits / total_signals) * 100, 2) if total_signals > 0 else 0
    
    return render_template('dashboard.html', signals=signals, accuracy=accuracy, total=total_signals, hits=total_hits)

if __name__ == '__main__':
    app.run()
  
