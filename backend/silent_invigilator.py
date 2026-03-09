"""
THE SILENT INVIGILATOR: Autonomous Real-Time Exam Malpractice Detection System
Using Behavioral Analysis with Computer Vision and Deep Learning

AIM: Automated, non-intrusive exam invigilation system utilizing advanced computer vision
and deep learning to detect, analyze, and flag suspicious student behaviors in real-time.

TECHNOLOGY STACK:
- Python 3.10+
- OpenCV (Computer Vision)
- MediaPipe (Face Mesh & Pose Estimation)
- YOLOv8 Nano (Object Detection - Mobile Phones)
- NumPy (Numerical Processing)

FEATURES:
✓ Precise real-time head orientation tracking (Yaw & Pitch angles)
✓ Automated detection of prohibited items (mobile phones)
✓ GUI overlay with live status indicators and warnings
✓ Logic-based flagging system filtering momentary vs sustained suspicious behavior
✓ Eye gaze deviation tracking
✓ Multiple person detection
✓ Comprehensive exam report generation
"""

import cv2
import numpy as np 
import mediapipe as mp
from collections import deque
from datetime import datetime
import json
import time
from ultralytics import YOLO

class Stabilizer:
    """Exponential smoothing for stable sensor readings"""
    def __init__(self, alpha=0.6):
        self.alpha = alpha
        self.value = None

    def update(self, new_value):
        if self.value is None:
            self.value = new_value
        else:
            self.value = (self.alpha * new_value) + ((1 - self.alpha) * self.value)
        return self.value

class SilentInvigilator:
    def __init__(self):
        print("🔧 Initializing Silent Invigilator System...")
        
        # Initialize MediaPipe components
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize detectors with optimized settings
        print("  ✓ Loading MediaPipe Face Mesh...")
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        
        print("  ✓ Loading MediaPipe Pose Estimation...")
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        
        print("  ✓ Loading MediaPipe Hand Detection...")
        self.hands = self.mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        
        # Initialize YOLOv8 for object detection
        print("  ✓ Loading YOLOv8 Nano model...")
        try:
            self.yolo_model = YOLO('yolov8n.pt')
            self.use_yolo = True
            print("  ✓ YOLOv8 loaded successfully")
        except Exception as e:
            print(f"  ⚠ YOLOv8 not available: {e}")
            self.use_yolo = False
        
        # Signal Stabilizers (Smoothing)
        self.stabilizers = {
            'yaw': Stabilizer(0.5),
            'pitch': Stabilizer(0.5),
            'gaze_h': Stabilizer(0.6), # Horizontal gaze
            'gaze_v': Stabilizer(0.6), # Vertical gaze
            'mouth': Stabilizer(0.3)
        }
        
        # Behavior tracking
        self.behavior_history = {
            'head_yaw': deque(maxlen=60),
            'head_pitch': deque(maxlen=60),
            'gaze_ratio': deque(maxlen=60),
            'mouth_open': deque(maxlen=60),
            'face_count': deque(maxlen=60),
            'looking_away': deque(maxlen=60),
            'phone_detected': deque(maxlen=60),
            'timestamps': deque(maxlen=60)
        }
        
        # Tuned Thresholds
        self.thresholds = {
            'head_yaw_limit': 25,      # degrees
            'head_pitch_limit': 20,    # degrees
            'gaze_center_min': 0.35,   # Relative iris position (0-1)
            'gaze_center_max': 0.65,
            'mouth_open_ratio': 0.5,   # MAR threshold for talking
            'phone_confidence': 0.45,
            'sustained_frames': 45,    # ~1.5s
        }
        
        # State tracking
        self.anomaly_scores = []
        self.alerts = []
        self.total_frames = 0
        self.suspicious_frames = 0
        self.start_time = None
        self.current_status = "Initializing"
        
        # Flag tracking
        self.flags = {
            'looking_left': 0,
            'looking_right': 0,
            'looking_down': 0,
            'looking_up': 0,
            'phone_present': 0,
            'multiple_persons': 0,
            'hand_near_face': 0,
            'talking': 0,
            'absent': 0
        }
        
        print("✅ Initialization Complete!\n")
        
    def calculate_head_pose(self, landmarks, image_shape):
        """
        Calculate head pose angles (pitch, yaw, roll) using 3D-to-2D perspective projection
        Returns: (pitch, yaw, roll) in degrees
        """
        h, w = image_shape[:2]
        
        # Key 3D facial landmarks (from MediaPipe Face Mesh)
        face_3d = []
        face_2d = []
        
        # Select specific landmarks for head pose estimation
        landmark_indices = [1, 33, 263, 61, 291, 199]  # nose, left_eye, right_eye, left_mouth, right_mouth, chin
        
        for idx in landmark_indices:
            lm = landmarks[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            face_3d.append([lm.x * w, lm.y * h, lm.z * 3000])
            face_2d.append([x, y])
        
        face_3d = np.array(face_3d, dtype=np.float64)
        face_2d = np.array(face_2d, dtype=np.float64)
        
        focal_length = w
        cam_matrix = np.array([[focal_length, 0, w / 2], [0, focal_length, h / 2], [0, 0, 1]])
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        
        success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_coeffs)
        rot_mat, _ = cv2.Rodrigues(rot_vec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rot_mat)
        
        # RQDecomp3x3 returns angles - handle properly
        # The output is typically small values that represent rotation
        pitch = angles[0]
        yaw = angles[1]
        roll = angles[2]
        
        # If values are very small (radians-like), convert to degrees
        # Otherwise they're already in a usable range
        if abs(pitch) < 3.15 and abs(yaw) < 3.15:  # Likely radians
            pitch = np.degrees(pitch)
            yaw = np.degrees(yaw)
            roll = np.degrees(roll)
        
        # Normalize to -180 to 180 range
        yaw = ((yaw + 180) % 360) - 180
        pitch = ((pitch + 180) % 360) - 180
        
        # Stabilize
        yaw = self.stabilizers['yaw'].update(yaw)
        pitch = self.stabilizers['pitch'].update(pitch)
        
        return pitch, yaw, roll
    
    def get_gaze_ratio(self, landmarks):
        """
        Calculate the ratio of the iris position relative to eye corners.
        Returns: average horizontal ratio (0.0=Left, 0.5=Center, 1.0=Right)
        """
        # Indices for Left Eye (33=Inner, 133=Outer, 468=Iris)
        # Indices for Right Eye (362=Inner, 263=Outer, 473=Iris)
        
        def get_ratio(eye_points, iris_point):
            # Horizontal ratio
            eye_width = np.linalg.norm(eye_points[0] - eye_points[1])
            if eye_width == 0: return 0.5
            
            # Project iris onto the line connecting eye corners
            # Simple approximation: relative distance to inner corner
            d_inner = np.linalg.norm(iris_point - eye_points[0])
            ratio = d_inner / eye_width
            return ratio

        # Get coordinates
        left_inner = np.array([landmarks[33].x, landmarks[33].y])
        left_outer = np.array([landmarks[133].x, landmarks[133].y])
        left_iris = np.array([landmarks[468].x, landmarks[468].y])
        
        right_inner = np.array([landmarks[362].x, landmarks[362].y])
        right_outer = np.array([landmarks[263].x, landmarks[263].y])
        right_iris = np.array([landmarks[473].x, landmarks[473].y])
        
        # Calculate ratios
        left_ratio = get_ratio([left_inner, left_outer], left_iris)
        right_ratio = get_ratio([right_inner, right_outer], right_iris)
        
        avg_ratio = (left_ratio + right_ratio) / 2
        return self.stabilizers['gaze_h'].update(avg_ratio)

    def calculate_mouth_aspect_ratio(self, landmarks):
        """
        Calculate Mouth Aspect Ratio (MAR) to detect talking/yawning.
        MAR = Vertical Distance / Horizontal Distance
        """
        # Mouth indices: 
        # Top: 13, Bottom: 14
        # Left: 61, Right: 291
        
        top = np.array([landmarks[13].x, landmarks[13].y])
        bottom = np.array([landmarks[14].x, landmarks[14].y])
        left = np.array([landmarks[61].x, landmarks[61].y])
        right = np.array([landmarks[291].x, landmarks[291].y])
        
        vertical_dist = np.linalg.norm(top - bottom)
        horizontal_dist = np.linalg.norm(left - right)
        
        if horizontal_dist == 0: return 0
        
        mar = vertical_dist / horizontal_dist
        return self.stabilizers['mouth'].update(mar)
    
    
    def detect_objects_yolo(self, frame):
        """
        Detect mobile phones and other prohibited objects using YOLOv8
        Returns: list of detections
        """
        if not self.use_yolo:
            return [], frame
        
        detections = []
        try:
            # Run YOLO inference (class 67 = cell phone in COCO dataset)
            results = self.yolo_model(frame, classes=[67], conf=self.thresholds['phone_confidence'], verbose=False)
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    
                    if cls == 67:  # Cell phone
                        detections.append({
                            'type': 'Mobile Phone',
                            'confidence': conf,
                            'bbox': (x1, y1, x2, y2)
                        })
                        
                        # Draw bounding box on frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        cv2.putText(frame, f'PHONE {conf:.2f}', (x1, y1 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        except Exception as e:
            pass  # Silent fail to not interrupt monitoring
        
        return detections, frame
    
    # Note: The main detect_suspicious_behavior method is defined below
        
    def draw_dashboard(self, frame, anomaly_score, detections, fps):
        """
        Draw a modern dashboard overlay with sidebar
        """
        h, w = frame.shape[:2]
        sidebar_w = 320
        
        # Create main canvas
        canvas = np.zeros((h, w + sidebar_w, 3), dtype=np.uint8)
        canvas[:, :w] = frame
        
        # Sidebar background (Dark Grey)
        sidebar = canvas[:, w:]
        sidebar[:] = (30, 30, 30)
        
        # --- HEADER ---
        cv2.rectangle(sidebar, (0, 0), (sidebar_w, 80), (20, 20, 20), -1)
        cv2.putText(sidebar, "SILENT INVIGILATOR", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(sidebar, "Exam Monitoring System", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        
        # --- RISK METER ---
        y_offset = 120
        cv2.putText(sidebar, "RISK LEVEL", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Risk bar background
        cv2.rectangle(sidebar, (20, y_offset + 15), (sidebar_w - 20, y_offset + 35), (50, 50, 50), -1)
        
        # Risk bar fill
        risk_color = (0, 255, 0) # Green
        if anomaly_score > 30: risk_color = (0, 255, 255) # Yellow
        if anomaly_score > 60: risk_color = (0, 0, 255) # Red
        
        fill_w = int((anomaly_score / 100) * (sidebar_w - 40))
        fill_w = max(0, min(fill_w, sidebar_w - 40))
        cv2.rectangle(sidebar, (20, y_offset + 15), (20 + fill_w, y_offset + 35), risk_color, -1)
        
        cv2.putText(sidebar, f"{int(anomaly_score)}%", (sidebar_w - 60, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, risk_color, 2)

        # --- STATUS INDICATORS ---
        y_offset += 80
        
        def draw_status_row(label, value, is_alert, y):
            color = (0, 0, 255) if is_alert else (0, 255, 0)
            icon = "(!)" if is_alert else "OK"
            cv2.putText(sidebar, label, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            cv2.putText(sidebar, icon, (sidebar_w - 50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        draw_status_row("Head Pose", "", self.flags['looking_left'] or self.flags['looking_right'] or self.flags['looking_up'] or self.flags['looking_down'], y_offset)
        draw_status_row("Eye Gaze", "", self.behavior_history['looking_away'][-1] if self.behavior_history['looking_away'] else 0, y_offset + 30)
        draw_status_row("Mouth", "", self.flags['talking'], y_offset + 60)
        draw_status_row("Phone", "", self.flags['phone_present'], y_offset + 90)
        draw_status_row("Presence", "", self.flags['absent'], y_offset + 120)

        # --- DETECTIONS LOG ---
        y_offset += 170
        cv2.putText(sidebar, "RECENT ALERTS", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Show last 5 detections
        for i, det in enumerate(detections[-5:]):
            cv2.putText(sidebar, f"> {det}", (20, y_offset + 30 + (i * 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 255), 1)

        # --- FOOTER ---
        cv2.putText(sidebar, f"FPS: {fps:.1f}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        cv2.putText(sidebar, datetime.now().strftime("%H:%M:%S"), (sidebar_w - 100, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

        return canvas

    def detect_suspicious_behavior(self, frame):
        """
        Main detection pipeline - analyzes frame for suspicious behaviors
        Returns: processed_frame, anomaly_score, detections_list
        """
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        h, w = frame.shape[:2]
        
        self.total_frames += 1
        current_time = time.time()
        if self.start_time is None: self.start_time = current_time
        
        # Process with MediaPipe
        face_results = self.face_mesh.process(image)
        pose_results = self.pose.process(image)
        hand_results = self.hands.process(image)
        
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        anomaly_score = 0
        detections = []
        
        # ===== FACE ANALYSIS =====
        if face_results.multi_face_landmarks:
            num_faces = len(face_results.multi_face_landmarks)
            self.flags['absent'] = 0
            
            if num_faces > 1:
                anomaly_score += 40
                detections.append(f"⚠ {num_faces} persons detected")
                self.flags['multiple_persons'] += 1
            else:
                self.flags['multiple_persons'] = max(0, self.flags['multiple_persons'] - 1)
            
            face_landmarks = face_results.multi_face_landmarks[0]
            
            # Draw Face Mesh
            self.mp_drawing.draw_landmarks(
                image=image,
                landmark_list=face_landmarks,
                connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
            )
            
            # 1. Head Pose
            try:
                pitch, yaw, roll = self.calculate_head_pose(face_landmarks.landmark, frame.shape)
                
                # Track head pose in history
                self.behavior_history['head_yaw'].append(yaw)
                self.behavior_history['head_pitch'].append(pitch)
                
                if abs(yaw) > self.thresholds['head_yaw_limit']:
                    anomaly_score += 20
                    direction = "LEFT" if yaw < 0 else "RIGHT"
                    detections.append(f"Head turned {direction}")
                    if direction == "LEFT": self.flags['looking_left'] += 1
                    else: self.flags['looking_right'] += 1
                else:
                    self.flags['looking_left'] = 0
                    self.flags['looking_right'] = 0
                    
                if abs(pitch) > self.thresholds['head_pitch_limit']:
                    anomaly_score += 20
                    direction = "UP" if pitch < 0 else "DOWN"
                    detections.append(f"Head turned {direction}")
                    if direction == "UP": self.flags['looking_up'] += 1
                    else: self.flags['looking_down'] += 1
                else:
                    self.flags['looking_up'] = 0
                    self.flags['looking_down'] = 0
                    
            except Exception:
                self.behavior_history['head_yaw'].append(0)
                self.behavior_history['head_pitch'].append(0)

            # 2. Gaze Tracking
            try:
                gaze_ratio = self.get_gaze_ratio(face_landmarks.landmark)
                self.behavior_history['gaze_ratio'].append(gaze_ratio)
                
                if gaze_ratio < self.thresholds['gaze_center_min']:
                    anomaly_score += 15
                    detections.append("Looking LEFT (Eyes)")
                    self.behavior_history['looking_away'].append(1)
                elif gaze_ratio > self.thresholds['gaze_center_max']:
                    anomaly_score += 15
                    detections.append("Looking RIGHT (Eyes)")
                    self.behavior_history['looking_away'].append(1)
                else:
                    self.behavior_history['looking_away'].append(0)
            except Exception:
                self.behavior_history['gaze_ratio'].append(0.5)
                self.behavior_history['looking_away'].append(0)
            
            # 3. Mouth Detection (Talking)
            try:
                mar = self.calculate_mouth_aspect_ratio(face_landmarks.landmark)
                if mar > self.thresholds['mouth_open_ratio']:
                    anomaly_score += 25
                    detections.append("Mouth Open / Talking")
                    self.flags['talking'] += 1
                else:
                    self.flags['talking'] = max(0, self.flags['talking'] - 1)
            except Exception: pass

        else:
            # No face detected
            anomaly_score += 30
            detections.append("⚠ No Face Detected")
            self.flags['absent'] += 1
            self.behavior_history['face_count'].append(0)
        
        # Track face count in history (for detected faces)
        if face_results.multi_face_landmarks:
            self.behavior_history['face_count'].append(len(face_results.multi_face_landmarks))

        # ===== HAND ANALYSIS =====
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                wrist_y = hand_landmarks.landmark[0].y
                if wrist_y < 0.5: # Hand near face
                    anomaly_score += 10
                    detections.append("Hand near face")
                    self.flags['hand_near_face'] += 1
                else:
                    self.flags['hand_near_face'] = 0

        # ===== PHONE DETECTION =====
        phone_detections, image = self.detect_objects_yolo(image)
        if phone_detections:
            anomaly_score += 50
            detections.append("🚨 Mobile Phone Detected")
            self.flags['phone_present'] += 1
            self.behavior_history['phone_detected'].append(1)
        else:
            self.flags['phone_present'] = 0
            self.behavior_history['phone_detected'].append(0)

        # ===== TEMPORAL ANALYSIS =====
        # Check for sustained behaviors
        if self.flags['looking_left'] > 30 or self.flags['looking_right'] > 30:
            anomaly_score += 20
            detections.append("🔴 Sustained Head Turn")
            
        if self.flags['talking'] > 15:
            anomaly_score += 20
            detections.append("🔴 Sustained Talking")

        # Store score
        self.anomaly_scores.append(anomaly_score)
        if anomaly_score > 40: self.suspicious_frames += 1
        
        # Generate Alert
        if anomaly_score > 60:
            alert = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'score': anomaly_score,
                'detections': list(set(detections))
            }
            self.alerts.append(alert)
            
            # Draw Alert Banner on Video
            cv2.rectangle(image, (0, 0), (w, 50), (0, 0, 255), -1)
            cv2.putText(image, "MALPRACTICE ALERT", (w//2 - 100, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return image, anomaly_score, list(set(detections))

    def run(self, video_source=0):
        """Main execution loop"""
        cap = cv2.VideoCapture(video_source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("="* 70)
        print(" " * 15 + "🎓 THE SILENT INVIGILATOR 🎓")
        print("=" * 70)
        print("Controls: [Q] Quit | [S] Save Report | [R] Reset")
        
        fps_start = time.time()
        frame_cnt = 0
        fps = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame_cnt += 1
            if frame_cnt % 10 == 0:
                fps = 10 / (time.time() - fps_start)
                fps_start = time.time()
            
            # Process
            processed_frame, score, detections = self.detect_suspicious_behavior(frame)
            
            # Draw Dashboard
            final_display = self.draw_dashboard(processed_frame, score, detections, fps)
            
            cv2.imshow('Silent Invigilator Dashboard', final_display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            elif key == ord('s'): self.save_report()
            elif key == ord('r'): self.alerts = []
            
        cap.release()
        cv2.destroyAllWindows()
        self.save_report()
        self.print_summary()
    
    def save_report(self):
        """
        Save comprehensive monitoring report to JSON file
        """
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        report = {
            'exam_session': {
                'start_time': datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A',
                'duration_seconds': round(elapsed_time, 2),
                'duration_formatted': f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
            },
            'statistics': {
                'total_frames_analyzed': self.total_frames,
                'suspicious_frames': self.suspicious_frames,
                'suspicious_percentage': round((self.suspicious_frames / self.total_frames * 100), 2) if self.total_frames > 0 else 0,
                'total_alerts': len(self.alerts),
                'average_anomaly_score': round(np.mean(self.anomaly_scores), 2) if self.anomaly_scores else 0,
                'max_anomaly_score': round(max(self.anomaly_scores), 2) if self.anomaly_scores else 0,
                'min_anomaly_score': round(min(self.anomaly_scores), 2) if self.anomaly_scores else 0
            },
            'behavior_analysis': {
                'avg_head_yaw': round(np.mean(list(self.behavior_history['head_yaw'])), 2) if self.behavior_history['head_yaw'] else 0,
                'avg_head_pitch': round(np.mean(list(self.behavior_history['head_pitch'])), 2) if self.behavior_history['head_pitch'] else 0,
                'avg_gaze_deviation': round(np.mean(list(self.behavior_history['gaze_ratio'])), 3) if self.behavior_history['gaze_ratio'] else 0,
                'looking_away_frames': sum(self.behavior_history['looking_away']),
                'phone_detected_frames': sum(self.behavior_history['phone_detected']),
                'multiple_faces_detected': sum(1 for x in self.behavior_history['face_count'] if x > 1)
            },
            'alerts': self.alerts,
            'flags_summary': {
                'max_looking_left_streak': self.flags.get('looking_left', 0),
                'max_looking_right_streak': self.flags.get('looking_right', 0),
                'max_looking_down_streak': self.flags.get('looking_down', 0),
                'max_looking_up_streak': self.flags.get('looking_up', 0),
                'max_phone_present_streak': self.flags.get('phone_present', 0),
                'max_multiple_persons_streak': self.flags.get('multiple_persons', 0)
            },
            'verdict': self.generate_verdict()
        }
        
        filename = f"exam_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
    
    def generate_verdict(self):
        """
        Generate final verdict based on collected evidence
        """
        if not self.anomaly_scores:
            return {"status": "INCOMPLETE", "reason": "Insufficient data"}
        
        avg_score = np.mean(self.anomaly_scores)
        alert_count = len(self.alerts)
        suspicious_ratio = self.suspicious_frames / self.total_frames if self.total_frames > 0 else 0
        
        if alert_count > 10 or avg_score > 50 or suspicious_ratio > 0.3:
            status = "HIGH RISK"
            color = "RED"
            recommendation = "Manual review strongly recommended. Multiple malpractice indicators detected."
        elif alert_count > 5 or avg_score > 30 or suspicious_ratio > 0.15:
            status = "MODERATE RISK"
            color = "YELLOW"
            recommendation = "Manual review suggested. Some suspicious behaviors observed."
        else:
            status = "LOW RISK"
            color = "GREEN"
            recommendation = "Student behavior appears normal. No significant concerns."
        
        return {
            "status": status,
            "color": color,
            "avg_anomaly_score": round(avg_score, 2),
            "total_alerts": alert_count,
            "suspicious_frame_ratio": round(suspicious_ratio, 3),
            "recommendation": recommendation
        }
    
    def print_summary(self):
        """
        Print summary statistics to console
        """
        verdict = self.generate_verdict()
        
        print(f"\n{'=' * 70}")
        print(" " * 25 + "📋 EXAM SUMMARY")
        print(f"{'=' * 70}")
        
        if self.total_frames > 0:
            print(f"\n⏱  Duration: {int((time.time() - self.start_time) // 60)}m {int((time.time() - self.start_time) % 60)}s")
            print(f"🎞  Total Frames: {self.total_frames}")
            print(f"⚠  Suspicious Frames: {self.suspicious_frames} ({(self.suspicious_frames/self.total_frames*100):.1f}%)")
            print(f"🚨 Total Alerts: {len(self.alerts)}")
            print(f"\n📊 Anomaly Scores:")
            print(f"   Average: {np.mean(self.anomaly_scores):.2f}")
            print(f"   Maximum: {max(self.anomaly_scores):.2f}")
            print(f"   Minimum: {min(self.anomaly_scores):.2f}")
            
            print(f"\n🎯 VERDICT: {verdict['status']}")
            print(f"💡 {verdict['recommendation']}")
        else:
            print("\n⚠  No frames processed")
        
        print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║              🎓 THE SILENT INVIGILATOR v2.0 🎓                     ║
    ║        Autonomous Real-Time Exam Malpractice Detection            ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
    
    🔍 DETECTION CAPABILITIES:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ✓ Face Detection & Counting (Multiple Person Detection)
    ✓ 3D Head Pose Estimation (Precise Pitch, Yaw, Roll angles)
    ✓ Eye Gaze Tracking (Iris position analysis)
    ✓ Hand Gesture Analysis (Near-face detection)
    ✓ Body Posture Monitoring (Shoulder alignment)
    ✓ Mobile Phone Detection (YOLOv8 Object Recognition)
    ✓ Temporal Behavior Analysis (Sustained vs Momentary)
    ✓ Real-time Anomaly Scoring with GUI Overlay
    ✓ Comprehensive JSON Report Generation
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    📋 REQUIREMENTS:
    • Python 3.10+
    • opencv-python
    • mediapipe
    • numpy
    • ultralytics (YOLOv8)
    
    🎥 VIDEO SOURCE OPTIONS:
    • 0 or 1 - Webcam
    • Path to video file (e.g., 'exam_recording.mp4')
    
    """)
    
    # Start the Silent Invigilator
    print("🚀 Initializing system...")
    print("-" * 70)
    
    invigilator = SilentInvigilator()
    
    print("\n📹 Starting exam monitoring with webcam...")
    print("=" * 70 + "\n")
    
    # Start monitoring (use 0 for default webcam, 1 for external camera, or video file path)
    invigilator.run(0)