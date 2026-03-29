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
import uuid
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from flask_socketio import SocketIO, emit, join_room

# ── DEMO MODE ────────────────────────────────────────────
# Set to True for presentation — uses simulated AI detection
DEMO_MODE = True

app = Flask(__name__)
app.secret_key = 'silent-invigilator-secret-key-2026'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

JWT_SECRET = os.getenv('SI_JWT_SECRET', 'silent-invigilator-jwt-secret-2026')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_MINUTES = int(os.getenv('SI_ACCESS_TOKEN_MINUTES', '30'))
REFRESH_TOKEN_DAYS = int(os.getenv('SI_REFRESH_TOKEN_DAYS', '7'))

ROLE_ADMIN = 'admin'
ROLE_INVIGILATOR = 'invigilator'

# ── DATABASE & LOGGING ───────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(__file__), 'invigilator.db')

def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA busy_timeout=30000')
    # Roles table
    c.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  description TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    # Logs table
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, 
                  risk_score INTEGER, 
                  event_type TEXT, 
                  description TEXT,
                  student_id INTEGER,
                  alert_level TEXT,
                  escalation TEXT)''')

    # Backward-compatible migration for pre-existing DBs
    cols = {row[1] for row in c.execute("PRAGMA table_info(logs)").fetchall()}
    if 'student_id' not in cols:
        c.execute('ALTER TABLE logs ADD COLUMN student_id INTEGER')
    if 'alert_level' not in cols:
        c.execute('ALTER TABLE logs ADD COLUMN alert_level TEXT')
    if 'escalation' not in cols:
        c.execute('ALTER TABLE logs ADD COLUMN escalation TEXT')

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT UNIQUE NOT NULL, 
                  password TEXT NOT NULL, 
                  role TEXT NOT NULL DEFAULT 'teacher', 
                  full_name TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    # Add compatibility columns for security and role mapping
    user_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
    if 'email' not in user_cols:
        c.execute('ALTER TABLE users ADD COLUMN email TEXT')
    if 'role_id' not in user_cols:
        c.execute('ALTER TABLE users ADD COLUMN role_id INTEGER')
    if 'is_active' not in user_cols:
        c.execute('ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1')
    if 'last_login_at' not in user_cols:
        c.execute('ALTER TABLE users ADD COLUMN last_login_at TEXT')

    # Exam sessions
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sessions
                 (id TEXT PRIMARY KEY,
                  exam_name TEXT NOT NULL,
                  class_name TEXT NOT NULL,
                  camera_source TEXT NOT NULL,
                  assigned_invigilator_id INTEGER,
                  status TEXT NOT NULL DEFAULT 'scheduled',
                  start_time TEXT,
                  end_time TEXT,
                  created_by INTEGER,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(created_by) REFERENCES users(id),
                  FOREIGN KEY(assigned_invigilator_id) REFERENCES users(id))''')

    # Session assignments
    c.execute('''CREATE TABLE IF NOT EXISTS session_assignments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  invigilator_id INTEGER NOT NULL,
                  assigned_by INTEGER,
                  assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(session_id, invigilator_id),
                  FOREIGN KEY(session_id) REFERENCES exam_sessions(id),
                  FOREIGN KEY(invigilator_id) REFERENCES users(id),
                  FOREIGN KEY(assigned_by) REFERENCES users(id))''')

    # Alerts table (session-isolated)
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  student_track_id INTEGER,
                  alert_type TEXT NOT NULL,
                  confidence_score REAL NOT NULL,
                  risk_score REAL,
                  severity TEXT NOT NULL,
                  dedupe_key TEXT,
                  message TEXT,
                  evidence_frame_uri TEXT,
                  acknowledged_by INTEGER,
                  acknowledged_at TEXT,
                  occurred_at TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  generated_by TEXT,
                  FOREIGN KEY(session_id) REFERENCES exam_sessions(id),
                  FOREIGN KEY(acknowledged_by) REFERENCES users(id))''')

    # Tracking summary table
    c.execute('''CREATE TABLE IF NOT EXISTS student_tracking
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  track_id INTEGER NOT NULL,
                  student_label TEXT,
                  first_seen_at TEXT,
                  last_seen_at TEXT,
                  avg_risk_score REAL DEFAULT 0,
                  max_risk_score REAL DEFAULT 0,
                  UNIQUE(session_id, track_id),
                  FOREIGN KEY(session_id) REFERENCES exam_sessions(id))''')

    # Delivery log for routed realtime alerts
    c.execute('''CREATE TABLE IF NOT EXISTS alert_delivery_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  alert_id TEXT NOT NULL,
                  recipient_user_id INTEGER NOT NULL,
                  channel TEXT NOT NULL,
                  delivered_at TEXT,
                  status TEXT NOT NULL,
                  FOREIGN KEY(alert_id) REFERENCES alerts(id),
                  FOREIGN KEY(recipient_user_id) REFERENCES users(id))''')

    # Full audit logs
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  actor_user_id INTEGER,
                  action TEXT NOT NULL,
                  resource_type TEXT,
                  resource_id TEXT,
                  ip_address TEXT,
                  user_agent TEXT,
                  metadata TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(actor_user_id) REFERENCES users(id))''')

    # Refresh token storage
    c.execute('''CREATE TABLE IF NOT EXISTS refresh_tokens
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  token_hash TEXT UNIQUE NOT NULL,
                  expires_at TEXT NOT NULL,
                  revoked_at TEXT,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Access token denylist (JWT jti revocation)
    c.execute('''CREATE TABLE IF NOT EXISTS access_token_denylist
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  jti TEXT UNIQUE NOT NULL,
                  expires_at TEXT NOT NULL,
                  revoked_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    # Indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_exam_sessions_status_time ON exam_sessions(status, start_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_session_assignments_user ON session_assignments(invigilator_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_alerts_session_time ON alerts(session_id, occurred_at DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_alerts_session_severity ON alerts(session_id, severity, occurred_at DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracking_session_track ON student_tracking(session_id, track_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_user_time ON activity_logs(actor_user_id, created_at DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_token_denylist_jti ON access_token_denylist(jti)')

    # Seed base roles
    c.execute('INSERT OR IGNORE INTO roles(name, description) VALUES (?, ?)', (ROLE_ADMIN, 'System Administrator'))
    c.execute('INSERT OR IGNORE INTO roles(name, description) VALUES (?, ?)', (ROLE_INVIGILATOR, 'Exam Invigilator'))
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=30000')
    return conn

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_role(role):
    role = (role or '').strip().lower()
    if role == 'teacher':
        return ROLE_INVIGILATOR
    return role

def _legacy_sha256(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, stored_hash):
    if not stored_hash:
        return False
    try:
        if stored_hash.startswith('$2a$') or stored_hash.startswith('$2b$') or stored_hash.startswith('$2y$'):
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return False
    return _legacy_sha256(password) == stored_hash

def build_access_token(user_row):
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_row['id']),
        'username': user_row['username'],
        'role': normalize_role(user_row['role']),
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def build_refresh_token():
    return secrets.token_urlsafe(48)

def store_refresh_token(user_id, raw_refresh_token):
    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)).isoformat()
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES (?, ?, ?)',
        (user_id, token_hash, expires_at)
    )
    conn.commit()
    conn.close()

def revoke_refresh_token(raw_refresh_token):
    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
    conn = get_db_connection()
    conn.execute(
        'UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL',
        (utc_now_iso(), token_hash)
    )
    conn.commit()
    conn.close()

def find_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,)).fetchone()
    conn.close()
    return row

def decode_access_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def is_access_token_revoked(jti):
    if not jti:
        return False
    conn = get_db_connection()
    row = conn.execute('SELECT 1 FROM access_token_denylist WHERE jti = ? LIMIT 1', (jti,)).fetchone()
    conn.close()
    return row is not None


def revoke_access_token_jti(jti, expires_ts):
    if not jti:
        return
    expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat() if expires_ts else utc_now_iso()
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO access_token_denylist(jti, expires_at) VALUES (?, ?)', (jti, expires_at))
    conn.commit()
    conn.close()

def extract_bearer_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth.split(' ', 1)[1].strip()
    return None

def log_activity(actor_user_id, action, resource_type=None, resource_id=None, metadata=None):
    try:
        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO activity_logs(actor_user_id, action, resource_type, resource_id, ip_address, user_agent, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                actor_user_id,
                action,
                resource_type,
                str(resource_id) if resource_id is not None else None,
                request.remote_addr,
                request.headers.get('User-Agent', ''),
                json.dumps(metadata) if metadata else None,
            )
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def is_user_assigned_to_session(user_id, role, session_id):
    role = normalize_role(role)
    if role == ROLE_ADMIN:
        return True
    conn = get_db_connection()
    row = conn.execute(
        'SELECT 1 FROM session_assignments WHERE session_id = ? AND invigilator_id = ? LIMIT 1',
        (session_id, user_id)
    ).fetchone()
    conn.close()
    return row is not None

def get_session_status(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT status FROM exam_sessions WHERE id = ? LIMIT 1', (session_id,)).fetchone()
    conn.close()
    return row['status'] if row else None

def get_session_camera_source(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT camera_source FROM exam_sessions WHERE id = ? LIMIT 1', (session_id,)).fetchone()
    conn.close()
    raw = row['camera_source'] if row and row['camera_source'] else 'camera_0'
    try:
        from camera import parse_camera_index
        idx = parse_camera_index(raw, default=0)
        return f'camera_{idx}'
    except Exception:
        return raw

def get_active_camera_session(camera_source='camera_0'):
    conn = get_db_connection()
    row = conn.execute(
        '''SELECT id FROM exam_sessions
           WHERE status = 'active' AND camera_source = ?
           ORDER BY start_time DESC LIMIT 1''',
        (camera_source,)
    ).fetchone()
    conn.close()
    return row['id'] if row else None

def resolve_camera_source_for_session(session_id):
    qs_source = (request.args.get('camera_source') or '').strip()
    if qs_source:
        return qs_source
    return get_session_camera_source(session_id)

def get_latest_active_session_for_user(user_id, role):
    role = normalize_role(role)
    conn = get_db_connection()
    if role == ROLE_ADMIN:
        row = conn.execute(
            "SELECT id FROM exam_sessions WHERE status = 'active' ORDER BY start_time DESC, updated_at DESC LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute(
            '''SELECT s.id
               FROM exam_sessions s
               JOIN session_assignments sa ON sa.session_id = s.id
               WHERE s.status = 'active' AND sa.invigilator_id = ?
               ORDER BY s.start_time DESC, s.updated_at DESC
               LIMIT 1''',
            (user_id,)
        ).fetchone()
    conn.close()
    return row['id'] if row else None

def jwt_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_bearer_token()
        if not token:
            return jsonify({'error': 'Missing bearer token'}), 401
        try:
            payload = decode_access_token(token)
            if is_access_token_revoked(payload.get('jti')):
                return jsonify({'error': 'Token revoked'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401

        user = find_user_by_id(payload.get('sub'))
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401

        request.jwt_user = {
            'id': int(user['id']),
            'username': user['username'],
            'role': normalize_role(user['role']),
        }
        return f(*args, **kwargs)
    return decorated

def api_role_required(*roles):
    norm_roles = {normalize_role(r) for r in roles}
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, 'jwt_user', None)
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401
            if user['role'] not in norm_roles:
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def seed_users():
    """Create default users if none exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    existing = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    seeded_count = 0
    if existing == 0:
        default_users = [
            ('admin', hash_password('admin123'), ROLE_ADMIN, 'Administrator'),
            ('sarah', hash_password('sarah123'), ROLE_INVIGILATOR, 'Dr. Sarah Mitchell'),
            ('james', hash_password('james123'), ROLE_INVIGILATOR, 'Prof. James Wilson'),
            ('elena', hash_password('elena123'), ROLE_INVIGILATOR, 'Ms. Elena Rodriguez'),
            ('robert', hash_password('robert123'), ROLE_INVIGILATOR, 'Mr. Robert Chen'),
        ]

        for uname, pwd, role, fname in default_users:
            conn.execute(
                'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
                (uname, pwd, role, fname)
            )
        conn.commit()
        seeded_count = len(default_users)

    # Backfill role_id for existing rows
    role_map = {r['name']: r['id'] for r in conn.execute('SELECT id, name FROM roles').fetchall()}
    conn.execute('UPDATE users SET role_id = ? WHERE role = ? OR role = ?', (role_map.get(ROLE_ADMIN), ROLE_ADMIN, 'admin'))
    conn.execute('UPDATE users SET role_id = ? WHERE role = ? OR role = ?', (role_map.get(ROLE_INVIGILATOR), ROLE_INVIGILATOR, 'teacher'))
    conn.execute("UPDATE users SET role = ? WHERE role = 'teacher'", (ROLE_INVIGILATOR,))
    conn.commit()
    conn.close()
    if seeded_count:
        print(f"[INIT] Seeded {seeded_count} default users")

# ── AUTH HELPERS ──────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    allowed_roles = {normalize_role(r) for r in roles}
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if normalize_role(session.get('role')) not in allowed_roles:
                return redirect(url_for('get_dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── GLOBAL CAMERA ────────────────────────────────────────
_camera      = None
_camera_lock = threading.Lock()

def get_camera(init=True, camera_source=None):
    global _camera
    with _camera_lock:
        if _camera is None and init:
            if DEMO_MODE:
                from camera import DemoCamera
                _camera = DemoCamera()
            else:
                from camera import VideoCamera
                _camera = VideoCamera()
        if _camera is not None and camera_source is not None and hasattr(_camera, 'set_camera_source'):
            try:
                _camera.set_camera_source(camera_source)
            except Exception:
                pass
    return _camera


def get_runtime_camera_source():
    cam = get_camera(init=False)
    if cam and hasattr(cam, 'get_camera_source'):
        try:
            return cam.get_camera_source()
        except Exception:
            pass
    return 'camera_0'

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

                def persist_structured_alert(session_id, student_track_id, alert_type, confidence_score, severity, message, risk_score):
                    if not session_id:
                        return
                    alert_id = str(uuid.uuid4())
                    occurred_at = utc_now_iso()
                    if not conn:
                        return
                    conn.execute(
                        '''INSERT INTO alerts
                           (id, session_id, student_track_id, alert_type, confidence_score, risk_score, severity, message, occurred_at, generated_by)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            alert_id,
                            session_id,
                            student_track_id,
                            alert_type,
                            float(confidence_score),
                            float(risk_score),
                            severity,
                            message,
                            occurred_at,
                            'silent-invigilator-camera',
                        )
                    )
                    socketio.emit('alert.created', {
                        'id': alert_id,
                        'session_id': session_id,
                        'student_track_id': student_track_id,
                        'alert_type': alert_type,
                        'confidence_score': float(confidence_score),
                        'risk_score': float(risk_score),
                        'severity': severity,
                        'message': message,
                        'occurred_at': occurred_at,
                    }, to=f'session:{session_id}')

                # Persist per-student cooldown/escalation alerts emitted by camera pipeline
                if hasattr(cam, 'pop_alert_events'):
                    events = cam.pop_alert_events()
                    if events:
                        conn = get_db_connection()
                        with conn:
                            for ev in events:
                                session_id = ev.get('session_id') or get_active_camera_session(get_runtime_camera_source())
                                conn.execute(
                                    """INSERT INTO logs
                                       (timestamp, risk_score, event_type, description, student_id, alert_level, escalation)
                                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (
                                        ev.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S')),
                                        int(ev.get('risk_score', 0)),
                                        ev.get('event_type', 'STUDENT ALERT'),
                                        ev.get('description', 'Per-student suspicious behavior detected'),
                                        ev.get('student_id'),
                                        ev.get('alert_level', 'medium'),
                                        ev.get('escalation', 'repeat'),
                                    )
                                )

                                persist_structured_alert(
                                    session_id=session_id,
                                    student_track_id=ev.get('student_id'),
                                    alert_type=ev.get('event_type', 'behavior').upper().replace(' ', '_'),
                                    confidence_score=float(ev.get('risk_score', 0)),
                                    severity=str(ev.get('alert_level', 'medium')).upper(),
                                    message=ev.get('description', 'Per-student suspicious behavior detected'),
                                    risk_score=float(ev.get('risk_score', 0)),
                                )
                        print(f"[LOG] Saved {len(events)} per-student alerts")
                
                # Check specific critical events first
                if cam.phone_detected and (now - last_log['phone'] > COOLDOWN):
                    conn = get_db_connection()
                    with conn:
                        conn.execute("""INSERT INTO logs
                                        (timestamp, risk_score, event_type, description, alert_level, escalation)
                                        VALUES (?, ?, ?, ?, ?, ?)""",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 80), 'PROHIBITED OBJECT (PHONE)', 'PHONE DETECTED - Mobile device on camera', 'high', 'repeat'))
                        persist_structured_alert(
                            session_id=get_active_camera_session(get_runtime_camera_source()),
                            student_track_id=None,
                            alert_type='OBJECT',
                            confidence_score=max(cam.anomaly_score, 80),
                            severity='HIGH',
                            message='PHONE DETECTED - Mobile device on camera',
                            risk_score=max(cam.anomaly_score, 80),
                        )
                        last_log['phone'] = now
                        print(f"[LOG] Alert saved: PHONE DETECTED ({cam.anomaly_score})")

                elif any("Material" in x for x in getattr(cam, 'detections', [])) and (now - last_log['material'] > COOLDOWN):
                    if not conn: conn = get_db_connection()
                    with conn:
                        conn.execute("""INSERT INTO logs
                                        (timestamp, risk_score, event_type, description, alert_level, escalation)
                                        VALUES (?, ?, ?, ?, ?, ?)""",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 60), 'SUSPICIOUS MATERIAL', 'Book or Paper detected on camera', 'medium', 'repeat'))
                        persist_structured_alert(
                            session_id=get_active_camera_session(get_runtime_camera_source()),
                            student_track_id=None,
                            alert_type='OBJECT',
                            confidence_score=max(cam.anomaly_score, 60),
                            severity='MEDIUM',
                            message='Book or Paper detected on camera',
                            risk_score=max(cam.anomaly_score, 60),
                        )
                        last_log['material'] = now
                        print(f"[LOG] Alert saved: MATERIAL DETECTED ({cam.anomaly_score})")

                elif not getattr(cam, 'face_detected', False) and len(getattr(cam, 'cached_persons', [])) > 0 and (now - last_log['missing'] > COOLDOWN):
                    if not conn: conn = get_db_connection()
                    with conn:
                        conn.execute("""INSERT INTO logs
                                        (timestamp, risk_score, event_type, description, alert_level, escalation)
                                        VALUES (?, ?, ?, ?, ?, ?)""",
                                     (time.strftime('%Y-%m-%d %H:%M:%S'), max(cam.anomaly_score, 50), 'FACE HIDDEN', 'Person detected but face is invisible/hidden', 'medium', 'repeat'))
                        persist_structured_alert(
                            session_id=get_active_camera_session(get_runtime_camera_source()),
                            student_track_id=None,
                            alert_type='BEHAVIOR',
                            confidence_score=max(cam.anomaly_score, 50),
                            severity='MEDIUM',
                            message='Person detected but face is invisible/hidden',
                            risk_score=max(cam.anomaly_score, 50),
                        )
                        last_log['missing'] = now
                        print(f"[LOG] Alert saved: FACE HIDDEN ({cam.anomaly_score})")

                # Fallback to general high anomaly score
                elif cam.anomaly_score > 60 and (now - last_log['general'] > COOLDOWN):
                    # Only log general anomaly if we didn't just log a specific one
                    if (now - max(last_log.values())) > 5:
                        if not conn: conn = get_db_connection()
                        with conn:
                            desc = ", ".join(cam.detections) if cam.detections else "High Anomaly Score detected (Aggregated behaviors)"
                            conn.execute("""INSERT INTO logs
                                            (timestamp, risk_score, event_type, description, alert_level, escalation)
                                            VALUES (?, ?, ?, ?, ?, ?)""",
                                         (time.strftime('%Y-%m-%d %H:%M:%S'), cam.anomaly_score, 'Suspicious Behavior', desc, 'medium', 'repeat'))
                            persist_structured_alert(
                                session_id=get_active_camera_session(get_runtime_camera_source()),
                                student_track_id=None,
                                alert_type='BEHAVIOR',
                                confidence_score=cam.anomaly_score,
                                severity='MEDIUM',
                                message=desc,
                                risk_score=cam.anomaly_score,
                            )
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
        role = normalize_role(role)
        
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (user,)).fetchone()
        matched = row and verify_password(pwd, row['password'])
        role_ok = row and normalize_role(row['role']) == role

        # Backward compatibility: allow old teacher role selector value
        if row and role == ROLE_INVIGILATOR and normalize_role(row['role']) == ROLE_INVIGILATOR:
            role_ok = True

        if matched and role_ok:
            if not row['password'].startswith('$2'):
                conn.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(pwd), row['id']))
            conn.execute('UPDATE users SET last_login_at = ? WHERE id = ?', (utc_now_iso(), row['id']))
            conn.commit()
        conn.close()
        
        if matched and role_ok:
            session['user'] = row['username']
            session['role'] = normalize_role(row['role'])
            session['full_name'] = row['full_name']
            session['user_id'] = row['id']
            session.permanent = True
            log_activity(row['id'], 'LOGIN', 'USER', row['id'])
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
    role = normalize_role(session.get('role', ''))
    if role == ROLE_ADMIN:
        return redirect(url_for('admin_dashboard'))
    elif role == ROLE_INVIGILATOR:
        return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

# ── ADMIN ROUTES ─────────────────────────────────────────

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    monitor_session_id = get_latest_active_session_for_user(session.get('user_id'), session.get('role'))
    monitor_url = f"/monitor?session_id={monitor_session_id}" if monitor_session_id else None
    return render_template('admin_dashboard.html', monitor_url=monitor_url)

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
    role = normalize_role(role)
    full_name = data.get('full_name', '').strip()
    
    if not all([username, password, role, full_name]):
        return jsonify({'error': 'All fields are required'}), 400
    
    if role not in [ROLE_ADMIN, ROLE_INVIGILATOR]:
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
@role_required(ROLE_INVIGILATOR)
def teacher_dashboard():
    monitor_session_id = get_latest_active_session_for_user(session.get('user_id'), session.get('role'))
    monitor_url = f"/monitor?session_id={monitor_session_id}" if monitor_session_id else None
    return render_template('teacher_dashboard_new.html', monitor_url=monitor_url)

# ── MONITORING ──────────────────────────────────────────

@app.route('/monitor')
@login_required
def monitor():
    """Live monitoring view — accessible by teacher and admin."""
    role = normalize_role(session.get('role'))
    user_id = session.get('user_id')
    if role not in [ROLE_INVIGILATOR, ROLE_ADMIN]:
        return redirect(url_for('get_dashboard'))

    session_id = request.args.get('session_id')
    if not session_id:
        return "session_id required", 400

    if not is_user_assigned_to_session(user_id, role, session_id):
        return "Forbidden", 403

    status = get_session_status(session_id)
    if status != 'active':
        return "Session is not active", 409

    log_activity(user_id, 'VIEW_SESSION', 'EXAM_SESSION', session_id)
    return render_template('monitor.html', session_id=session_id)


@app.route('/api/cameras', methods=['GET'])
@login_required
def api_list_cameras_web():
    session_id = request.args.get('session_id', '').strip()
    role = normalize_role(session.get('role'))
    user_id = session.get('user_id')

    if session_id:
        if not is_user_assigned_to_session(user_id, role, session_id):
            return jsonify({'error': 'Forbidden'}), 403

    from camera import list_available_cameras
    cameras = list_available_cameras(max_index=6)

    selected = None
    if session_id:
        selected = get_session_camera_source(session_id)
    if not selected:
        cam = get_camera(init=False)
        if cam and hasattr(cam, 'get_camera_source'):
            try:
                selected = cam.get_camera_source()
            except Exception:
                selected = None
    if not selected:
        selected = 'camera_0'

    return jsonify({'cameras': cameras, 'selected_source': selected})


@app.route('/api/sessions/<session_id>/camera-source', methods=['PATCH'])
@login_required
def api_set_session_camera_source_web(session_id):
    role = normalize_role(session.get('role'))
    user_id = session.get('user_id')
    if role not in (ROLE_ADMIN, ROLE_INVIGILATOR):
        return jsonify({'error': 'Forbidden'}), 403
    if not is_user_assigned_to_session(user_id, role, session_id):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json(silent=True) or {}
    source = (data.get('camera_source') or '').strip()
    if not source:
        return jsonify({'error': 'camera_source is required'}), 400

    conn = get_db_connection()
    row = conn.execute('SELECT id FROM exam_sessions WHERE id = ?', (session_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    conn.execute('UPDATE exam_sessions SET camera_source = ?, updated_at = ? WHERE id = ?', (source, utc_now_iso(), session_id))
    conn.commit()
    conn.close()

    cam = get_camera(init=False)
    if cam and hasattr(cam, 'set_camera_source'):
        try:
            cam.set_camera_source(source)
        except Exception:
            pass

    log_activity(user_id, 'UPDATE_CAMERA_SOURCE', 'EXAM_SESSION', session_id, {'camera_source': source})
    return jsonify({'session_id': session_id, 'camera_source': source})

# ── API ENDPOINTS ────────────────────────────────────────

@app.route('/api/alerts')
@login_required
def get_alerts():
    limit = request.args.get('limit', 50, type=int)
    session_id = request.args.get('session_id')
    role = normalize_role(session.get('role'))
    user_id = session.get('user_id')

    conn = get_db_connection()
    if role == ROLE_ADMIN:
        if session_id:
            rows = conn.execute(
                '''SELECT a.id, a.occurred_at as timestamp, CAST(a.risk_score AS INTEGER) as risk_score,
                          a.alert_type as event_type, a.message as description,
                          a.student_track_id as student_id, lower(a.severity) as alert_level,
                          CASE WHEN a.acknowledged_at IS NULL THEN 'repeat' ELSE 'acknowledged' END as escalation
                   FROM alerts a
                   WHERE a.session_id = ?
                   ORDER BY a.occurred_at DESC LIMIT ?''',
                (session_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                '''SELECT a.id, a.occurred_at as timestamp, CAST(a.risk_score AS INTEGER) as risk_score,
                          a.alert_type as event_type, a.message as description,
                          a.student_track_id as student_id, lower(a.severity) as alert_level,
                          CASE WHEN a.acknowledged_at IS NULL THEN 'repeat' ELSE 'acknowledged' END as escalation
                   FROM alerts a
                   ORDER BY a.occurred_at DESC LIMIT ?''',
                (limit,)
            ).fetchall()
    else:
        if session_id:
            rows = conn.execute(
                '''SELECT a.id, a.occurred_at as timestamp, CAST(a.risk_score AS INTEGER) as risk_score,
                          a.alert_type as event_type, a.message as description,
                          a.student_track_id as student_id, lower(a.severity) as alert_level,
                          CASE WHEN a.acknowledged_at IS NULL THEN 'repeat' ELSE 'acknowledged' END as escalation
                   FROM alerts a
                   JOIN session_assignments sa ON sa.session_id = a.session_id
                   WHERE sa.invigilator_id = ? AND a.session_id = ?
                   ORDER BY a.occurred_at DESC LIMIT ?''',
                (user_id, session_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                '''SELECT a.id, a.occurred_at as timestamp, CAST(a.risk_score AS INTEGER) as risk_score,
                          a.alert_type as event_type, a.message as description,
                          a.student_track_id as student_id, lower(a.severity) as alert_level,
                          CASE WHEN a.acknowledged_at IS NULL THEN 'repeat' ELSE 'acknowledged' END as escalation
                   FROM alerts a
                   JOIN session_assignments sa ON sa.session_id = a.session_id
                   WHERE sa.invigilator_id = ?
                   ORDER BY a.occurred_at DESC LIMIT ?''',
                (user_id, limit)
            ).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats')
@login_required
def get_stats():
    role = normalize_role(session.get('role'))
    user_id = session.get('user_id')
    conn = get_db_connection()
    if role == ROLE_ADMIN:
        total = conn.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
        critical = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 70").fetchone()[0]
        warnings = conn.execute("SELECT COUNT(*) FROM logs WHERE risk_score >= 40 AND risk_score < 70").fetchone()[0]

        type_dist = conn.execute(
            'SELECT event_type, COUNT(*) as cnt FROM logs GROUP BY event_type ORDER BY cnt DESC'
        ).fetchall()

        hourly = conn.execute(
            "SELECT substr(timestamp, 12, 2) as hour, COUNT(*) as cnt, AVG(risk_score) as avg_score FROM logs GROUP BY hour ORDER BY hour"
        ).fetchall()
    else:
        total = conn.execute(
            '''SELECT COUNT(*) FROM alerts a
               JOIN session_assignments sa ON sa.session_id = a.session_id
               WHERE sa.invigilator_id = ?''',
            (user_id,)
        ).fetchone()[0]
        critical = conn.execute(
            '''SELECT COUNT(*) FROM alerts a
               JOIN session_assignments sa ON sa.session_id = a.session_id
               WHERE sa.invigilator_id = ? AND a.severity = 'HIGH' ''',
            (user_id,)
        ).fetchone()[0]
        warnings = conn.execute(
            '''SELECT COUNT(*) FROM alerts a
               JOIN session_assignments sa ON sa.session_id = a.session_id
               WHERE sa.invigilator_id = ? AND a.severity = 'MEDIUM' ''',
            (user_id,)
        ).fetchone()[0]

        type_dist = conn.execute(
            '''SELECT a.alert_type as event_type, COUNT(*) as cnt
               FROM alerts a
               JOIN session_assignments sa ON sa.session_id = a.session_id
               WHERE sa.invigilator_id = ?
               GROUP BY a.alert_type
               ORDER BY cnt DESC''',
            (user_id,)
        ).fetchall()

        hourly = conn.execute(
            '''SELECT substr(a.occurred_at, 12, 2) as hour, COUNT(*) as cnt, AVG(a.risk_score) as avg_score
               FROM alerts a
               JOIN session_assignments sa ON sa.session_id = a.session_id
               WHERE sa.invigilator_id = ?
               GROUP BY hour ORDER BY hour''',
            (user_id,)
        ).fetchall()
    
    conn.close()
    
    return jsonify({
        'total_alerts': total,
        'critical_alerts': critical,
        'warning_alerts': warnings,
        'type_distribution': [{'type': r['event_type'], 'count': r['cnt']} for r in type_dist],
        'hourly_trend': [{'hour': r['hour'], 'count': r['cnt'], 'avg_score': round(r['avg_score'], 1)} for r in hourly],
    })


# ── SECURE API V2 (JWT + SESSION ISOLATION) ─────────────────

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400

    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,)).fetchone()
    if not row or not verify_password(password, row['password']):
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401

    # Transparent migration from legacy SHA-256 to bcrypt
    if not row['password'].startswith('$2'):
        try:
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(password), row['id']))
        except sqlite3.OperationalError:
            pass

    refresh_token = build_refresh_token()
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)).isoformat()
    conn.execute(
        'INSERT INTO refresh_tokens(user_id, token_hash, expires_at) VALUES (?, ?, ?)',
        (row['id'], token_hash, expires_at)
    )
    access_token = build_access_token(row)
    try:
        conn.execute('UPDATE users SET last_login_at = ? WHERE id = ?', (utc_now_iso(), row['id']))
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
    conn.close()

    log_activity(row['id'], 'LOGIN', 'USER', row['id'])

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in_minutes': ACCESS_TOKEN_MINUTES,
        'user': {
            'id': row['id'],
            'username': row['username'],
            'role': normalize_role(row['role']),
            'full_name': row['full_name'],
        }
    })


@app.route('/api/auth/refresh', methods=['POST'])
def api_refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refresh_token', '')
    if not refresh_token:
        return jsonify({'error': 'refresh_token required'}), 400

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    conn = get_db_connection()
    row = conn.execute(
        '''SELECT rt.*, u.id as uid FROM refresh_tokens rt
           JOIN users u ON u.id = rt.user_id
           WHERE rt.token_hash = ? AND rt.revoked_at IS NULL AND u.is_active = 1''',
        (token_hash,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Invalid refresh token'}), 401

    if datetime.fromisoformat(row['expires_at']) < datetime.now(timezone.utc):
        conn.close()
        return jsonify({'error': 'Refresh token expired'}), 401

    user = conn.execute('SELECT * FROM users WHERE id = ?', (row['user_id'],)).fetchone()
    conn.close()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    return jsonify({'access_token': build_access_token(user), 'token_type': 'Bearer'})


@app.route('/api/auth/logout', methods=['POST'])
@jwt_required_api
def api_logout():
    token = extract_bearer_token()
    if token:
        try:
            payload = decode_access_token(token)
            revoke_access_token_jti(payload.get('jti'), payload.get('exp'))
        except Exception:
            pass
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refresh_token', '')
    if refresh_token:
        revoke_refresh_token(refresh_token)
    log_activity(request.jwt_user['id'], 'LOGOUT', 'USER', request.jwt_user['id'])
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
@jwt_required_api
def api_me():
    return jsonify(request.jwt_user)


@app.route('/api/invigilators', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_list_invigilators():
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT id, username, full_name FROM users WHERE role = ? AND is_active = 1 ORDER BY full_name',
        (ROLE_INVIGILATOR,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/roles', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_roles():
    conn = get_db_connection()
    rows = conn.execute('SELECT id, name, description, created_at FROM roles ORDER BY id').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/users', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_users_list():
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT u.id, u.username, u.email, u.full_name, u.role, u.role_id, u.is_active, u.last_login_at, u.created_at
           FROM users u ORDER BY u.id'''
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/users', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_users_create():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip() or None
    full_name = (data.get('full_name') or '').strip()
    password = (data.get('password') or '').strip()
    role = normalize_role(data.get('role'))
    if not username or not full_name or not password or role not in (ROLE_ADMIN, ROLE_INVIGILATOR):
        return jsonify({'error': 'username, full_name, password, role are required'}), 400

    conn = get_db_connection()
    role_row = conn.execute('SELECT id FROM roles WHERE name = ?', (role,)).fetchone()
    role_id = role_row['id'] if role_row else None
    try:
        conn.execute(
            '''INSERT INTO users(username, email, password, full_name, role, role_id, is_active)
               VALUES (?, ?, ?, ?, ?, ?, 1)''',
            (username, email, hash_password(password), full_name, role, role_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'username/email already exists'}), 409

    new_id = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()['id']
    conn.close()
    log_activity(request.jwt_user['id'], 'CREATE_USER', 'USER', new_id, {'role': role})
    return jsonify({'id': new_id, 'username': username, 'role': role}), 201


@app.route('/api/users/<int:user_id>', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_users_patch(user_id):
    data = request.get_json(silent=True) or {}
    updates = []
    vals = []
    conn = get_db_connection()

    if 'full_name' in data:
        updates.append('full_name = ?')
        vals.append((data.get('full_name') or '').strip())
    if 'email' in data:
        updates.append('email = ?')
        vals.append((data.get('email') or '').strip() or None)
    if 'is_active' in data:
        updates.append('is_active = ?')
        vals.append(1 if bool(data.get('is_active')) else 0)
    if 'role' in data:
        role = normalize_role(data.get('role'))
        if role not in (ROLE_ADMIN, ROLE_INVIGILATOR):
            conn.close()
            return jsonify({'error': 'Invalid role'}), 400
        role_row = conn.execute('SELECT id FROM roles WHERE name = ?', (role,)).fetchone()
        updates.append('role = ?')
        vals.append(role)
        updates.append('role_id = ?')
        vals.append(role_row['id'] if role_row else None)
    if 'password' in data and (data.get('password') or '').strip():
        updates.append('password = ?')
        vals.append(hash_password((data.get('password') or '').strip()))

    if not updates:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400

    vals.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(vals))
    conn.commit()
    row = conn.execute('SELECT id, username, email, full_name, role, is_active FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'User not found'}), 404
    log_activity(request.jwt_user['id'], 'PATCH_USER', 'USER', user_id)
    return jsonify(dict(row))


@app.route('/api/sessions', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_create_session():
    data = request.get_json(silent=True) or {}
    exam_name = (data.get('exam_name') or '').strip()
    class_name = (data.get('class_name') or '').strip()
    invigilator_id = data.get('invigilator_id')
    camera_source = (data.get('camera_source') or 'camera_0').strip()

    if not exam_name or not class_name or not invigilator_id:
        return jsonify({'error': 'exam_name, class_name, invigilator_id are required'}), 400

    session_id = str(uuid.uuid4())
    now = utc_now_iso()
    conn = get_db_connection()
    inv = conn.execute(
        'SELECT id FROM users WHERE id = ? AND role = ? AND is_active = 1',
        (invigilator_id, ROLE_INVIGILATOR)
    ).fetchone()
    if not inv:
        conn.close()
        return jsonify({'error': 'Invigilator not found'}), 404

    conn.execute(
        '''INSERT INTO exam_sessions
           (id, exam_name, class_name, camera_source, assigned_invigilator_id, status, created_by, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?)''',
        (session_id, exam_name, class_name, camera_source, invigilator_id, request.jwt_user['id'], now, now)
    )
    conn.execute(
        'INSERT INTO session_assignments(session_id, invigilator_id, assigned_by) VALUES (?, ?, ?)',
        (session_id, invigilator_id, request.jwt_user['id'])
    )
    conn.commit()
    conn.close()

    log_activity(request.jwt_user['id'], 'CREATE_SESSION', 'EXAM_SESSION', session_id, {
        'invigilator_id': invigilator_id,
        'camera_source': camera_source,
    })

    return jsonify({'session_id': session_id, 'status': 'scheduled'})


@app.route('/api/sessions', methods=['GET'])
@jwt_required_api
def api_list_sessions():
    user = request.jwt_user
    conn = get_db_connection()
    if user['role'] == ROLE_ADMIN:
        rows = conn.execute('SELECT * FROM exam_sessions ORDER BY created_at DESC').fetchall()
    else:
        rows = conn.execute(
            '''SELECT s.* FROM exam_sessions s
               JOIN session_assignments a ON a.session_id = s.id
               WHERE a.invigilator_id = ?
               ORDER BY s.created_at DESC''',
            (user['id'],)
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/sessions/<session_id>', methods=['GET'])
@jwt_required_api
def api_get_session(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM exam_sessions WHERE id = ?', (session_id,)).fetchone()
    assigns = conn.execute(
        '''SELECT sa.invigilator_id, u.username, u.full_name
           FROM session_assignments sa JOIN users u ON u.id = sa.invigilator_id
           WHERE sa.session_id = ?''',
        (session_id,)
    ).fetchall()
    conn.close()
    if not row:
        return jsonify({'error': 'Session not found'}), 404
    payload = dict(row)
    payload['assignments'] = [dict(a) for a in assigns]
    return jsonify(payload)


@app.route('/api/sessions/<session_id>/assignments', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_add_assignment(session_id):
    data = request.get_json(silent=True) or {}
    invigilator_id = data.get('invigilator_id')
    if not invigilator_id:
        return jsonify({'error': 'invigilator_id is required'}), 400
    conn = get_db_connection()
    sess = conn.execute('SELECT id FROM exam_sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    inv = conn.execute('SELECT id FROM users WHERE id = ? AND role = ? AND is_active = 1', (invigilator_id, ROLE_INVIGILATOR)).fetchone()
    if not inv:
        conn.close()
        return jsonify({'error': 'Invigilator not found'}), 404
    conn.execute(
        'INSERT OR IGNORE INTO session_assignments(session_id, invigilator_id, assigned_by) VALUES (?, ?, ?)',
        (session_id, invigilator_id, request.jwt_user['id'])
    )
    conn.execute('UPDATE exam_sessions SET assigned_invigilator_id = ?, updated_at = ? WHERE id = ?', (invigilator_id, utc_now_iso(), session_id))
    conn.commit()
    conn.close()
    log_activity(request.jwt_user['id'], 'ASSIGN_INVIGILATOR', 'EXAM_SESSION', session_id, {'invigilator_id': invigilator_id})
    return jsonify({'success': True})


@app.route('/api/sessions/<session_id>/assignments/<int:user_id>', methods=['DELETE'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_remove_assignment(session_id, user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM session_assignments WHERE session_id = ? AND invigilator_id = ?', (session_id, user_id))
    conn.commit()
    conn.close()
    log_activity(request.jwt_user['id'], 'UNASSIGN_INVIGILATOR', 'EXAM_SESSION', session_id, {'invigilator_id': user_id})
    return jsonify({'success': True})


@app.route('/api/sessions/<session_id>/live-token', methods=['GET'])
@jwt_required_api
def api_live_token(session_id):
    user = request.jwt_user
    status = get_session_status(session_id)
    if status is None:
        return jsonify({'error': 'Session not found'}), 404
    if status != 'active':
        return jsonify({'error': 'Session is not active'}), 409
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403

    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user['id']),
        'session_id': session_id,
        'role': user['role'],
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=5)).timestamp()),
        'scope': 'live_feed',
        'jti': str(uuid.uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return jsonify({'live_token': token, 'expires_in_seconds': 300})


@app.route('/api/sessions/<session_id>/start', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_start_session(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id FROM exam_sessions WHERE id = ?', (session_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    now = utc_now_iso()
    conn.execute(
        "UPDATE exam_sessions SET status = 'active', start_time = COALESCE(start_time, ?), updated_at = ? WHERE id = ?",
        (now, now, session_id)
    )
    conn.commit()
    conn.close()
    log_activity(request.jwt_user['id'], 'START_SESSION', 'EXAM_SESSION', session_id)
    socketio.emit('session.status_changed', {'session_id': session_id, 'status': 'active'}, to=f'session:{session_id}')
    return jsonify({'session_id': session_id, 'status': 'active'})


@app.route('/api/sessions/<session_id>/complete', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_complete_session(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id FROM exam_sessions WHERE id = ?', (session_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    now = utc_now_iso()
    conn.execute(
        "UPDATE exam_sessions SET status = 'completed', end_time = ?, updated_at = ? WHERE id = ?",
        (now, now, session_id)
    )
    conn.commit()
    conn.close()
    log_activity(request.jwt_user['id'], 'COMPLETE_SESSION', 'EXAM_SESSION', session_id)
    socketio.emit('session.status_changed', {'session_id': session_id, 'status': 'completed'}, to=f'session:{session_id}')
    return jsonify({'session_id': session_id, 'status': 'completed'})


@app.route('/api/sessions/<session_id>/alerts', methods=['GET'])
@jwt_required_api
def api_session_alerts(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    limit = min(request.args.get('limit', 100, type=int), 500)
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM alerts WHERE session_id = ? ORDER BY occurred_at DESC LIMIT ?',
        (session_id, limit)
    ).fetchall()
    conn.close()
    log_activity(user['id'], 'VIEW_SESSION_ALERTS', 'EXAM_SESSION', session_id)
    return jsonify([dict(r) for r in rows])


@app.route('/api/sessions/<session_id>/report', methods=['GET'])
@jwt_required_api
def api_session_report(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403

    conn = get_db_connection()
    summary = conn.execute(
        '''SELECT COUNT(*) as total,
                  SUM(CASE WHEN severity='HIGH' THEN 1 ELSE 0 END) as high_count,
                  SUM(CASE WHEN severity='MEDIUM' THEN 1 ELSE 0 END) as medium_count,
                  SUM(CASE WHEN severity='LOW' THEN 1 ELSE 0 END) as low_count
           FROM alerts WHERE session_id = ?''',
        (session_id,)
    ).fetchone()
    top_students = conn.execute(
        '''SELECT student_track_id, COUNT(*) as alert_count, MAX(risk_score) as max_risk, AVG(risk_score) as avg_risk
           FROM alerts
           WHERE session_id = ? AND student_track_id IS NOT NULL
           GROUP BY student_track_id
           ORDER BY max_risk DESC, alert_count DESC
           LIMIT 10''',
        (session_id,)
    ).fetchall()
    timeline = conn.execute(
        '''SELECT substr(occurred_at, 1, 16) as bucket, COUNT(*) as count
           FROM alerts WHERE session_id = ?
           GROUP BY bucket ORDER BY bucket''',
        (session_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        'session_id': session_id,
        'summary': dict(summary) if summary else {},
        'top_suspicious_students': [dict(r) for r in top_students],
        'timeline': [dict(r) for r in timeline],
    })


@app.route('/api/sessions/<session_id>/alerts/stats', methods=['GET'])
@jwt_required_api
def api_session_alert_stats(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    row = conn.execute(
        '''SELECT COUNT(*) as total,
                  SUM(CASE WHEN severity='HIGH' THEN 1 ELSE 0 END) as high,
                  SUM(CASE WHEN severity='MEDIUM' THEN 1 ELSE 0 END) as medium,
                  SUM(CASE WHEN severity='LOW' THEN 1 ELSE 0 END) as low,
                  AVG(risk_score) as avg_risk
           FROM alerts WHERE session_id = ?''',
        (session_id,)
    ).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {'total': 0, 'high': 0, 'medium': 0, 'low': 0, 'avg_risk': 0})


@app.route('/api/sessions/<session_id>/timeline', methods=['GET'])
@jwt_required_api
def api_session_timeline(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT substr(occurred_at, 1, 16) as minute_bucket,
                  COUNT(*) as alerts,
                  SUM(CASE WHEN severity='HIGH' THEN 1 ELSE 0 END) as high_count
           FROM alerts
           WHERE session_id = ?
           GROUP BY minute_bucket
           ORDER BY minute_bucket''',
        (session_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/sessions/<session_id>/top-suspicious', methods=['GET'])
@jwt_required_api
def api_session_top_suspicious(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT student_track_id,
                  COUNT(*) as total_alerts,
                  MAX(risk_score) as max_risk,
                  AVG(risk_score) as avg_risk
           FROM alerts
           WHERE session_id = ? AND student_track_id IS NOT NULL
           GROUP BY student_track_id
           ORDER BY max_risk DESC, total_alerts DESC
           LIMIT 20''',
        (session_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/sessions/<session_id>/heatmap', methods=['GET'])
@jwt_required_api
def api_session_heatmap(session_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT student_track_id, CAST(substr(occurred_at, 12, 2) AS INTEGER) as hour,
                  COUNT(*) as intensity
           FROM alerts
           WHERE session_id = ? AND student_track_id IS NOT NULL
           GROUP BY student_track_id, hour
           ORDER BY intensity DESC''',
        (session_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/sessions/<session_id>/alerts/<alert_id>/ack', methods=['POST'])
@jwt_required_api
def api_ack_alert(session_id, alert_id):
    user = request.jwt_user
    if not is_user_assigned_to_session(user['id'], user['role'], session_id):
        return jsonify({'error': 'Forbidden'}), 403
    now = utc_now_iso()
    conn = get_db_connection()
    row = conn.execute('SELECT id FROM alerts WHERE id = ? AND session_id = ?', (alert_id, session_id)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Alert not found'}), 404
    conn.execute(
        'UPDATE alerts SET acknowledged_by = ?, acknowledged_at = ? WHERE id = ?',
        (user['id'], now, alert_id)
    )
    conn.commit()
    conn.close()
    log_activity(user['id'], 'ALERT_ACK', 'ALERT', alert_id, {'session_id': session_id})
    socketio.emit('alert.acknowledged', {'session_id': session_id, 'alert_id': alert_id, 'user_id': user['id']}, to=f'session:{session_id}')
    return jsonify({'success': True})


@app.route('/api/audit/logs', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_audit_logs():
    limit = min(request.args.get('limit', 200, type=int), 1000)
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT al.*, u.username
           FROM activity_logs al
           LEFT JOIN users u ON u.id = al.actor_user_id
           ORDER BY al.created_at DESC
           LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/audit/logs/session/<session_id>', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def api_audit_logs_session(session_id):
    limit = min(request.args.get('limit', 200, type=int), 1000)
    conn = get_db_connection()
    rows = conn.execute(
        '''SELECT al.*, u.username
           FROM activity_logs al
           LEFT JOIN users u ON u.id = al.actor_user_id
           WHERE al.resource_type = 'EXAM_SESSION' AND al.resource_id = ?
           ORDER BY al.created_at DESC
           LIMIT ?''',
        (session_id, limit)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# Auth aliases requested in enterprise API contract
@app.route('/auth/login', methods=['POST'])
def api_login_alias():
    return api_login()


@app.route('/auth/refresh', methods=['POST'])
def api_refresh_alias():
    return api_refresh()


@app.route('/auth/logout', methods=['POST'])
@jwt_required_api
def api_logout_alias():
    return api_logout()


@app.route('/auth/me', methods=['GET'])
@jwt_required_api
def api_me_alias():
    return api_me()


# Full route aliases for contract compatibility without /api prefix
@app.route('/roles', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def roles_alias():
    return api_roles()


@app.route('/users', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def users_list_alias():
    return api_users_list()


@app.route('/users', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def users_create_alias():
    return api_users_create()


@app.route('/users/<int:user_id>', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def users_patch_alias(user_id):
    return api_users_patch(user_id)


@app.route('/sessions', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def sessions_create_alias():
    return api_create_session()


@app.route('/sessions', methods=['GET'])
@jwt_required_api
def sessions_list_alias():
    return api_list_sessions()


@app.route('/sessions/<session_id>', methods=['GET'])
@jwt_required_api
def sessions_get_alias(session_id):
    return api_get_session(session_id)


@app.route('/sessions/<session_id>/start', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def sessions_start_alias(session_id):
    return api_start_session(session_id)


@app.route('/sessions/<session_id>/complete', methods=['PATCH'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def sessions_complete_alias(session_id):
    return api_complete_session(session_id)


@app.route('/sessions/<session_id>/assignments', methods=['POST'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def sessions_add_assignment_alias(session_id):
    return api_add_assignment(session_id)


@app.route('/sessions/<session_id>/assignments/<int:user_id>', methods=['DELETE'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def sessions_remove_assignment_alias(session_id, user_id):
    return api_remove_assignment(session_id, user_id)


@app.route('/sessions/<session_id>/live-token', methods=['GET'])
@jwt_required_api
def sessions_live_token_alias(session_id):
    return api_live_token(session_id)


@app.route('/sessions/<session_id>/stream', methods=['GET'])
def sessions_stream_alias(session_id):
    return api_session_stream(session_id)


@app.route('/sessions/<session_id>/alerts', methods=['GET'])
@jwt_required_api
def sessions_alerts_alias(session_id):
    return api_session_alerts(session_id)


@app.route('/sessions/<session_id>/alerts/stats', methods=['GET'])
@jwt_required_api
def sessions_alerts_stats_alias(session_id):
    return api_session_alert_stats(session_id)


@app.route('/sessions/<session_id>/alerts/<alert_id>/ack', methods=['POST'])
@jwt_required_api
def sessions_alert_ack_alias(session_id, alert_id):
    return api_ack_alert(session_id, alert_id)


@app.route('/sessions/<session_id>/report', methods=['GET'])
@jwt_required_api
def sessions_report_alias(session_id):
    return api_session_report(session_id)


@app.route('/sessions/<session_id>/timeline', methods=['GET'])
@jwt_required_api
def sessions_timeline_alias(session_id):
    return api_session_timeline(session_id)


@app.route('/sessions/<session_id>/top-suspicious', methods=['GET'])
@jwt_required_api
def sessions_top_suspicious_alias(session_id):
    return api_session_top_suspicious(session_id)


@app.route('/sessions/<session_id>/heatmap', methods=['GET'])
@jwt_required_api
def sessions_heatmap_alias(session_id):
    return api_session_heatmap(session_id)


@app.route('/audit/logs', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def audit_logs_alias():
    return api_audit_logs()


@app.route('/audit/logs/session/<session_id>', methods=['GET'])
@jwt_required_api
@api_role_required(ROLE_ADMIN)
def audit_logs_session_alias(session_id):
    return api_audit_logs_session(session_id)


@app.route('/internal/ai/alerts', methods=['POST'])
def internal_ai_alert_alias():
    return api_internal_ai_alert()


@app.route('/api/internal/ai/alerts', methods=['POST'])
def api_internal_ai_alert():
    api_key = request.headers.get('X-Internal-Api-Key', '')
    expected = os.getenv('SI_INTERNAL_API_KEY', 'silent-invigilator-internal')
    if api_key != expected:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    required = ['session_id', 'alert_type', 'confidence_score', 'severity', 'message']
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    session_id = data['session_id']
    conn = get_db_connection()
    session_row = conn.execute('SELECT * FROM exam_sessions WHERE id = ? AND status = ?', (session_id, 'active')).fetchone()
    if not session_row:
        conn.close()
        return jsonify({'error': 'Session not active'}), 404

    severity = str(data['severity']).upper()
    dedupe_key = data.get('dedupe_key')
    # Alert cooldown + dedupe within 15s, unless escalation to higher severity
    if dedupe_key:
        prev = conn.execute(
            '''SELECT id, severity, occurred_at FROM alerts
               WHERE session_id = ? AND dedupe_key = ?
               ORDER BY occurred_at DESC LIMIT 1''',
            (session_id, dedupe_key)
        ).fetchone()
        if prev:
            prev_ts = datetime.fromisoformat(prev['occurred_at']) if 'T' in prev['occurred_at'] else None
            now_utc = datetime.now(timezone.utc)
            elapsed = (now_utc - prev_ts).total_seconds() if prev_ts else 999
            rank = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
            escalation = rank.get(severity, 0) > rank.get((prev['severity'] or '').upper(), 0)
            if elapsed < 15 and not escalation:
                conn.close()
                return jsonify({'success': True, 'deduped': True, 'reason': 'cooldown'})

    alert_id = str(uuid.uuid4())
    occurred_at = data.get('occurred_at') or utc_now_iso()
    conn.execute(
        '''INSERT INTO alerts
           (id, session_id, student_track_id, alert_type, confidence_score, risk_score, severity, dedupe_key, message, evidence_frame_uri, occurred_at, generated_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            alert_id,
            session_id,
            data.get('student_track_id'),
            data['alert_type'],
            float(data['confidence_score']),
            float(data.get('risk_score', data['confidence_score'])),
            severity,
            dedupe_key,
            data['message'],
            data.get('evidence_frame_uri'),
            occurred_at,
            data.get('generated_by', 'ai-engine')
        )
    )
    conn.commit()
    conn.close()

    payload = {
        'id': alert_id,
        'session_id': session_id,
        'student_track_id': data.get('student_track_id'),
        'alert_type': data['alert_type'],
        'confidence_score': float(data['confidence_score']),
        'risk_score': float(data.get('risk_score', data['confidence_score'])),
        'severity': severity,
        'message': data['message'],
        'occurred_at': occurred_at,
    }
    socketio.emit('alert.created', payload, to=f'session:{session_id}')
    return jsonify({'success': True, 'alert_id': alert_id})

@app.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    conn = get_db_connection()
    conn.execute('DELETE FROM logs')
    conn.commit()
    conn.close()
    return redirect(url_for('get_dashboard'))

# ── VIDEO STREAMING ──────────────────────────────────────

def generate_frames(camera_source=None):
    camera = get_camera(camera_source=camera_source)
    while True:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def get_request_identity():
    # Prefer JWT identity for API clients
    token = extract_bearer_token()
    if token:
        try:
            payload = decode_access_token(token)
            user = find_user_by_id(payload.get('sub'))
            if user:
                return {'id': int(user['id']), 'role': normalize_role(user['role']), 'username': user['username']}
        except Exception:
            return None

    # Fallback to existing cookie session
    if 'user_id' in session:
        return {
            'id': int(session.get('user_id')),
            'role': normalize_role(session.get('role')),
            'username': session.get('user'),
        }
    return None


def ensure_live_access(session_id):
    identity = get_request_identity()
    if not identity:
        return None, ("Unauthorized", 401)
    if not session_id:
        return None, ("session_id required", 400)
    status = get_session_status(session_id)
    if status is None:
        return None, ("Session not found", 404)
    if status != 'active':
        return None, ("Session is not active", 409)
    if not is_user_assigned_to_session(identity['id'], identity['role'], session_id):
        return None, ("Forbidden", 403)
    return identity, None


def validate_live_token(live_token, session_id):
    if not live_token:
        return False, 'Missing live token'
    try:
        payload = decode_access_token(live_token)
    except jwt.ExpiredSignatureError:
        return False, 'Live token expired'
    except Exception:
        return False, 'Invalid live token'

    if payload.get('scope') != 'live_feed':
        return False, 'Invalid token scope'
    if payload.get('session_id') != session_id:
        return False, 'Session mismatch'
    status = get_session_status(session_id)
    if status is None:
        return False, 'Session not found'
    if status != 'active':
        return False, 'Session is not active'
    if is_access_token_revoked(payload.get('jti')):
        return False, 'Token revoked'
    user = find_user_by_id(payload.get('sub'))
    if not user:
        return False, 'Invalid user'
    if not is_user_assigned_to_session(int(user['id']), normalize_role(user['role']), session_id):
        return False, 'Forbidden'
    return True, {'id': int(user['id']), 'role': normalize_role(user['role']), 'username': user['username']}

@app.route('/video_feed')
def video_feed():
    session_id = request.args.get('session_id')
    identity, err = ensure_live_access(session_id)
    if err:
        return err
    camera_source = resolve_camera_source_for_session(session_id)
    log_activity(identity['id'], 'VIEW_SESSION', 'EXAM_SESSION', session_id, {'endpoint': 'video_feed', 'camera_source': camera_source})
    return Response(generate_frames(camera_source=camera_source), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/sessions/<session_id>/stream', methods=['GET'])
def api_session_stream(session_id):
    live_token = request.args.get('live_token', '')
    ok, result = validate_live_token(live_token, session_id)
    if not ok:
        return jsonify({'error': result}), 401 if 'token' in result.lower() else 403
    identity = result
    camera_source = resolve_camera_source_for_session(session_id)
    log_activity(identity['id'], 'VIEW_SESSION', 'EXAM_SESSION', session_id, {'endpoint': 'session_stream', 'camera_source': camera_source})
    return Response(generate_frames(camera_source=camera_source), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    session_id = request.args.get('session_id')
    identity, err = ensure_live_access(session_id)
    if err:
        return err
    camera_source = resolve_camera_source_for_session(session_id)
    camera = get_camera(camera_source=camera_source)
    log_activity(identity['id'], 'VIEW_SESSION', 'EXAM_SESSION', session_id, {'endpoint': 'status', 'camera_source': camera_source})
    return jsonify(camera.get_stats())


@socketio.on('join_session')
def ws_join_session(data):
    token = (data or {}).get('token')
    session_id = (data or {}).get('session_id')
    if not token or not session_id:
        emit('error', {'message': 'token and session_id are required'})
        return

    try:
        payload = decode_access_token(token)
        user = find_user_by_id(payload.get('sub'))
        if not user:
            emit('error', {'message': 'Invalid user'})
            return
        status = get_session_status(session_id)
        if status is None:
            emit('error', {'message': 'Session not found'})
            return
        if status != 'active':
            emit('error', {'message': 'Session is not active'})
            return
        if not is_user_assigned_to_session(int(user['id']), normalize_role(user['role']), session_id):
            emit('error', {'message': 'Forbidden'})
            return
        join_room(f'session:{session_id}')
        emit('joined', {'session_id': session_id})
        log_activity(int(user['id']), 'WS_JOIN_SESSION', 'EXAM_SESSION', session_id)
    except Exception:
        emit('error', {'message': 'Invalid token'})

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
    print("   Admin:       admin / admin123")
    print("   Invigilator: sarah / sarah123")
    print("-" * 60)
    print(f" URL: http://localhost:5000")
    print("=" * 60)
    
    # Camera is initialized lazily on first stream request.
    # This avoids startup blocking if AI models/webcam take time to initialize.
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
