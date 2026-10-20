# AegisWatch — AI-Powered CCTV Surveillance & Incident Response System

> **B.Tech Computer Science Project — Software Prototype**  
> Uses pre-trained AI models (YOLOv8, DETR) for real-time detection.  
> All AI detections are probabilistic. Human verification is mandatory before any action.

---

## Features

- 📡 **Live Webcam CCTV** — PC webcam as virtual security camera
- 🎬 **Recorded Video Analysis** — Upload MP4/AVI/MOV for AI processing
- 🤖 **AI Detection** — YOLOv8 + HuggingFace DETR (switchable at runtime)
- 🔍 **Behaviour Analysis** — Loitering, suspicious movement, abandoned objects, zone intrusion, possible theft
- 🚨 **Incident Management** — Full lifecycle: NEW → VERIFIED → ASSIGNED → RESPONDING → RESOLVED
- 🗺️ **Nearest Responder Dispatch** — Haversine distance calculation
- ⚡ **Real-Time Alerts** — WebSocket push notifications
- 📊 **Analytics Dashboard** — Incident statistics, camera summaries
- 🔐 **Authentication** — JWT, role-based access (Admin / Operator / Responder)

---

## System Requirements

| Requirement | Minimum |
|---|---|
| OS | Windows 10 / 11 |
| Python | 3.9 or later (3.14 recommended) |
| RAM | 4 GB (8 GB recommended for DETR) |
| Disk | 2 GB free (for model cache) |
| Camera | Any USB webcam or built-in laptop camera |
| Browser | Chrome, Edge, or Firefox (latest) |

> **No GPU required.** All AI runs on CPU.

---

## Installation

### 1. Clone / download the project

```
AI-Surveillance-System\
├── backend\
├── frontend\
├── models\
├── database\
├── tests\
├── requirements.txt
└── start.bat          ← run this to launch
```

### 2. Install Python dependencies

Open a terminal in the project folder:

```powershell
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, YOLOv8 (`ultralytics`), HuggingFace Transformers, OpenCV, and all other dependencies.

> **First run:** YOLOv8 and DETR model weights are downloaded automatically (~25 MB + ~160 MB). Requires an internet connection.

### 3. Start the application

Double-click **`start.bat`** — or run from terminal:

```powershell
python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
```

The browser opens automatically at **http://localhost:8000**.

---

## Demo Login Credentials

| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin123` |
| **Operator** | `operator` | `operator123` |
| **Responder** | `responder1` | `resp123` |

> Admin has full access. Operators verify/reject incidents. Responders respond to dispatches.

---

## Using Live Webcam CCTV

1. Log in as **admin** or **operator**
2. Go to **Surveillance** in the sidebar
3. Select the **📡 LIVE CCTV** tab
4. Click **▶ START CAMERA**
5. Allow browser camera permission when prompted
6. The webcam feed appears with AI detection bounding boxes
7. Alerts appear in the **AI Alerts** panel when incidents are detected
8. Click **■ STOP CAMERA** to end the session

> The webcam is treated as **CAM-001 (Main Gate)**. Frames are sent to the AI engine every 2 seconds.

---

## Using Recorded Video Analysis

1. Go to **Surveillance** → **🎬 VIDEO ANALYSIS** tab
2. Drag-and-drop a video file or click to browse
3. Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv` (max 500 MB)
4. Click **🔍 START ANALYSIS**
5. Watch the progress bar and event timeline update in real time
6. When complete, click **View Incidents →** to see any generated incidents
7. Upload another video with **Analyze Another Video**

> The AI processes approximately 3 frames per second of video for speed.

---

## Switching AI Models

The system supports two AI models, switchable without restarting:

| Model | Key | Notes |
|---|---|---|
| **YOLOv8n** (default) | `yolov8` | Fast, COCO 80-class, AGPL-3.0 |
| **DETR ResNet-50** | `detr` | HuggingFace `facebook/detr-resnet-50`, slower on CPU, Apache-2.0 |

Switch via the API:

```powershell
# Switch to DETR
Invoke-RestMethod -Uri http://localhost:8000/api/models/switch -Method POST `
  -Headers @{Authorization="Bearer <token>"} `
  -ContentType "application/json" `
  -Body '{"model":"detr"}'

# Switch back to YOLOv8
Invoke-RestMethod -Uri http://localhost:8000/api/models/switch -Method POST `
  -Headers @{Authorization="Bearer <token>"} `
  -ContentType "application/json" `
  -Body '{"model":"yolov8"}'
```

---

## Incident Workflow

```
AI Detection
    ↓
Incident Created (status: NEW)
    ↓
Operator Reviews → VERIFY or REJECT (→ FALSE POSITIVE)
    ↓
ASSIGN nearest available responder
    ↓
Responder ACCEPTS
    ↓
Responder marks RESPONDING
    ↓
RESOLVED (with notes)
```

All transitions are logged in the incident history.

---

## Project Structure

```
backend/src/
  main.py                  — FastAPI app, all routes, WebSocket
  routers/                 — auth, cameras, incidents, responders, zones,
  │                          evidence, analytics, surveillance, stream
  services/
  │  ai_service.py         — Frame inference, behaviour analysis, incident creation
  │  incident_service.py   — FSM transitions, create/detail
  │  zone_service.py       — Zone geometry, intrusion detection
  │  responder_service.py  — Haversine, nearest-responder dispatch
  │  alert_service.py      — WebSocket connection manager
  models/                  — SQLAlchemy ORM models (11 tables)
  auth.py                  — JWT, bcrypt, role guards

models/
  object_detector.py       — YOLOv8 wrapper
  hf_detector.py           — DETR HuggingFace wrapper
  model_manager.py         — Registry + hot-swap

frontend/
  index.html               — Single-page app entry
  js/pages/                — dashboard, surveillance, incidents,
  │                          responders, zones, map, analytics, cameras
  js/api.js                — Centralised fetch + JWT client

database/seed/seed_data.py — Creates demo cameras, responders, zones, users

tests/
  test_full.py             — 58 automated unit + integration tests
  e2e_test.py              — 29 end-to-end API + WebSocket tests
```

---

## Running Tests

```powershell
# All 58 automated tests
python -m pytest tests/test_full.py -v

# End-to-end tests (requires running server)
$env:PYTHONIOENCODING="utf-8"; python tests/e2e_test.py
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **Port 8000 already in use** | Change port: `--port 8001` in start.bat or run `netstat -ano \| findstr 8000` to find and close the process |
| **Camera permission denied** | Open browser settings → Privacy → Camera → allow `localhost` |
| **No camera found** | Ensure webcam is connected and not used by another app (Teams, Zoom, etc.) |
| **DETR is very slow** | Expected on CPU (~2–5 s/frame). Switch back to YOLOv8 for real-time use |
| **Model download fails** | Check internet connection. Models cached at `%USERPROFILE%\.cache\huggingface\hub\` |
| **Database locked** | Only one uvicorn instance can run at a time. Close the other window |
| **Login fails** | Run `python database\seed\seed_data.py` to re-create demo users |
| **No incidents appearing** | Ensure AI detection is enabled (✓ AI Detection checkbox) and camera is running |

---

## AI Model Attribution & Licenses

| Model | Source | License |
|---|---|---|
| YOLOv8n | [Ultralytics](https://github.com/ultralytics/ultralytics) | AGPL-3.0 |
| DETR ResNet-50 | [facebook/detr-resnet-50](https://huggingface.co/facebook/detr-resnet-50) | Apache-2.0 |

> This project uses pre-trained weights and does **not** train any models from scratch.

---

## Disclaimer

This is an **academic prototype** for demonstration purposes only.  
- AI detections are probabilistic and **require human verification** before any action.  
- The system does **not** connect to real police, emergency services, or any external infrastructure.  
- Do **not** use this system for real security decisions without authorised human oversight.
