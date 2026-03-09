# AI Agent Onboarding Prompt

## 🎯 Purpose
This file contains the **Initial Onboarding Prompt** designed to act as the perfect first message your team members should send to their AI agents (like GitHub Copilot, Cursor, Codeium, ChatGPT, or Claude). 

By using this prompt, the AI will deeply explore the project's architecture, understand the core functionalities of the exam malpractice detection system, and be fully prepared to assist with any further development.

---

## 📋 Instructions for Team Members

1. Open your IDE or target AI assistant.
2. Select the option that allows the AI to "read the workspace" (e.g., using `@workspace` in Cursor or Copilot).
3. Copy the prompt below entirely.
4. Paste it into the chat and hit Enter.
5. Wait for the AI to analyze the repository and provide its summary. You are now ready to collaborate!

---

## 🤖 The Masterpiece Prompt

Copy everything inside the block below:

```text
Hello! I have just forked and cloned this repository, "The Silent Invigilator" - an Autonomous Real-Time Exam Malpractice Detection System.

Before we start working on features or bug fixes, I need you to deeply understand the architecture, core algorithms, and directory structure of this project so we can collaborate effectively.

Please act as an Expert Software Architect and complete the following deep-read of my workspace:

### 1. Architectural Overview
Scan the repository and provide a high-level summary of the 3 main domains in this project:
- The **`backend/`** (Python/Flask backend handling the ML models: Mediapipe and YOLOv8).
- The **`mobile_app/`** (Flutter application).
- The relationship between the ML backend and the user interfaces (both Web Dashboard and Mobile App).

### 2. Core Detection Logic (Deep Dive)
Examine `backend/camera.py` and `backend/silent_invigilator.py`. I need you to explicitly understand and summarize the mathematical and logical heuristics used for:
- 3D Head Pose Estimation (Pitch, Yaw, Roll via solvePnP).
- Eye Gaze Tracking (Iris ratio analysis).
- Mouth Aspect Ratio (MAR) and Hand Tracking.
- Object Detection integration (YOLOv8 Nano).
- The "Temporal Behavior Filtering" (Anomaly score accumulation and alert thresholds). 

### 3. Execution & Workflow
Explore the run configurations. Explain the difference between:
- Standalone Desktop Mode (`run_standalone.bat`)
- Web Dashboard Mode (`run_web.bat`)

Once you have investigated these specific files and concepts, reply with:
1. A concise bulleted summary of the core ML detection heuristics.
2. An overview of the application's data flow (from camera frame capture -> ML analysis -> UI status update & reporting).
3. The phrase: "✅ **Workspace Fully Analyzed!** I understand the Silent Invigilator's architecture and ML core. I am strictly aware that all Python ML code lives in `backend/` and the Flutter frontend lives in `mobile_app/`. How can I help you improve the system today?"

Do not suggest code changes yet. I just want to confirm you have built a perfect mental model of this application.
```
