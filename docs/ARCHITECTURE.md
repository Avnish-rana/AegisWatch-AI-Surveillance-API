# AegisWatch — Architecture Document

## System Overview

AegisWatch is a single-server, software-only AI surveillance prototype designed to run on a normal Windows laptop.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         BROWSER (Frontend SPA)                       │
│  Dashboard │ Surveillance │ Incidents │ Map │ Analytics │ Responders │
└───────────────────────────┬──────────────────────────────────────────┘
                            │  HTTP REST + WebSocket
┌───────────────────────────▼──────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)                      │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │  auth  │ │ cameras  │ │incidents │ │responders│ │ surveillance │  │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘ └──────┬──────┘  │
│                                                             │         │
│  ┌──────────────────────────────────────────────────────────▼──────┐  │
│  │                      AI Service Layer                           │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │  │
│  │  │ ModelManager   │  │ Behavior Engine│  │  Risk Engine     │  │  │
│  │  │ (yolov8/detr)  │  │ (rule-based)   │  │  (0-100 score)   │  │  │
│  │  └────────────────┘  └────────────────┘  └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  SQLite Database │  │  WebSocket Mgr   │  │  Static Files     │  │
│  │  (SQLAlchemy)    │  │  (Real-time WS)  │  │  (Frontend SPA)   │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Backend (FastAPI)

| Component | File | Purpose |
|-----------|------|---------|
| Main App | `backend/src/main.py` | Entry point, routing, CORS, startup |
| Database | `backend/src/database.py` | SQLAlchemy async engine (SQLite) |
| Auth | `backend/src/auth.py` | JWT tokens, password hashing |
| AI Service | `backend/src/services/ai_service.py` | Frame processing, behavior analysis |
| Incident Service | `backend/src/services/incident_service.py` | FSM, creation, history |
| Responder Service | `backend/src/services/responder_service.py` | Haversine, nearest-responder |
| Alert Service | `backend/src/services/alert_service.py` | WebSocket broadcast |

### API Routers

| Router | Prefix | Description |
|--------|--------|-------------|
| auth.py | `/api/auth` | Login, me, logout |
| cameras.py | `/api/cameras` | CRUD, toggle, stream-info |
| incidents.py | `/api/incidents` | Full FSM workflow |
| responders.py | `/api/responders` | CRUD, nearest, availability |
| surveillance.py | `/api/surveillance` | Start/stop/status, frame processing |
| analytics.py | `/api/analytics` | Summary, charts, distributions |
| evidence.py | `/api/evidence` | File list, serve |
| zones.py | `/api/zones` | CRUD detection zones |
| stream.py | `/api/stream` | MJPEG stream, snapshot |

### AI Models

| Key | Model | License | Size |
|-----|-------|---------|------|
| `yolov8` (primary) | YOLOv8n | AGPL-3.0 | 6.5 MB |
| `detr` (secondary/HF) | facebook/detr-resnet-50 | Apache 2.0 | 166 MB |

### Database (SQLite via SQLAlchemy async)

Tables: `users`, `cameras`, `incidents`, `evidence`, `responders`, `assignments`,
`zones`, `detection_logs`, `incident_status_history`, `system_settings`

---

## Data Flow

### Live Webcam Mode

```
Webcam → getUserMedia() → HTMLVideoElement
                       → Canvas.drawImage()
                       → canvas.toDataURL() → base64 frame
                       → POST /api/surveillance/frame
                       → ai_service.process_frame()
                       → YOLOv8n.predict()
                       → Behavior Analysis
                       → Incident created (if triggered)
                       → WebSocket broadcast → Browser alert
                       → Bounding boxes drawn on canvas
```

### Video Upload Mode

```
User uploads .mp4 → POST /api/surveillance/upload-video
                  → File saved to data/uploads/
                  → POST /api/surveillance/start-video?camera_id=...
                  → Background thread reads frames via OpenCV
                  → Same AI pipeline as webcam mode
                  → GET /api/surveillance/jobs → progress polling
                  → Results displayed in frontend
```

---

## Security Design

- JWT bearer tokens (24h expiry)
- Password hashing with bcrypt
- No facial recognition (privacy by design)
- Anonymous track IDs only (Person #14 etc.)
- Human-in-the-loop verification before dispatch
- All incident creation requires human verification step

---

## Incident Status FSM

```
NEW → UNDER_REVIEW → VERIFIED → ASSIGNED → ACCEPTED → RESPONDING → RESOLVED
 ↓        ↓             ↓           ↓
CANCELLED CANCELLED   CANCELLED  CANCELLED
          ↓
    FALSE_POSITIVE
```

---

## Deployment (Local)

- Single process: `uvicorn backend.src.main:app --port 8000`
- Frontend served as static files by FastAPI
- No Docker required
- No cloud required
- All data stored in `surveillance.db` (SQLite)
