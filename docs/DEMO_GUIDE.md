# AegisWatch — College Demo Guide

## Setup Before Demo (Do This in Advance)

```bat
setup.bat       # First time only — installs deps, creates DB, seeds data
start.bat       # Start the application
```

Open: **http://localhost:8000**

---

## Demo Script (10 Minutes)

### Step 1 — Login (30 seconds)

- Username: `admin`
- Password: `admin123`
- Point out: JWT authentication, role-based access

---

### Step 2 — Dashboard (1 minute)

Show dashboard cards:
- **5 cameras** configured
- **Active incidents** count
- **Available responders** count
- Real-time WebSocket connection indicator

---

### Step 3 — Live CCTV with Webcam (3 minutes)

1. Click **Surveillance** in the sidebar
2. Select **Live CCTV** tab
3. Click **START CAMERA**
4. Browser will ask for webcam permission — click Allow
5. Live video appears with AI overlay

**Show the audience:**
- Green bounding boxes around detected persons
- Track ID numbers (Person #1, Person #2...)
- Confidence percentage
- FPS counter
- Risk level indicator

**Demo events:**
- Wave your hand → AI detects person
- Stay in frame without moving → Loitering alert triggers in ~30s
- Point a scissors/knife toward camera → weapon detection

---

### Step 4 — Video Analysis (2 minutes)

1. Click **Video Analysis** tab (or navigate to Recorded Videos)
2. Click **Upload Video** or drag and drop an MP4 file
3. Click **Start Analysis**
4. Watch progress bar
5. After completion, view:
   - Detection timeline
   - Incident list
   - Risk scores

---

### Step 5 — Incident Management (2 minutes)

1. Click **Incidents** in sidebar
2. Show incident table (type, severity, risk, camera, time, status)
3. Click any incident to view details:
   - AI confidence score
   - Track IDs involved
   - Timestamp
   - Evidence metadata
4. Click **Verify** — incident status changes to VERIFIED
5. Click **Dispatch** — system auto-finds nearest available responder using Haversine formula
6. Show responder assignment + distance

---

### Step 6 — Map View (1 minute)

1. Click **Map** in sidebar
2. Show camera markers (blue)
3. Show incident markers (red)
4. Show responder markers (green)
5. Click a marker for details

---

### Step 7 — Analytics (30 seconds)

1. Click **Analytics**
2. Show incident type distribution chart
3. Show severity breakdown
4. Show active cameras count

---

### Step 8 — Responders (30 seconds)

1. Click **Responders**
2. Show list: Officer Sharma, Officer Patel, etc.
3. Show availability status (AVAILABLE / BUSY / OFFLINE)

---

## Key Talking Points

| Point | Explanation |
|-------|------------|
| Real AI | YOLOv8n (6.5MB) runs locally — no cloud, no internet |
| Hugging Face | facebook/detr-resnet-50 also integrated (Apache 2.0) |
| Privacy | Anonymous tracking IDs only — no face recognition |
| Human-in-loop | AI creates alerts; humans verify before dispatch |
| Haversine formula | Nearest responder calculated with real GPS math |
| WebSocket | Real-time alerts pushed instantly to browser |
| No fake data | All detections from actual YOLOv8 inference |

---

## Ethical Disclaimer (Say This During Demo)

> "This is an academic prototype. All AI detections are probabilistic and
> require human verification before any action is taken. The system does
> not connect to real police or emergency services. No facial recognition
> is used. All persons are tracked by anonymous IDs only."

---

## If Something Goes Wrong

| Problem | Fix |
|---------|-----|
| Webcam shows black | Click Stop, wait 2s, click Start again |
| No AI boxes | Check console — model may be loading (give it 10s) |
| Login fails | Ensure the server is running (start.bat) |
| Incidents page crashes | Refresh the page |
| Port blocked | Change PORT in .env and restart |
