# 🚀 QUICK START GUIDE
## The Silent Invigilator - Exam Monitoring System

### ⚡ Fast Setup (3 Steps)

#### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

Or manually:
```bash
pip install opencv-python mediapipe numpy ultralytics flask flask-cors
```

#### Step 2: Run the Program
```bash
cd backend
python silent_invigilator.py
```

#### Step 3: Monitor Exam
- The webcam GUI will open automatically
- Watch the live detection overlays
- Press **Q** to quit and generate report

---

### 🎮 Controls

| Key | Function |
|-----|----------|
| **Q** | Quit and save final report |
| **S** | Save report (continue monitoring) |
| **R** | Reset alerts |

---

### 📊 What You'll See

**On Screen:**
- ✅ Green face mesh overlay
- 📐 Head pose angles (Yaw, Pitch)
- 👁️ Gaze status indicator
- 📱 Phone detection boxes (if detected)
- 🎯 Anomaly score (bottom bar)
- ⚠️ Alert banner (when suspicious)

**After Exit:**
- 📄 JSON report file: `exam_report_YYYYMMDD_HHMMSS.json`
- 📊 Console summary with verdict

---

### 🔧 Common Issues

**Camera not working?**
```bash
# Try different camera index
# In silent_invigilator.py, change last line:
invigilator.run(1)  # Try 1, 2, etc.
```

**Too slow?**
- Lower camera resolution (edit `cap.set()` calls)
- Or disable YOLO: `self.use_yolo = False`

**YOLOv8 downloading?**
- First run downloads ~6MB model
- Requires internet connection
- Saved to local directory

---

### 📝 Test Scenarios

**Normal Behavior:**
- Look at screen → Status: "✓ Focused"
- Low anomaly score (0-20)
- No alerts

**Suspicious Behavior (for testing):**
- Look left/right sharply → "Looking LEFT/RIGHT"
- Look down → "Looking DOWN"
- Move hand near face → "Hand near face"
- Hold phone to camera → "🚨 Mobile Phone detected"
- Have someone else in frame → "⚠ Multiple persons"

---

### 📈 Understanding the Report

**Verdict Levels:**
- **LOW RISK** (Green): Normal behavior, avg score < 30
- **MODERATE RISK** (Yellow): Some concerns, avg score 30-50
- **HIGH RISK** (Red): Significant issues, avg score > 50

**Key Metrics:**
- `total_alerts`: Number of high-score events (>60)
- `suspicious_percentage`: % of frames with anomaly
- `avg_anomaly_score`: Overall behavior rating

---

### 🎯 Next Steps

1. ✅ Run with webcam
2. ✅ Test different behaviors
3. ✅ Review generated JSON report
4. ✅ Adjust thresholds if needed (see README.md)
5. ✅ Use with recorded exam videos

---

### 📚 Full Documentation

See **README.md** for:
- Complete feature list
- Technical details
- Configuration options
- Troubleshooting guide
- Performance optimization

---

**Ready to detect exam malpractice? Run the program now! 🚀**
