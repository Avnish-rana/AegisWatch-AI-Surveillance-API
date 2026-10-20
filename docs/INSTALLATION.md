# AegisWatch — Installation Guide (Windows)

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| Python | 3.10 | 3.11–3.12 |
| RAM | 4 GB | 8 GB |
| Disk Space | 2 GB | 4 GB |
| Webcam | USB/built-in | USB HD webcam |
| Internet | Required (first run only) | - |

---

## Quick Install (Recommended)

1. Open a terminal in the project root directory.
2. Run the one-click setup:

```bat
setup.bat
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Initialize the database
- Seed demo data (users, cameras, responders)

---

## Manual Install

### Step 1 — Python virtual environment

```bat
python -m venv venv
venv\Scripts\activate
```

### Step 2 — Install dependencies

```bat
pip install -r requirements.txt
```

### Step 3 — Environment configuration

```bat
copy .env.example .env
```

Edit `.env` if needed (see `.env.example` for options).

### Step 4 — Initialize database and seed data

```bat
python database\seed\seed_data.py
```

---

## Running the Application

### Option A — One-click start

```bat
start.bat
```

### Option B — Manual start

```bat
venv\Scripts\activate
python -m backend.src.main
```

Open browser: http://localhost:8000

---

## First Login

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | ADMIN |
| operator | operator123 | OPERATOR |
| responder1 | resp123 | RESPONDER |

---

## Stopping the Application

```bat
stop.bat
```

Or press `Ctrl+C` in the terminal.

---

## Troubleshooting

### Camera permission denied
- Allow browser camera access when prompted
- Check Windows privacy settings → Camera → Allow apps

### Model download fails
- Ensure internet access
- Try: `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"`

### Port 8000 already in use
- Change PORT in `.env`: `PORT=8001`
- Or run: `stop.bat` to kill existing processes

### Database errors
- Delete `surveillance.db` and re-run `python database\seed\seed_data.py`

### Webcam not detected
- Ensure no other application is using the webcam
- Try changing `CAMERA_ID=1` in `.env`
