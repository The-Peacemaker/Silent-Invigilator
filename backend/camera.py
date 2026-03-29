"""
THE SILENT INVIGILATOR — Camera & AI Processing Module
======================================================
Architecture:
  - Thread 1 (Worker): Captures frames + runs AI (MediaPipe + YOLO)
  - Main Thread (Flask): Serves latest processed JPEG via get_frame()

All heavy objects (VideoCapture, FaceMesh, YOLO) are created INSIDE
the worker thread to avoid Windows COM / threading crashes.
"""

import cv2
import numpy as np
import threading
import time
import os
import re
from collections import deque

try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
except Exception:
    AutoDetectionModel = None
    get_sliced_prediction = None


YOLO_MODEL_PATH = 'yolov8n.pt' if os.path.exists('yolov8n.pt') else 'yolov8s.pt'


def parse_camera_index(camera_source, default=0):
    if camera_source is None:
        return default
    s = str(camera_source).strip().lower()
    if s in ("", "default", "default_camera", "laptop", "integrated", "internal"):
        return 0
    if s in ("webcam", "external", "usb"):
        return 1
    m = re.match(r"^camera_(\d+)$", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return default


def _camera_candidates(requested_index, max_index=5):
    candidates = [requested_index, 0, 1, 2, 3, 4]
    uniq = []
    for c in candidates:
        if c not in uniq and 0 <= c < max_index:
            uniq.append(c)
    return uniq


def list_available_cameras(max_index=5):
    available = []
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    for idx in range(max_index):
        opened = False
        for backend in backends:
            cap = None
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap is not None and cap.isOpened():
                    opened = True
                    cap.release()
                    break
            except Exception:
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
        if opened:
            if idx == 0:
                name = "Laptop Camera (Built-in)"
            elif idx == 1:
                name = "Webcam (External USB)"
            else:
                name = f"External Camera {idx}"
            available.append({"id": f"camera_{idx}", "index": idx, "name": name})
    if not available:
        available = [{"id": "camera_0", "index": 0, "name": "Laptop Camera (Built-in)"}]
    return available


def _clamp_bbox(x1, y1, x2, y2, w, h):
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(0, min(int(x2), w - 1))
    y2 = max(0, min(int(y2), h - 1))
    if x2 <= x1:
        x2 = min(w - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(h - 1, y1 + 1)
    return (x1, y1, x2, y2)


def _bbox_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def _bbox_iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = _bbox_area(a) + _bbox_area(b) - inter
    if union <= 0:
        return 0.0
    return inter / union


def _risk_tier(score):
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _draw_modern_box(frame, x1, y1, x2, y2, label, color):
    """Draws a futuristic, professional bounding box with corner brackets and a clean label."""
    # Settings
    thickness = 2
    corner_length = max(15, int(0.15 * min(x2 - x1, y2 - y1)))  # dynamic corner size
    
    # 1. Draw subtle background tint for the box area
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)

    # 2. Draw Corner Brackets (Top-left)
    cv2.line(frame, (x1, y1), (x1 + corner_length, y1), color, thickness)
    cv2.line(frame, (x1, y1), (x1, y1 + corner_length), color, thickness)
    
    # Bottom-left
    cv2.line(frame, (x1, y2), (x1 + corner_length, y2), color, thickness)
    cv2.line(frame, (x1, y2), (x1, y2 - corner_length), color, thickness)
    
    # Top-right
    cv2.line(frame, (x2, y1), (x2 - corner_length, y1), color, thickness)
    cv2.line(frame, (x2, y1), (x2, y1 + corner_length), color, thickness)
    
    # Bottom-right
    cv2.line(frame, (x2, y2), (x2 - corner_length, y2), color, thickness)
    cv2.line(frame, (x2, y2), (x2, y2 - corner_length), color, thickness)

    # 3. Draw clean label box at the top
    (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(frame, (x1, y1 - text_h - 10), (x1 + text_w + 10, y1), color, -1)
    
    # Label text (white or inverted depending on brightness)
    cv2.putText(frame, label, (x1 + 5, y1 - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

class VideoCamera:
    def __init__(self):
        print("[CAMERA] Initializing Silent Invigilator AI Engine...")

        # ── Shared State (read by Flask, written by worker) ─────
        self.lock = threading.Lock()
        self.output_frame = None          # Latest JPEG bytes
        self.stopped = False
        self.last_access = 0.0

        # Detection metrics (atomic-ish writes in CPython GIL)
        self.frame_count = 0
        self.anomaly_score = 0
        self.detections = []
        self.face_detected = False
        self.phone_detected = False
        self.current_pose = "Center"
        self.gaze_direction = "Center"

        # Smoothing buffers
        self.yaw_buffer = deque(maxlen=5)
        self.pitch_buffer = deque(maxlen=5)
        self.score_history = deque(maxlen=12)

        # Cached YOLO results (persist between YOLO runs)
        self.cached_persons = []
        self.cached_phones = []
        self.cached_books = []

        # Runtime camera source state
        self.requested_camera_index = 0
        self.active_camera_index = None

        # ── Launch Worker Thread ────────────────────────────────
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def __del__(self):
        self.stopped = True

    def set_camera_source(self, camera_source):
        self.requested_camera_index = parse_camera_index(camera_source, default=0)

    def get_camera_source(self):
        idx = self.active_camera_index if self.active_camera_index is not None else self.requested_camera_index
        return f"camera_{idx}"

    # ════════════════════════════════════════════════════════════
    #  WORKER THREAD — captures + processes frames
    # ════════════════════════════════════════════════════════════
    def _worker_loop(self):
        """
        Runs entirely in its own thread.
        Creates camera & AI models HERE to avoid Windows threading issues.
        """

        # ── 1. Init (thread-local) ───────────────────────
        print("[CAMERA] Worker started. Waiting for stream request...")
        cap = None
        has_cam = False

        # ── 2. Load MediaPipe FaceMesh (thread-local) ───────────
        face_mesh = None
        try:
            import mediapipe as mp
            face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("[CAMERA] MediaPipe FaceMesh loaded OK")
        except Exception as e:
            print(f"[CAMERA] MediaPipe FAILED: {e}  (head pose disabled)")

        # ── 3. Load YOLO (thread-local) ─────────────────────────
        yolo = None
        try:
            from ultralytics import YOLO
            yolo = YOLO(YOLO_MODEL_PATH)
            print("[CAMERA] YOLOv8s loaded OK")
        except Exception as e:
            print(f"[CAMERA] YOLO FAILED: {e}  (phone detection disabled)")

        print("[CAMERA] ✓ AI Engine ready. Processing frames...")

        # ── 4. Main Processing Loop ─────────────────────────────
        while not self.stopped:
            try:
                now = time.time()
                is_active = (now - self.last_access) < 5.0
                
                if is_active and not has_cam:
                    print("[CAMERA] Hardware requested. Opening webcam...")
                    for cam_idx in _camera_candidates(self.requested_camera_index):
                        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                            try:
                                cap = cv2.VideoCapture(cam_idx, backend)
                                if cap.isOpened():
                                    print(f"[CAMERA] Opened camera {cam_idx} with backend {backend}")
                                    self.active_camera_index = cam_idx
                                    break
                            except: pass
                        if cap is not None and cap.isOpened():
                            break
                    has_cam = cap is not None and cap.isOpened()
                    if has_cam:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    else:
                        print("[CAMERA] WARNING: Could not open camera hardware!")
                
                elif not is_active and has_cam:
                    print("[CAMERA] Hardware idle. Releasing webcam...")
                    cap.release()
                    has_cam = False
                    self.active_camera_index = None
                    with self.lock:
                        self.output_frame = None

                if has_cam and self.active_camera_index is not None and self.active_camera_index != self.requested_camera_index:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                    has_cam = False
                    self.active_camera_index = None

                if not has_cam:
                    time.sleep(0.1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                self.frame_count += 1
                h, w = frame.shape[:2]

                risk = 0
                det_list = []

                # ─── YOLO Object Detection (every 15th frame) ───
                if yolo and self.frame_count % 15 == 0:
                    try:
                        results = yolo.predict(
                            frame,
                            classes=[0, 67, 73],   # person, phone, book
                            conf=0.20,             # High sensitivity
                            verbose=False,
                            imgsz=320              # Small = fast
                        )
                        phones, books, persons = [], [], []
                        for r in results:
                            for box in r.boxes:
                                cls = int(box.cls[0])
                                c = box.xyxy[0].cpu().numpy().astype(int)
                                if cls == 67:   phones.append(c)
                                elif cls == 73: books.append(c)
                                elif cls == 0:  persons.append(c)
                        self.cached_phones = phones
                        self.cached_books = books
                        self.cached_persons = persons
                    except Exception as e:
                        print(f"[CAMERA] YOLO error: {e}")

                # Draw cached YOLO results
                phone_now = False
                for (x1, y1, x2, y2) in self.cached_phones:
                    _draw_modern_box(frame, x1, y1, x2, y2, "PROHIBITED: PHONE", (0, 0, 255))
                    risk = max(risk, 100)  # INSTANT MAX RISK
                    det_list.append("PHONE DETECTED")
                    phone_now = True

                for (x1, y1, x2, y2) in self.cached_books:
                    _draw_modern_box(frame, x1, y1, x2, y2, "SUSPICIOUS: PAPER/BOOK", (0, 165, 255))
                    risk += 30
                    det_list.append("Material Detected")

                # ─── MediaPipe Face Analysis (every frame) ───────
                face_found = False
                if face_mesh:
                    try:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        res = face_mesh.process(rgb)

                        if res.multi_face_landmarks:
                            face_found = True
                            lm = res.multi_face_landmarks[0].landmark

                            # Head Pose
                            pitch, yaw = self._head_pose(lm, w, h)
                            self.yaw_buffer.append(yaw)
                            self.pitch_buffer.append(pitch)
                            avg_yaw = float(np.mean(self.yaw_buffer))
                            avg_pitch = float(np.mean(self.pitch_buffer))

                            # Classify pose
                            pose = "Center"
                            if avg_yaw > 25:
                                pose = "Right"
                                risk += 15
                                det_list.append("Head Turn (Right)")
                            elif avg_yaw < -25:
                                pose = "Left"
                                risk += 15
                                det_list.append("Head Turn (Left)")
                            if avg_pitch > 15:
                                pose = "Down"
                                risk += 20
                                det_list.append("Looking Down")

                            self.current_pose = pose

                            # Gaze
                            gaze = self._gaze(lm)
                            self.gaze_direction = gaze

                            # Draw nose dot
                            nx = int(lm[1].x * w)
                            ny = int(lm[1].y * h)
                            cv2.circle(frame, (nx, ny), 4, (0, 255, 255), -1)

                    except Exception as e:
                        pass  # Silently skip bad frames

                # If person visible but no face => suspicious
                if not face_found and len(self.cached_persons) > 0:
                    risk += 10
                    det_list.append("Face Hidden")

                # ─── Update Shared State ─────────────────────────
                self.score_history.append(risk)
                
                # If a phone is detected, bypass the moving average smoothing
                if phone_now:
                    self.anomaly_score = 100
                    self.score_history[-1] = 100
                else:
                    self.anomaly_score = int(np.mean(self.score_history))
                    
                self.face_detected = face_found
                self.phone_detected = phone_now
                self.detections = list(set(det_list))

                # ─── Draw HUD Overlay ────────────────────────────
                col = (0, 255, 0)
                if self.anomaly_score > 60:
                    col = (0, 0, 255)
                elif self.anomaly_score > 30:
                    col = (0, 165, 255)

                # Risk bar at top
                cv2.rectangle(frame, (0, 0), (w, 32), (0, 0, 0), -1)
                bar_w = int(w * self.anomaly_score / 100)
                if bar_w > 0:
                    overlay_bar = frame.copy()
                    cv2.rectangle(overlay_bar, (0, 0), (bar_w, 32), col, -1)
                    cv2.addWeighted(overlay_bar, 0.4, frame, 0.6, 0, frame)
                    
                # Clean text with background for readability
                cv2.putText(frame, f"RISK: {self.anomaly_score}%", (10, 22), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"POSE: {self.current_pose}", (140, 22), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                # Person count
                cv2.putText(frame, f"PERSONS: {len(self.cached_persons)}",
                            (w - 120, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (255, 255, 255), 1)

                # ─── Encode & Store ──────────────────────────────
                _, jpeg = cv2.imencode('.jpg', frame,
                                       [cv2.IMWRITE_JPEG_QUALITY, 65])
                with self.lock:
                    self.output_frame = jpeg.tobytes()

            except Exception as e:
                print(f"[CAMERA] Frame error: {e}")
                time.sleep(0.05)

        # Cleanup
        cap.release()
        if face_mesh:
            face_mesh.close()
        print("[CAMERA] Worker stopped.")

    # ════════════════════════════════════════════════════════════
    #  PUBLIC API — called from Flask threads
    # ════════════════════════════════════════════════════════════
    def get_frame(self):
        """Returns latest JPEG bytes (non-blocking)."""
        self.last_access = time.time()
        with self.lock:
            if self.output_frame:
                return self.output_frame

        # Still initializing — show loading screen
        blank = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(blank, "STARTING AI ENGINE...", (120, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 0), 2)
        cv2.putText(blank, "Please wait...", (220, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        _, jpeg = cv2.imencode('.jpg', blank)
        return jpeg.tobytes()

    def get_stats(self):
        """Returns detection data for dashboard API."""
        y = float(np.mean(self.yaw_buffer)) if self.yaw_buffer else 0.0
        p = float(np.mean(self.pitch_buffer)) if self.pitch_buffer else 0.0
        return {
            'risk_score':     self.anomaly_score,
            'face_detected':  self.face_detected,
            'phone_detected': self.phone_detected,
            'head_pose':      self.current_pose,
            'gaze':           self.gaze_direction,
            'yaw':            round(y, 1),
            'pitch':          round(p, 1),
            'detections':     self.detections,
            'persons':        len(self.cached_persons),
            'camera_source':  self.get_camera_source(),
            'audio_level':    0,
        }

    # ════════════════════════════════════════════════════════════
    #  PRIVATE HELPERS
    # ════════════════════════════════════════════════════════════
    def _serve_placeholder(self, msg):
        """Generate a static placeholder frame when camera is unavailable."""
        blank = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(blank, msg, (80, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, jpeg = cv2.imencode('.jpg', blank)
        with self.lock:
            self.output_frame = jpeg.tobytes()

    def _head_pose(self, landmarks, img_w, img_h):
        """solvePnP-based head pose estimation → (pitch, yaw) in degrees."""
        pts_2d = []
        for idx in [1, 152, 33, 263, 61, 291]:
            lm = landmarks[idx]
            pts_2d.append([int(lm.x * img_w), int(lm.y * img_h)])
        pts_2d = np.array(pts_2d, dtype=np.float64)

        pts_3d = np.array([
            (0, 0, 0),           # Nose
            (0, -330, -65),      # Chin
            (-225, 170, -135),   # Left eye
            (225, 170, -135),    # Right eye
            (-150, -150, -125),  # Left mouth
            (150, -150, -125),   # Right mouth
        ], dtype=np.float64)

        cam = np.array([
            [img_w, 0, img_h / 2],
            [0, img_w, img_w / 2],
            [0, 0, 1]
        ], dtype=np.float64)
        dist = np.zeros((4, 1), dtype=np.float64)

        ok, rvec, tvec = cv2.solvePnP(pts_3d, pts_2d, cam, dist)
        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        return angles[0], angles[1]   # pitch, yaw

    def _gaze(self, landmarks):
        """Simple iris-based gaze direction."""
        try:
            ri = landmarks[362]
            ro = landmarks[263]
            iris = landmarks[473]
            d = ro.x - ri.x
            if abs(d) < 1e-6:
                return "Center"
            ratio = (iris.x - ri.x) / d
            if ratio > 0.58:
                return "Left"
            elif ratio < 0.42:
                return "Right"
        except:
            pass
        return "Center"


# ════════════════════════════════════════════════════════════
#  DEMO CAMERA — Uses REAL MediaPipe + Scripted Timeline
#  Real face tracking, real landmarks, real head pose
# ════════════════════════════════════════════════════════════

class DemoCamera:
    """
    Uses REAL MediaPipe FaceMesh for actual face tracking + head pose.
    Skips YOLO (which is broken). Runs real AI detection!
    """

    def __init__(self):
        import mediapipe as mp
        print("[AI] Initializing REAL AI Camera (MediaPipe FaceMesh)...")

        self.lock = threading.Lock()
        self.output_frame = None
        self.stopped = False
        self.last_access = 0.0

        # MediaPipe FaceMesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=3,
            refine_landmarks=True,  # includes iris
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # YOLOv8 for tracking + object detection
        self.yolo = None
        self.sahi_model = None
        try:
            from ultralytics import YOLO
            self.yolo = YOLO(YOLO_MODEL_PATH)
            print("[AI] YOLOv8s loaded OK for DemoCamera")
        except Exception as e:
            print(f"[AI] YOLO FAILED: {e}  (phone detection disabled)")

        # SAHI slicing for far/small object detection (phone/chit)
        if AutoDetectionModel and self.yolo:
            try:
                self.sahi_model = AutoDetectionModel.from_pretrained(
                    model_type='ultralytics',
                    model_path=YOLO_MODEL_PATH,
                    confidence_threshold=0.20,
                    device='cpu'
                )
                print("[AI] SAHI small-object slicing enabled")
            except Exception as e:
                self.sahi_model = None
                print(f"[AI] SAHI unavailable: {e}")

        # Detection state
        self.frame_count = 0
        self.anomaly_score = 0
        self.detections = []
        self.face_detected = False
        self.phone_detected = False
        self.current_pose = "Center"
        self.gaze_direction = "Center"
        self.yaw_buffer = deque(maxlen=8)
        self.pitch_buffer = deque(maxlen=8)
        self.score_history = deque(maxlen=15)
        self.cached_persons = [(100, 80, 540, 400)]
        self.cached_phones = []
        self.cached_books = []

        # Runtime camera source state
        self.requested_camera_index = 0
        self.active_camera_index = None

        # Runtime telemetry
        self.fps = 0.0
        self._last_loop_ts = time.time()

        # Adaptive inference cadence for laptop-grade real-time performance
        self.yolo_interval = 8
        self.tracking_interval = 2
        self.use_bytetrack = True
        self._bytetrack_error_logged = False

        # Multi-person track state (true ByteTrack IDs from Ultralytics tracker)
        self.next_track_id = 1
        self.track_iou_threshold = 0.25
        self.max_track_lost = 30
        self.tracks = {}
        self.students = []
        self.alert_history = deque(maxlen=60)
        self.last_track_frame = {}

        # Per-student alert cooldown/escalation queue for DB logger
        self.alert_lock = threading.Lock()
        self.pending_alert_events = deque(maxlen=300)
        self.alert_state = {}
        self.alert_cooldown_sec = 12

        # 3D model points for head pose estimation (same as VideoCamera)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),        # Nose tip (1)
            (0.0, -330.0, -65.0),    # Chin (152)
            (-225.0, 170.0, -135.0), # Left eye corner (263)
            (225.0, 170.0, -135.0),  # Right eye corner (33)
            (-150.0, -150.0, -125.0),# Left mouth corner (287)
            (150.0, -150.0, -125.0), # Right mouth corner (57)
        ], dtype=np.float64)

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def __del__(self):
        self.stopped = True

    def set_camera_source(self, camera_source):
        self.requested_camera_index = parse_camera_index(camera_source, default=0)

    def get_camera_source(self):
        idx = self.active_camera_index if self.active_camera_index is not None else self.requested_camera_index
        return f"camera_{idx}"

    def _head_pose(self, landmarks, img_w, img_h):
        """Estimate head pose using real MediaPipe landmarks + solvePnP."""
        # Key landmark indices
        indices = [1, 152, 263, 33, 287, 57]
        pts_2d = np.array([
            (landmarks[i].x * img_w, landmarks[i].y * img_h) for i in indices
        ], dtype=np.float64)

        focal_length = img_w
        center = (img_w / 2, img_h / 2)
        cam_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        ok, rvec, tvec = cv2.solvePnP(self.model_points, pts_2d, cam_matrix, dist_coeffs)
        if not ok:
            return 0.0, 0.0
        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        return angles[0] * 360, angles[1] * 360  # pitch, yaw

    def _gaze_direction(self, landmarks, img_w, img_h):
        """Compute gaze direction from pupil position relative to eye corners."""
        # Left eye: 33 (outer), 133 (inner), 468 (iris center)
        # Right eye: 362 (outer), 263 (inner), 473 (iris center)
        try:
            # Left eye
            l_outer = np.array([landmarks[33].x * img_w, landmarks[33].y * img_h])
            l_inner = np.array([landmarks[133].x * img_w, landmarks[133].y * img_h])
            l_iris = np.array([landmarks[468].x * img_w, landmarks[468].y * img_h])
            l_ratio = np.linalg.norm(l_iris - l_outer) / (np.linalg.norm(l_inner - l_outer) + 1e-6)

            # Right eye
            r_outer = np.array([landmarks[362].x * img_w, landmarks[362].y * img_h])
            r_inner = np.array([landmarks[263].x * img_w, landmarks[263].y * img_h])
            r_iris = np.array([landmarks[473].x * img_w, landmarks[473].y * img_h])
            r_ratio = np.linalg.norm(r_iris - r_outer) / (np.linalg.norm(r_inner - r_outer) + 1e-6)

            avg = (l_ratio + r_ratio) / 2
            if avg < 0.40:
                return "Right"
            elif avg > 0.60:
                return "Left"
            else:
                return "Center"
        except:
            return "Center"

    def _update_tracks(self, person_boxes, now_ts):
        """
        Lightweight IoU-based tracker for persistent student IDs.
        This keeps laptop performance high without extra ReID models.
        """
        # Age existing tracks first
        for trk in self.tracks.values():
            trk['lost'] += 1

        unmatched_det = set(range(len(person_boxes)))
        track_ids = list(self.tracks.keys())

        # Greedy association by IoU
        for tid in track_ids:
            best_idx = None
            best_iou = 0.0
            prev_box = self.tracks[tid]['bbox']
            for det_idx in list(unmatched_det):
                iou = _bbox_iou(prev_box, person_boxes[det_idx])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = det_idx

            if best_idx is not None and best_iou >= self.track_iou_threshold:
                box = person_boxes[best_idx]
                trk = self.tracks[tid]
                trk['bbox'] = box
                trk['last_seen'] = now_ts
                trk['lost'] = 0
                unmatched_det.remove(best_idx)

        # Spawn tracks for unmatched detections
        for det_idx in unmatched_det:
            tid = self.next_track_id
            self.next_track_id += 1
            self.tracks[tid] = {
                'id': tid,
                'bbox': person_boxes[det_idx],
                'last_seen': now_ts,
                'lost': 0,
                'gaze_hist': deque(maxlen=90),
                'pose_hist': deque(maxlen=90),
                'risk_hist': deque(maxlen=90),
                'score': 0.0,
                'tier': 'low',
            }

        # Cleanup stale tracks
        stale = [tid for tid, trk in self.tracks.items() if trk['lost'] > self.max_track_lost]
        for tid in stale:
            self.tracks.pop(tid, None)

    def _merge_boxes(self, boxes, iou_thr=0.5):
        merged = []
        for box in boxes:
            keep = True
            for e in merged:
                if _bbox_iou(box, e) >= iou_thr:
                    keep = False
                    break
            if keep:
                merged.append(box)
        return merged

    def _run_bytetrack(self, frame, w, h, now_ts):
        """Run true ByteTrack through Ultralytics tracking API and update self.tracks."""
        if self.yolo is None or not self.use_bytetrack:
            return False
        try:
            results = self.yolo.track(
                frame,
                classes=[0],
                conf=0.25,
                iou=0.45,
                imgsz=384,
                persist=True,
                tracker='bytetrack.yaml',
                verbose=False
            )

            seen = set()
            for r in results:
                if r.boxes is None or r.boxes.xyxy is None:
                    continue
                xyxy = r.boxes.xyxy.cpu().numpy().astype(int)
                ids = r.boxes.id
                for i, b in enumerate(xyxy):
                    if ids is None:
                        continue
                    tid = ids[i]
                    if tid is None:
                        continue
                    tid = int(tid.item())
                    seen.add(tid)
                    box = _clamp_bbox(b[0], b[1], b[2], b[3], w, h)

                    if tid not in self.tracks:
                        self.tracks[tid] = {
                            'id': tid,
                            'bbox': box,
                            'last_seen': now_ts,
                            'lost': 0,
                            'gaze_hist': deque(maxlen=90),
                            'pose_hist': deque(maxlen=90),
                            'risk_hist': deque(maxlen=90),
                            'score': 0.0,
                            'tier': 'low',
                        }
                    else:
                        self.tracks[tid]['bbox'] = box
                        self.tracks[tid]['last_seen'] = now_ts
                        self.tracks[tid]['lost'] = 0

                    self.last_track_frame[tid] = self.frame_count

            # Age non-seen tracks and drop stale
            for tid, trk in list(self.tracks.items()):
                if tid not in seen:
                    trk['lost'] += 1
                if trk['lost'] > self.max_track_lost:
                    self.tracks.pop(tid, None)
                    self.last_track_frame.pop(tid, None)

            return True

        except Exception as e:
            msg = str(e)
            if ('lap' in msg.lower()) or ('bytetrack' in msg.lower()):
                self.use_bytetrack = False
                if not self._bytetrack_error_logged:
                    print("[AI] ByteTrack disabled (missing dependency). Using lightweight tracker fallback.")
                    self._bytetrack_error_logged = True
            else:
                print(f"[AI] ByteTrack error: {e}")
            return False

    def _enqueue_student_alert(self, student, now_ts, phone_hit=False, book_hit=False):
        sid = int(student['id'])
        score = float(student['score'])
        level = _risk_tier(score)
        if level == 'low' and not phone_hit and not book_hit:
            return

        st = self.alert_state.get(sid, {'level': 'low', 'last_emit': 0.0})
        prev_level = st['level']
        last_emit = st['last_emit']
        elapsed = now_ts - last_emit

        rank = {'low': 0, 'medium': 1, 'high': 2}
        is_escalation = rank.get(level, 0) > rank.get(prev_level, 0)
        should_emit = is_escalation or elapsed >= self.alert_cooldown_sec

        if not should_emit:
            st['level'] = level
            self.alert_state[sid] = st
            return

        event_type = f"STUDENT {level.upper()} ALERT"
        reason_parts = []
        if phone_hit:
            reason_parts.append('phone_detected')
        if book_hit:
            reason_parts.append('material_detected')
        if student.get('pose') in ('Left', 'Right', 'Down', 'Up'):
            reason_parts.append(f"pose:{student.get('pose')}")
        if student.get('gaze') in ('Left', 'Right'):
            reason_parts.append(f"gaze:{student.get('gaze')}")
        if not reason_parts:
            reason_parts.append('temporal_behavior_pattern')

        escalation = 'escalated' if is_escalation else 'repeat'
        desc = f"Student #{sid} {level.upper()} ({score:.1f}) [{escalation}] -> " + ', '.join(reason_parts)

        with self.alert_lock:
            self.pending_alert_events.append({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'student_id': sid,
                'risk_score': int(round(score)),
                'alert_level': level,
                'event_type': event_type,
                'description': desc,
                'escalation': escalation,
            })

        st['level'] = level
        st['last_emit'] = now_ts
        self.alert_state[sid] = st

    def pop_alert_events(self):
        """Consume queued per-student alerts for database persistence."""
        with self.alert_lock:
            events = list(self.pending_alert_events)
            self.pending_alert_events.clear()
        return events

    def _compute_track_score(self, trk, phone_hit, book_hit, gaze, pose):
        """Temporal cheating confidence score (0-100) per student track."""
        trk['gaze_hist'].append(gaze)
        trk['pose_hist'].append(pose)

        gaze_hist = list(trk['gaze_hist'])
        pose_hist = list(trk['pose_hist'])
        n = max(1, len(gaze_hist))

        gaze_dev = sum(1 for g in gaze_hist if g not in ('Center', 'Unknown')) / n
        head_dev = sum(1 for p in pose_hist if p in ('Left', 'Right', 'Down', 'Up')) / n
        look_down = sum(1 for p in pose_hist if p == 'Down') / n

        # Sustained suspiciousness in recent short window
        short = 20
        tail_gaze = gaze_hist[-short:] if gaze_hist else []
        tail_pose = pose_hist[-short:] if pose_hist else []
        sustained = 0.0
        if tail_gaze and tail_pose:
            tail_hits = 0
            for i in range(min(len(tail_gaze), len(tail_pose))):
                if tail_gaze[i] in ('Left', 'Right') or tail_pose[i] in ('Down', 'Left', 'Right'):
                    tail_hits += 1
            sustained = tail_hits / max(1, min(len(tail_gaze), len(tail_pose)))

        object_term = 1.0 if phone_hit else (0.45 if book_hit else 0.0)

        raw = (
            0.40 * object_term +
            0.22 * gaze_dev +
            0.16 * head_dev +
            0.14 * look_down +
            0.08 * sustained
        )
        score = float(max(0.0, min(100.0, raw * 100.0)))

        if phone_hit:
            score = max(score, 85.0)

        trk['risk_hist'].append(score)
        trk['score'] = float(np.mean(trk['risk_hist']))
        trk['tier'] = _risk_tier(trk['score'])
        return trk['score']

    def _worker_loop(self):
        """Captures frames, runs AI, tracks multiple students, and computes temporal risk."""
        print("[AI] Worker thread started. Waiting for stream request...")
        cap = None
        has_cam = False

        print("[AI] ✓ REAL AI Camera ready. Running MediaPipe FaceMesh...")

        while not self.stopped:
            try:
                self.frame_count += 1
                now = time.time()

                # True processing FPS (EMA)
                dt = max(1e-3, now - self._last_loop_ts)
                self._last_loop_ts = now
                inst_fps = 1.0 / dt
                self.fps = (0.9 * self.fps + 0.1 * inst_fps) if self.fps > 0 else inst_fps

                is_active = (now - self.last_access) < 5.0

                if is_active and not has_cam:
                    print("[AI] Hardware requested. Opening webcam hardware...")
                    for cam_idx in _camera_candidates(self.requested_camera_index):
                        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                            try:
                                cap = cv2.VideoCapture(cam_idx, backend)
                                if cap.isOpened():
                                    print(f"[AI] Webcam {cam_idx} opened with backend {backend}")
                                    self.active_camera_index = cam_idx
                                    break
                            except Exception:
                                pass
                        if cap is not None and cap.isOpened():
                            break

                    has_cam = cap is not None and cap.isOpened()
                    if has_cam:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    else:
                        print("[AI] ERROR: No webcam available!")

                elif not is_active and has_cam:
                    print("[AI] Stream closed. Releasing webcam hardware...")
                    cap.release()
                    has_cam = False
                    self.active_camera_index = None
                    with self.lock:
                        self.output_frame = None

                if has_cam and self.active_camera_index is not None and self.active_camera_index != self.requested_camera_index:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                    has_cam = False
                    self.active_camera_index = None

                if not has_cam:
                    time.sleep(0.1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.03)
                    continue

                h, w = frame.shape[:2]

                # Publish raw frame immediately so stream never hangs on AI step.
                try:
                    _, quick_jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    with self.lock:
                        self.output_frame = quick_jpeg.tobytes()
                except Exception:
                    pass

                # ─── True ByteTrack person tracking (persistent IDs) ───
                if self.frame_count % self.tracking_interval == 0:
                    tracked = self._run_bytetrack(frame, w, h, now)
                    if not tracked and self.yolo is not None:
                        # Fallback: detect persons + lightweight IoU tracking.
                        try:
                            person_boxes = []
                            res_person = self.yolo.predict(
                                frame,
                                classes=[0],
                                conf=0.25,
                                verbose=False,
                                imgsz=320
                            )
                            for r in res_person:
                                if r.boxes is None:
                                    continue
                                for box in r.boxes:
                                    c = box.xyxy[0].cpu().numpy().astype(int)
                                    person_boxes.append(_clamp_bbox(c[0], c[1], c[2], c[3], w, h))
                            self._update_tracks(person_boxes, now)
                        except Exception:
                            pass

                # Keep cached persons from active tracks for compatibility
                self.cached_persons = [trk['bbox'] for trk in self.tracks.values() if trk.get('lost', 0) == 0]

                # ─── Small-object detection (YOLO + SAHI slicing) ───
                if self.yolo and self.frame_count % self.yolo_interval == 0:
                    try:
                        base_phones, base_books = [], []
                        res_obj = self.yolo.predict(
                            frame,
                            classes=[67, 73],
                            conf=0.20,
                            verbose=False,
                            imgsz=640
                        )
                        for r in res_obj:
                            if r.boxes is None:
                                continue
                            for box in r.boxes:
                                cls = int(box.cls[0])
                                c = box.xyxy[0].cpu().numpy().astype(int)
                                bxyxy = _clamp_bbox(c[0], c[1], c[2], c[3], w, h)
                                if cls == 67:
                                    base_phones.append(bxyxy)
                                elif cls == 73:
                                    base_books.append(bxyxy)

                        sahi_phones, sahi_books = [], []
                        if self.sahi_model and get_sliced_prediction:
                            sahi_pred = get_sliced_prediction(
                                frame,
                                self.sahi_model,
                                slice_height=320,
                                slice_width=320,
                                overlap_height_ratio=0.20,
                                overlap_width_ratio=0.20,
                                perform_standard_pred=False,
                                verbose=0,
                            )
                            for op in sahi_pred.object_prediction_list:
                                cat = int(op.category.id)
                                bb = op.bbox
                                bxyxy = _clamp_bbox(bb.minx, bb.miny, bb.maxx, bb.maxy, w, h)
                                if cat == 67:
                                    sahi_phones.append(bxyxy)
                                elif cat == 73:
                                    sahi_books.append(bxyxy)

                        self.cached_phones = self._merge_boxes(base_phones + sahi_phones, iou_thr=0.55)
                        self.cached_books = self._merge_boxes(base_books + sahi_books, iou_thr=0.55)
                    except Exception as e:
                        print(f"[AI] Object detection error: {e}")

                # Process faces and associate to tracks
                face_found = False
                face_by_track = {}
                if self.face_mesh is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = self.face_mesh.process(rgb)

                    if results.multi_face_landmarks:
                        face_found = True
                        for fl in results.multi_face_landmarks:
                            lm = fl.landmark
                            xs = [l.x * w for l in lm]
                            ys = [l.y * h for l in lm]
                            fb = _clamp_bbox(min(xs) - 15, min(ys) - 20, max(xs) + 15, max(ys) + 10, w, h)

                            pitch, yaw = self._head_pose(lm, w, h)
                            self.yaw_buffer.append(yaw)
                            self.pitch_buffer.append(pitch)

                            pose = "Center"
                            if abs(yaw) > 25:
                                pose = "Right" if yaw > 0 else "Left"
                            elif abs(pitch) > 18:
                                pose = "Down" if pitch > 0 else "Up"

                            gaze = self._gaze_direction(lm, w, h)

                            # Associate this face to the best active person track by IoU
                            best_tid = None
                            best_iou = 0.0
                            for tid, trk in self.tracks.items():
                                iou = _bbox_iou(fb, trk['bbox'])
                                if iou > best_iou:
                                    best_iou = iou
                                    best_tid = tid
                            if best_tid is None and self.tracks:
                                # fallback to nearest by area overlap heuristic
                                best_tid = max(self.tracks.keys(), key=lambda t: _bbox_iou(fb, self.tracks[t]['bbox']))

                            if best_tid is not None:
                                face_by_track[best_tid] = {
                                    'pose': pose,
                                    'gaze': gaze,
                                    'bbox': fb,
                                    'yaw': float(yaw),
                                    'pitch': float(pitch),
                                }

                            # Draw iris landmarks only (cheap and useful)
                            self.mp_drawing.draw_landmarks(
                                image=frame,
                                landmark_list=fl,
                                connections=self.mp_face_mesh.FACEMESH_IRISES,
                                landmark_drawing_spec=None,
                                connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_iris_connections_style()
                            )

                # Per-track scoring and annotation
                students = []
                global_detections = set()
                global_phone = len(self.cached_phones) > 0

                for tid, trk in self.tracks.items():
                    if trk['lost'] > 0:
                        continue

                    tb = trk['bbox']

                    phone_hit = any(_bbox_iou(tb, pb) > 0.02 for pb in self.cached_phones)
                    book_hit = any(_bbox_iou(tb, bb) > 0.02 for bb in self.cached_books)

                    obs = face_by_track.get(tid, None)
                    if obs is None:
                        pose = "Unknown"
                        gaze = "Unknown"
                        yaw = 0.0
                        pitch = 0.0
                    else:
                        pose = obs['pose']
                        gaze = obs['gaze']
                        yaw = obs['yaw']
                        pitch = obs['pitch']

                    score = self._compute_track_score(trk, phone_hit, book_hit, gaze, pose)

                    # Alert categories with anti-spam logging
                    tier = trk['tier']
                    if tier == 'high' and now - trk['last_seen'] < 0.2:
                        global_detections.add(f"High Risk: Student #{tid}")
                    elif tier == 'medium':
                        global_detections.add(f"Suspicious: Student #{tid}")

                    if phone_hit:
                        global_detections.add(f"PHONE DETECTED near Student #{tid}")
                    if pose in ('Left', 'Right'):
                        global_detections.add(f"Head Turn ({pose}) - Student #{tid}")
                    if pose == 'Down':
                        global_detections.add(f"Looking Down - Student #{tid}")
                    if gaze in ('Left', 'Right'):
                        global_detections.add(f"Gaze {gaze} - Student #{tid}")

                    # Draw person box and track label
                    box_color = (0, 255, 0)
                    if score >= 70:
                        box_color = (0, 0, 255)
                    elif score >= 40:
                        box_color = (0, 165, 255)

                    _draw_modern_box(
                        frame,
                        tb[0], tb[1], tb[2], tb[3],
                        f"ID {tid} | {int(score)}% {tier.upper()}",
                        box_color
                    )

                    students.append({
                        'id': tid,
                        'score': round(score, 1),
                        'tier': tier,
                        'pose': pose,
                        'gaze': gaze,
                        'yaw': round(yaw, 1),
                        'pitch': round(pitch, 1),
                        'bbox': [int(tb[0]), int(tb[1]), int(tb[2]), int(tb[3])],
                    })

                    self._enqueue_student_alert(students[-1], now, phone_hit=phone_hit, book_hit=book_hit)

                # Draw object overlays after track boxes
                for (x1, y1, x2, y2) in self.cached_phones:
                    _draw_modern_box(frame, x1, y1, x2, y2, "PROHIBITED: PHONE", (0, 0, 255))
                for (x1, y1, x2, y2) in self.cached_books:
                    _draw_modern_box(frame, x1, y1, x2, y2, "SUSPICIOUS: PAPER/BOOK", (0, 165, 255))

                # Global score from max active student risk + temporal smoothing
                top_score = max([s['score'] for s in students], default=0.0)
                self.score_history.append(top_score)
                if global_phone:
                    self.anomaly_score = 100
                    self.score_history[-1] = 100
                else:
                    self.anomaly_score = int(np.mean(self.score_history)) if self.score_history else int(top_score)

                # Keep deterministic ordering
                students.sort(key=lambda s: s['score'], reverse=True)
                self.students = students

                # Backward-compatible fields for existing dashboard
                self.face_detected = face_found
                self.phone_detected = global_phone
                if students:
                    self.current_pose = students[0]['pose']
                    self.gaze_direction = students[0]['gaze']
                else:
                    self.current_pose = "Center"
                    self.gaze_direction = "Center"
                self.detections = sorted(global_detections)

                # HUD overlay
                col = (0, 255, 0) if self.anomaly_score < 40 else (0, 165, 255) if self.anomaly_score < 70 else (0, 0, 255)
                cv2.rectangle(frame, (0, 0), (w, 36), (0, 0, 0), -1)
                bar_w = int(w * self.anomaly_score / 100)
                if bar_w > 0:
                    overlay_bar = frame.copy()
                    cv2.rectangle(overlay_bar, (0, 0), (bar_w, 36), col, -1)
                    cv2.addWeighted(overlay_bar, 0.35, frame, 0.65, 0, frame)

                cv2.putText(frame, f"RISK: {self.anomaly_score}%", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
                cv2.putText(frame, f"TRACKS: {len(students)}", (180, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (220, 220, 220), 1)
                cv2.putText(frame, f"FPS: {self.fps:.1f}", (w - 120, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (220, 220, 220), 1)

                # Encode and publish
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
                with self.lock:
                    self.output_frame = jpeg.tobytes()

                # Real-time pacing target around 30 FPS
                time.sleep(0.012)

            except Exception as e:
                print(f"[AI] Frame error: {e}")
                time.sleep(0.05)

        if cap:
            cap.release()
        print("[AI] Worker stopped.")

    def get_frame(self):
        """Returns latest JPEG bytes (non-blocking)."""
        self.last_access = time.time()
        with self.lock:
            if self.output_frame:
                return self.output_frame

        blank = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(blank, "INITIALIZING AI ENGINE...", (80, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 0), 2)
        cv2.putText(blank, "Loading MediaPipe FaceMesh...", (140, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
        _, jpeg = cv2.imencode('.jpg', blank)
        return jpeg.tobytes()

    def get_stats(self):
        """Returns detection data for dashboard API — same format as VideoCamera."""
        y = float(np.mean(self.yaw_buffer)) if self.yaw_buffer else 0.0
        p = float(np.mean(self.pitch_buffer)) if self.pitch_buffer else 0.0
        return {
            'risk_score':     self.anomaly_score,
            'face_detected':  self.face_detected,
            'phone_detected': self.phone_detected,
            'head_pose':      self.current_pose,
            'gaze':           self.gaze_direction,
            'yaw':            round(y, 1),
            'pitch':          round(p, 1),
            'detections':     self.detections,
            'persons':        len(self.students),
            'students':       self.students,
            'fps':            round(self.fps, 1),
            'risk_tier':      _risk_tier(self.anomaly_score),
            'camera_source':  self.get_camera_source(),
            'audio_level':    0,
        }

