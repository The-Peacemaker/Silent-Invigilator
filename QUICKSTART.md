# Quick Start Guide
## The Silent Invigilator - Exam Monitoring System

This guide outlines the quick setup and execution procedures for the Silent Invigilator exam monitoring system.

---

### Installation and Execution

#### Step 1: Install Dependencies
Navigate to the backend directory and install the required Python packages.

```bash
cd backend
pip install -r requirements.txt
```

Alternatively, manually install the required packages:
```bash
pip install opencv-python mediapipe numpy ultralytics flask flask-cors
```

#### Step 2: Start the System
Run the main invigilator script to start the monitoring session.

```bash
cd backend
python silent_invigilator.py
```

#### Step 3: Monitor Session
* The webcam interface will open automatically.
* The system will display real-time detection overlays on the video stream.
* Press the **Q** key to terminate the session and generate the final report.

---

### System Controls

The application supports the following keyboard shortcuts:

| Key | Action |
|-----|--------|
| **Q** | Terminate monitoring and save the final report |
| **S** | Save the current report and continue monitoring |
| **R** | Reset active alerts |

---

### Output and Visual Indicators

#### Real-Time On-Screen Indicators
* **Face Mesh Overlay:** Visual tracker showing facial landmarks.
* **Head Pose Estimation:** Displays numerical Pitch and Yaw angles.
* **Gaze Direction:** Indicates whether the student is looking Center, Left, Right, Up, or Down.
* **Object Bounding Boxes:** Highlights detected prohibited items, such as mobile phones.
* **Anomaly Score:** Real-time risk indicator shown at the bottom of the window.
* **Alert Banners:** Red warning banner displayed when the anomaly score exceeds safety thresholds.

#### Session Outputs
* **JSON Report:** Saved as `exam_report_YYYYMMDD_HHMMSS.json` upon exit.
* **Console Summary:** Displays the final assessment and calculated risk verdict.

---

### Troubleshooting and Performance Tuning

#### Customizing Camera Index
If your camera fails to initialize, adjust the camera device index in `silent_invigilator.py`:

```python
# Locate the run call at the bottom of the script:
invigilator.run(1)  # Change 0 to 1, 2, or the appropriate index for external webcams.
```

#### Performance Optimization
* **Lower Stream Resolution:** Modify the OpenCV capture resolution parameters in the script.
* **Disable YOLO Detection:** Set `self.use_yolo = False` to run only the facial landmark tracking.

#### First-Time Run
* On the first execution, the system will download the YOLOv8 Nano weight file (~6 MB). An active internet connection is required for this step.

---

### Verification and Test Scenarios

#### Normal Behavior
* Looking straight at the camera will display a "Focused" status.
* The anomaly score will hover between 0 and 20.

#### Anomaly Triggers (Testing)
* **Gaze Aversion:** Turn your head or look away from the screen to trigger gaze indicators.
* **Physical Movement:** Place your hand near your face to trigger hand proximity flags.
* **Prohibited Objects:** Hold a mobile phone in front of the camera to trigger object detection.
* **Multiple Subjects:** Introduce a second person into the frame to trigger multiple person detection flags.

---

### Understanding the Generated Report

#### Risk Verdicts
* **Low Risk:** Normal behavior pattern. The average anomaly score remains below 30.
* **Moderate Risk:** Moderate anomalies detected. The average anomaly score is between 30 and 50.
* **High Risk:** Significant suspicious behavior detected. The average anomaly score exceeds 50.

#### Core Metrics
* `total_alerts`: The count of occurrences where the anomaly score exceeded 60.
* `suspicious_percentage`: The percentage of frames flagged with anomalous behavior.
* `avg_anomaly_score`: The composite score across the entire exam duration.

---

### Full Documentation
For advanced configurations, technical specifications, and custom threshold adjustments, please refer to the main [README.md](file:///c:/Users/bened/Documents/MINI-PROJECT/silent-invigilator/README.md).
