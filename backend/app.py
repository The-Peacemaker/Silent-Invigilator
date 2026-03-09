"""
THE SILENT INVIGILATOR — Flask Web Server
Includes:
 - Role-based Authentication (Admin / Teacher / Staff Invigilator)
 - Live MJPEG Streaming
 - JSON Status & Stats APIs
 - SQLite Database Logging (Background Thread)
 - Admin User Management
 - Dashboard Routes per Role

 run command :  cd silent-invigilator && .venv\Scripts\python.exe app.py
"""

from flask import Flask, render_template, Response, jsonify, request, redirect, session, url_for
from flask_cors import CORS
from functools import wraps
import threading
import time
import sqlite3
import os
import hashlib
import json

# ── DEMO MODE ────────────────────────────────────────────
# Set to True for presentation — uses simulated AI detection
DEMO_MODE = True

app = Flask(__name__)
app.secret_key = 'silent-invigilator-secret-key-2026'
CORS(app)

# ── DATABASE & LOGGING ───────────────────────────────────
DB_FILE = 'invigilator.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Logs table
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, 
                  risk_score INTEGER, 
                  event_type TEXT, 
                  description TEXT)''')
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE NOT NULL, 
                  password TEXT NOT NULL, 
                  role TEXT NOT NULL DEFAULT 'teacher', 
                  full_name TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def seed_users():
    """Create default users if none exist."""
    conn = sqlite3.connect(DB_FILE)
    existing = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    default_users = [
        ('admin', hash_password('admin123'), 'admin', 'Administrator'),
        ('sarah', hash_password('sarah123'), 'teacher', 'Dr. Sarah Mitchell'),
        ('james', hash_password('james123'), 'teacher', 'Prof. James Wilson'),
        ('elena', hash_password('elena123'), 'teacher', 'Ms. Elena Rodriguez'),
        ('robert', hash_password('robert123'), 'teacher', 'Mr. Robert Chen'),
    ]
    
    for uname, pwd, role, fname in default_users:
        conn.execute(
            'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
            (uname, pwd, role, fname)
        )
    conn.commit()
    conn.close()
    print(f"[INIT] Seeded {len(default_users)} default users")

# ── AUTH HELPERS ──────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                return redirect(url_for('get_dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── GLOBAL CAMERA ────────────────────────────────────────
_camera      = None
_camera_lock = threading.Lock()

def get_camera(init=True):
    global _camera
    with _camera_lock:
        if _camera is None and init:
            if DEMO_MODE:
                from camera import DemoCamera
                _camera = DemoCamera()
            else:
                from camera import VideoCamera
                _camera = VideoCamera()
    return _camera

# ── BACKGROUND LOGGER ────────────────────────────────────
def background_monitor():
    """
    Background thread that monitors detection state.
    Logs specific high-risk events (Phone, Material, etc.) to SQLite.
    """
    print("[INFO] Background Logger Started")
    
    # Track last log time per specific event type to prevent database spam
    last_log = {
        'phone': 0,
        'material': 0,
        'proximity': 0,
        'audio': 0,
        'missing': 0,
        'general': 0
    }
    COOLDOWN = 15  # 15 seconds cooldown per event type

    while True:
        try:
            cam = get_camera(init=False)
            if cam:
                now = time.time()
                conn = None
                
                # Check specific critical events first
                if cam.phone_detected and (now - last_log['phone'] > COOLDOWN):
                    conn = get_db_connection()
                    with conn:
                        conn.execute("INSERT INTO logs (timestamp, risk_score, event_type, description) VALUES (?, ?, ?, ?)",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 80), 'PROHIBITED OBJECT (PHONE)', 'PHONE DETECTED - Mobile device on camera'))
                        last_log['phone'] = now
                        print(f"[LOG] Alert saved: PHONE DETECTED ({cam.anomaly_score})")

                elif any("Material" in x for x in getattr(cam, 'detections', [])) and (now - last_log['material'] > COOLDOWN):
                    if not conn: conn = get_db_connection()
                    with conn:
                        conn.execute("INSERT INTO logs (timestamp, risk_score, event_type, description) VALUES (?, ?, ?, ?)",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 60), 'SUSPICIOUS MATERIAL', 'Book or Paper detected on camera'))
                        last_log['material'] = now
                        print(f"[LOG] Alert saved: MATERIAL DETECTED ({cam.anomaly_score})")

                elif not getattr(cam, 'face_detected', False) and len(getattr(cam, 'cached_persons', [])) > 0 and (now - last_log['missing'] > COOLDOWN):
                    if not conn: conn = get_db_connection()
                    with conn:
                        conn.execute("INSERT INTO logs (timestamp, risk_score, event_type, description) VALUES (?, ?, ?, ?)",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 50), 'FACE HIDDEN', 'Person detected but face is invisible/hidden'))
                        last_log['missing'] = now
                        print(f"[LOG] Alert saved: FACE HIDDEN ({cam.anomaly_score})")

                # Fallback to general high anomaly score
                elif cam.anomaly_score > 60 and (now - last_log['general'] > COOLDOWN):
                    # Only log general anomaly if we didn't just log a specific one
                    if (now - max(last_log.values())) > 5:
                        if not conn: conn = get_db_connection()
                        with conn:
                            desc = ", ".join(cam.detections) if cam.detections else "High Anomaly Score detected (Aggregated behaviors)"
                            conn.execute("INSERT INTO logs (timestamp, risk_score, event_type, description) VALUES (?, ?, ?, ?)",
                                         (time.strftime('%Y-%m-%d %H:%M:%S'), cam.anomaly_score, 'Suspicious Behavior', desc))
                            last_log['general'] = now
                            print(f"[LOG] Alert saved: Suspicious Behavior ({cam.anomaly_score})")

                if conn:
                    conn.close()

            time.sleep(1)
        except Exception as e:
            print(f"[Logger] Error: {e}")
            time.sleep(1)

# ── PUBLIC ROUTES ────────────────────────────────────────

@app.route('/')
def homepage():
    """Public landing page — product showcase."""
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pwd  = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        
        conn = get_db_connection()
        row = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ? AND role = ?',
            (user, hash_password(pwd), role)
        ).fetchone()
        conn.close()
        
        if row:
            session['user'] = row['username']
            session['role'] = row['role']
            session['full_name'] = row['full_name']
            session['user_id'] = row['id']
            session.permanent = True
            return redirect(url_for('get_dashboard'))
        else:
            error = 'Invalid credentials or role mismatch. Access denied.'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))

@app.route('/dashboard')
@login_required
def get_dashboard():
    """Route to the correct dashboard based on role."""
    role = session.get('role', '')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

# ── ADMIN ROUTES ─────────────────────────────────────────

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/users', methods=['GET'])
@role_required('admin')
def list_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role, full_name, created_at FROM users ORDER BY id').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/admin/users', methods=['POST'])
@role_required('admin')
def add_user():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip()
    full_name = data.get('full_name', '').strip()
    
    if not all([username, password, role, full_name]):
        return jsonify({'error': 'All fields are required'}), 400
    
    if role not in ['admin', 'teacher']:
        return jsonify({'error': 'Invalid role'}), 400
    
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
            (username, hash_password(password), role, full_name)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'User {username} created'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409

@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
@role_required('admin')
def delete_user(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/stats')
@role_required('admin')
def admin_stats():
    conn = get_db_connection()
    total_alerts = conn.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
    critical = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 70").fetchone()[0]
    warnings = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 40 AND risk_score < 70").fetchone()[0]
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    
    # Alert type distribution
    type_dist = conn.execute(
        'SELECT event_type, COUNT(*) as cnt FROM logs GROUP BY event_type ORDER BY cnt DESC'
    ).fetchall()
    
    # Recent 24h trend (group by hour)
    hourly = conn.execute(
        "SELECT substr(timestamp, 12, 2) as hour, COUNT(*) as cnt, AVG(risk_score) as avg_score FROM logs GROUP BY hour ORDER BY hour"
    ).fetchall()
    
    conn.close()
    
    info_alerts = total_alerts - critical - warnings
    
    return jsonify({
        'total_alerts': total_alerts,
        'critical_alerts': critical,
        'warning_alerts': warnings,
        'total_users': total_users,
        'type_distribution': [{'type': r['event_type'], 'count': r['cnt']} for r in type_dist],
        'hourly_trend': [{'hour': r['hour'], 'count': r['cnt'], 'avg_score': round(r['avg_score'], 1)} for r in hourly],
        'risk_distribution': {
            'critical': critical,
            'warning': warnings,
            'info': info_alerts
        }
    })

# ── TEACHER ROUTES ───────────────────────────────────────

@app.route('/teacher')
@role_required('teacher')
def teacher_dashboard():
    return render_template('teacher_dashboard_new.html')

# ── MONITORING ──────────────────────────────────────────

@app.route('/monitor')
@login_required
def monitor():
    """Live monitoring view — accessible by teacher and admin."""
    if session.get('role') not in ['teacher', 'admin']:
        return redirect(url_for('get_dashboard'))
    return render_template('monitor.html')

# ── API ENDPOINTS ────────────────────────────────────────

@app.route('/api/alerts')
@login_required
def get_alerts():
    limit = request.args.get('limit', 50, type=int)
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route('/api/stats')
@login_required
def get_stats():
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
    critical = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 70").fetchone()[0]
    warnings = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 40 AND risk_score < 70").fetchone()[0]
    
    type_dist = conn.execute(
        'SELECT event_type, COUNT(*) as cnt FROM logs GROUP BY event_type ORDER BY cnt DESC'
    ).fetchall()
    
    hourly = conn.execute(
        "SELECT substr(timestamp, 12, 2) as hour, COUNT(*) as cnt, AVG(risk_score) as avg_score FROM logs GROUP BY hour ORDER BY hour"
    ).fetchall()
    
    conn.close()
    
    return jsonify({
        'total_alerts': total,
        'critical_alerts': critical,
        'warning_alerts': warnings,
        'type_distribution': [{'type': r['event_type'], 'count': r['cnt']} for r in type_dist],
        'hourly_trend': [{'hour': r['hour'], 'count': r['cnt'], 'avg_score': round(r['avg_score'], 1)} for r in hourly],
    })

@app.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    conn = get_db_connection()
    conn.execute('DELETE FROM logs')
    conn.commit()
    conn.close()
    return redirect(url_for('get_dashboard'))

# ── VIDEO STREAMING ──────────────────────────────────────

def generate_frames():
    camera = get_camera()
    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    if 'user' not in session: return "Unauthorized", 401
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    camera = get_camera()
    return jsonify(camera.get_stats())

# ── ENTRY POINT ──────────────────────────────────────────

def seed_demo_logs():
    """Pre-populate with realistic demo logs."""
    conn = sqlite3.connect(DB_FILE)
    existing = conn.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    demo_entries = [
        ('2026-03-03 08:30:15', 75, 'Suspicious Behavior', 'Head Turn (Right), Gaze deviation detected @ Dr. Mitchell session'),
        ('2026-03-03 08:31:42', 85, 'PROHIBITED OBJECT (PHONE)', 'PHONE DETECTED, Candidate ID 1042 — AUTO-FLAGGED'),
        ('2026-03-03 08:32:10', 65, 'Suspicious Behavior', 'Looking Down — possible hidden material near desk edge'),
        ('2026-03-03 08:35:28', 90, 'PROHIBITED OBJECT (PHONE)', 'PHONE DETECTED — second violation, Candidate ID 1042'),
        ('2026-03-03 08:38:45', 72, 'COLLUSION (PROXIMITY)', 'Multiple persons detected @ Zone 4 — Critical proximity scan triggered'),
        ('2026-03-03 08:40:12', 68, 'Suspicious Behavior', 'Head Turn (Left), sustained gaze deviation > 5s @ Student Log #492'),
        ('2026-03-03 08:42:55', 80, 'AUDIO VIOLATION', 'Talking detected — audio level spike 78 dB (Pattern match: Verbal)'),
        ('2026-03-03 08:45:30', 62, 'Suspicious Behavior', 'Face hidden — student looking away from primary sensor array'),
        ('2026-03-03 08:50:18', 95, 'PROHIBITED OBJECT (PHONE)', 'CRITICAL: PHONE DETECTED + Head Turn (Right) — Manual review required'),
        ('2026-03-03 09:01:05', 70, 'Suspicious Behavior', 'Repeated gaze deviation pattern (Y-Axis Anomaly) @ Hall B-03'),
        ('2026-03-03 09:05:33', 78, 'COLLUSION (PROXIMITY)', 'Two students detected exchanging material objects @ Exam-Zone-Alpha'),
        ('2026-03-03 09:10:20', 88, 'PROHIBITED OBJECT (PHONE)', 'Object classification: [Mobile Device] Confidence 98.2% @ Zone Central'),
        ('2026-03-03 09:12:44', 42, 'Suspicious Behavior', 'Repeated hand movements under desk — tracking behavioral history'),
        ('2026-03-03 09:15:10', 55, 'AUDIO VIOLATION', 'Whispering detected — frequency spectrum analysis positive for Speech'),
        ('2026-03-03 09:18:22', 92, 'PROHIBITED OBJECT (PHONE)', 'SYSTEM LOCK: PHONE DETECTED @ Prof. James session (Incident #99021)'),
        ('2026-03-03 09:20:05', 64, 'Suspicious Behavior', 'Continuous hallway scanning pattern — anomaly detected'),
        ('2026-03-03 09:22:15', 79, 'Suspicious Behavior', 'Multiple failed gaze-focus attempts — Gaze: OFF_PAPER_DOWN'),
        ('2026-03-03 09:25:30', 98, 'PROHIBITED OBJECT (PHONE)', 'EXTREME RISK: Smart Watch detection @ Student #2011'),
        ('2026-03-03 09:28:44', 82, 'AUDIO VIOLATION', 'High decibel verbal exchange triggered silent alarm @ Zone D'),
        ('2026-03-03 09:30:12', 74, 'Suspicious Behavior', 'Face tilt anomaly (35°) detected for extended duration'),
    ]
    
    for ts, score, evt, desc in demo_entries:
        conn.execute(
            'INSERT INTO logs (timestamp, risk_score, event_type, description) VALUES (?, ?, ?, ?)',
            (ts, score, evt, desc)
        )
    conn.commit()
    conn.close()
    print(f"[DEMO] Seeded {len(demo_entries)} demo log entries")


if __name__ == '__main__':
    # Initialize DB
    init_db()
    
    # Seed default users
    seed_users()
    
    # Seed demo logs if in demo mode
    if DEMO_MODE:
        seed_demo_logs()
    
    # Start Background Logger
    t = threading.Thread(target=background_monitor, daemon=True)
    t.start()
    
    # Start Server
    print("=" * 60)
    if DEMO_MODE:
        print(" SILENT INVIGILATOR — DEMO MODE")
        print(" No AI dependencies required!")
    else:
        print(" SILENT INVIGILATOR — PRODUCTION MODE")
    print("-" * 60)
    print(" Default Logins:")
    print("   Admin:    admin / admin123")
    print("   Teacher:  teacher / teacher123")
    print("-" * 60)
    print(f" URL: http://localhost:5000")
    print("=" * 60)
    
    # Initialize camera globally for background threads
    get_camera()
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
