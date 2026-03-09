# 🎓 THE SILENT INVIGILATOR

## Autonomous Real-Time Exam Malpractice Detection System Using Behavioral Analysis

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Latest-orange.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Nano-red.svg)

---

## 🎯 AIM

To develop an **automated, non-intrusive exam invigilation system** that utilizes advanced computer vision and deep learning algorithms to detect, analyze, and flag suspicious student behaviors in real-time. The primary objective is to eliminate human error and bias in surveillance by implementing a multi-modal AI capable of identifying complex malpractice indicators such as:

- ❌ Unauthorized object usage (mobile phones)
- 👀 Frequent gaze aversion
- 🤔 Abnormal physical movements
- 👥 Multiple person detection
- 🖐️ Suspicious hand gestures

---

## 🔧 TECHNOLOGY STACK

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Programming Language** | Python 3.10+ | Core implementation |
| **Computer Vision** | OpenCV (cv2) | Video processing & display |
| **Pose Estimation** | Google MediaPipe | Face Mesh, Hand & Pose tracking |
| **Object Detection** | YOLOv8 Nano (Ultralytics) | Mobile phone detection |
| **Numerical Processing** | NumPy | Mathematical operations |

---

## ✨ FEATURES

### 🎯 Core Detection Capabilities

✅ **Face Detection & Counting**
- Detects up to 3 faces simultaneously
- Alerts when multiple persons are present
- Real-time face mesh visualization

✅ **3D Head Pose Estimation**
- Precise **Pitch** (up/down), **Yaw** (left/right), and **Roll** (tilt) angles
- **Stabilized readings** using exponential smoothing
- Threshold-based alerts for head turning

✅ **Advanced Eye Gaze Tracking**
- **Iris Ratio Analysis**: Calculates relative position of iris within eye corners
- Detects looking Left/Right/Center with high accuracy
- Robust against head movement

✅ **Mouth & Talking Detection**
- **Mouth Aspect Ratio (MAR)** analysis
- Detects talking, yawning, or mouth opening
- Filters momentary movements

✅ **Hand Gesture Analysis**
- Bilateral hand tracking (up to 2 hands)
- Detection of hands near face region
- Skeletal hand visualization

✅ **Body Posture Monitoring**
- Shoulder alignment analysis
- Unusual posture detection

✅ **Mobile Phone Detection**
- YOLOv8 Nano object detection
- Real-time bounding box visualization
- Confidence scoring (>50% threshold)

✅ **Temporal Behavior Analysis**
- Sustained vs. momentary behavior filtering
- Flag-based tracking for prolonged suspicious activity
- Anomaly score accumulation over time

### 🎨 Modern Dashboard UI

✅ **Professional Sidebar Interface**
- **Risk Level Meter**: Visual color-coded bar (Green/Yellow/Red)
- **Status Indicators**: Live icons for Head, Gaze, Mouth, Phone, Presence
- **Recent Alerts Log**: Scrolling list of last 5 detections
- **FPS & Time**: Real-time performance monitoring

✅ **Comprehensive Reporting**
- JSON report generation with timestamp
- Detailed statistics (avg/max/min anomaly scores)
- Behavioral metrics (head pose, gaze, detections)
- Final verdict with risk assessment

---

## 📥 INPUTS REQUIRED

1. **Video Feed**
   - Continuous real-time video from webcam (default)
   - Or pre-recorded video file (MP4, AVI, etc.)
   - Minimum resolution: 640x480 (1280x720 recommended)

2. **System Resources**
   - Python 3.10+ runtime environment
   - CPU/GPU for inference (GPU recommended for YOLOv8)
   - Webcam/camera device

3. **Pre-trained Models** (Auto-downloaded)
   - MediaPipe Face Mesh weights
   - YOLOv8 Nano model (`yolov8n.pt`)

---

## 📤 EXPECTED OUTCOMES

1. **Real-time Video Processing**
   - Live annotated video feed with overlays
   - Head orientation angles displayed (Yaw, Pitch)
   - Gaze status (OK/AWAY)

2. **Object Detection**
   - Bounding boxes around detected mobile phones
   - Confidence scores displayed

3. **Status Indicators**
   - Current behavior status ("✓ Focused", "Looking LEFT", etc.)
   - Color-coded anomaly score (Green/Yellow/Red)
   - Alert count

4. **Alert System**
   - Real-time alerts for anomaly score > 60
   - Red banner notifications for critical events
   - Sustained behavior flagging

5. **Final Report (JSON)**
   ```json
   {
     "exam_session": { ... },
     "statistics": { ... },
     "behavior_analysis": { ... },
     "alerts": [ ... ],
     "verdict": { ... }
   }
   ```

---

## 🚀 INSTALLATION

### Prerequisites

```bash
Python 3.10 or higher
pip (Python package manager)
Webcam or video source
```

### Step 1: Clone/Download Repository

```bash
cd silent-invigilator
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv .venv
```

**Activate virtual environment:**
- Windows: `.venv\Scripts\activate`
- macOS/Linux: `source .venv/bin/activate`

### Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Dependency Breakdown:**
- `opencv-python`: Video capture and display
- `mediapipe`: Face, hand, and pose detection
- `numpy`: Numerical operations
- `ultralytics`: YOLOv8 object detection

---

## 🎮 USAGE

### Basic Usage (Webcam)

```bash
cd backend
python silent_invigilator.py
```

This will run the standalone desktop version.

### 🌐 WEB DASHBOARD (RECOMMENDED)

For the modern Brutalist UI experience:

```bash
cd backend
python app.py
```

1. Open your browser to `http://127.0.0.1:5000`
2. Grant camera permissions if prompted.
3. Used for real-time monitoring with graphical charts.

This version features:
- Live video stream with HUD overlay
- Real-time risk meter and anomaly graph
- Status indicators for Face, Gaze, Phone, and Audio
- Alert logging system

### Advanced Usage (Video File)

Modify the last line in `silent_invigilator.py`:

```python
invigilator.run('path/to/exam_recording.mp4')
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `Q` | Quit monitoring and generate final report |
| `S` | Save current report (without quitting) |
| `R` | Reset alerts and anomaly scores |

---

## 📊 OUTPUT EXAMPLES

### Console Output

```
╔════════════════════════════════════════════════════════════════════╗
║              🎓 THE SILENT INVIGILATOR v2.0 🎓                     ║
║        Autonomous Real-Time Exam Malpractice Detection            ║
╚════════════════════════════════════════════════════════════════════╝

🔧 Initializing Silent Invigilator System...
  ✓ Loading MediaPipe Face Mesh...
  ✓ Loading MediaPipe Pose Estimation...
  ✓ Loading MediaPipe Hand Detection...
  ✓ Loading YOLOv8 Nano model...
  ✓ YOLOv8 loaded successfully
✅ Initialization Complete!

📹 Monitoring Started...

Controls:
  [Q] - Quit and generate report
  [S] - Save current report
  [R] - Reset alerts
----------------------------------------------------------------------

📋 EXAM SUMMARY
======================================================================
⏱  Duration: 3m 42s
🎞  Total Frames: 6742
⚠  Suspicious Frames: 284 (4.2%)
🚨 Total Alerts: 12

📊 Anomaly Scores:
   Average: 18.45
   Maximum: 87.30
   Minimum: 0.00

🎯 VERDICT: MODERATE RISK
💡 Manual review suggested. Some suspicious behaviors observed.
======================================================================
```

### JSON Report Structure

```json
{
  "exam_session": {
    "start_time": "2025-12-14 10:30:15",
    "duration_seconds": 222.45,
    "duration_formatted": "3m 42s"
  },
  "statistics": {
    "total_frames_analyzed": 6742,
    "suspicious_frames": 284,
    "suspicious_percentage": 4.21,
    "total_alerts": 12,
    "average_anomaly_score": 18.45,
    "max_anomaly_score": 87.30,
    "min_anomaly_score": 0.00
  },
  "behavior_analysis": {
    "avg_head_yaw": 12.34,
    "avg_head_pitch": 8.76,
    "avg_gaze_deviation": 0.043,
    "looking_away_frames": 145,
    "phone_detected_frames": 8,
    "multiple_faces_detected": 2
  },
  "alerts": [
    {
      "timestamp": "2025-12-14 10:31:47.234",
      "frame_number": 2543,
      "score": 75,
      "detections": [
        "Looking RIGHT (32.4°)",
        "🔴 Prolonged right gaze"
      ],
      "flags": { ... }
    }
  ],
  "verdict": {
    "status": "MODERATE RISK",
    "color": "YELLOW",
    "avg_anomaly_score": 18.45,
    "total_alerts": 12,
    "suspicious_frame_ratio": 0.042,
    "recommendation": "Manual review suggested..."
  }
}
```

---

## 🎨 GUI OVERLAY EXPLAINED

### Status Indicators

- **Top Left:**
  - Yaw angle (left/right head rotation)
  - Pitch angle (up/down head rotation)
  - Gaze status (OK / AWAY)

- **Top Right:**
  - Elapsed time
  - Current frame number
  - FPS (frames per second)

- **Bottom Status Bar:**
  - Anomaly Score (color-coded)
  - Current Status ("✓ Focused", "Looking LEFT", etc.)
  - Total Alerts

- **Alert Banner (when triggered):**
  - Red background overlay
  - "🚨 MALPRACTICE ALERT!" text

---

## ⚙️ CONFIGURATION

### Threshold Tuning

Edit thresholds in `__init__` method:

```python
self.thresholds = {
    'head_yaw_max': 30,          # degrees (left/right)
    'head_pitch_max': 25,        # degrees (up/down)
    'gaze_deviation_max': 0.06,  # normalized units
    'sustained_look_away_frames': 45,  # ~1.5 sec
    'phone_confidence': 0.5,     # YOLO confidence
    'multiple_faces_frames': 15, # ~0.5 sec
}
```

### Anomaly Score Weights

Modify scoring in `detect_suspicious_behavior()`:

- Multiple persons: **+40 points**
- Head turned beyond threshold: **+25 points**
- Eyes looking away: **+15 points**
- Phone detected: **+50 points**
- Sustained inattention: **+30 points**

**Alert Trigger:** Score > 60

---

## 🔬 TECHNICAL DETAILS

### Head Pose Estimation Algorithm

Uses **solvePnP** (Perspective-n-Point) algorithm:
1. Extract 3D facial landmarks (x, y, z) from MediaPipe
2. Project to 2D image coordinates
3. Estimate camera matrix (focal length, principal point)
4. Solve for rotation and translation vectors
5. Decompose rotation matrix into Euler angles (pitch, yaw, roll)

### Eye Gaze Tracking

1. Locate iris centers (landmarks 468, 473)
2. Calculate eye region centers
3. Measure Euclidean distance between iris and eye center
4. Average left and right eye deviations
5. Normalize to 0-1 range

### Temporal Behavior Filtering

Uses **deque** data structures with 60-frame sliding windows:
- Filters momentary movements
- Detects sustained patterns (>45 frames = 1.5 seconds)
- Implements flag-based streak counting

---

## 📁 PROJECT STRUCTURE

```text
silent-invigilator/
│
├── backend/                  # Python Flask backend & ML models
│   ├── app.py                # Web Dashboard application
│   ├── silent_invigilator.py # Standalone desktop application
│   ├── camera.py             # CV and ML logic
│   ├── requirements.txt      # Python dependencies
│   ├── yolov8n.pt            # YOLOv8 weights (auto-downloaded)
│   ├── static/               # Web assets (CSS, JS, Images)
│   ├── templates/            # HTML templates
│   └── exam_report_*.json    # Generated reports
│
├── mobile_app/               # Flutter mobile application
│
├── docs/                     # Documentation files
│   ├── EXECUTION_PLAN.md     # Project execution plan
│   └── project.txt           # React UI specification
│
├── run_standalone.bat        # Windows launcher for desktop mode
├── run_web.bat               # Windows launcher for web dashboard
├── README.md                 # This file
└── QUICKSTART.md             # Quick start guide
```

---

## 🐛 TROUBLESHOOTING

### Issue: "Camera access denied"
**Solution:** Grant camera permissions to Python/Terminal

### Issue: YOLOv8 not loading
**Solution:** Ensure internet connection for initial download of `yolov8n.pt`

### Issue: Low FPS / Lag
**Solutions:**
- Reduce camera resolution
- Disable YOLOv8 (set `self.use_yolo = False`)
- Use lighter face mesh connections (FACEMESH_CONTOURS instead of TESSELATION)

### Issue: Too many false positives
**Solution:** Increase threshold values in configuration

### Issue: Missing detections
**Solution:** Decrease MediaPipe confidence thresholds (currently 0.6)

---

## 🚀 PERFORMANCE OPTIMIZATION

### Speed Improvements

1. **Use GPU acceleration** (CUDA for YOLO)
2. **Lower camera resolution** (640x480 instead of 1280x720)
3. **Reduce MediaPipe face count** (max_num_faces=1)
4. **Skip frames** (process every 2nd or 3rd frame)

### Accuracy Improvements

1. **Increase detection confidence** (0.7 instead of 0.6)
2. **Calibrate thresholds** for specific exam environments
3. **Add more YOLO classes** (books, papers, etc.)
4. **Implement audio analysis** for voice detection

---

## 📜 LICENSE

This project is for educational and research purposes.

---

## 👨‍💻 DEVELOPER NOTES

### Future Enhancements

- [ ] Multi-student monitoring (grid view)
- [ ] Audio analysis for voice detection
- [ ] Cloud-based report storage
- [ ] Real-time dashboard (web interface)
- [ ] Machine learning anomaly detection (LSTM)
- [ ] Exam session scheduling
- [ ] Automated email alerts

---

## 🙏 ACKNOWLEDGMENTS

- **MediaPipe** by Google Research
- **Ultralytics YOLOv8** for object detection
- **OpenCV** community

---

## 📞 SUPPORT

For issues or questions, please check:
1. Troubleshooting section above
2. MediaPipe documentation: https://google.github.io/mediapipe/
3. YOLOv8 docs: https://docs.ultralytics.com/

---

**Built with ❤️ for academic integrity**
