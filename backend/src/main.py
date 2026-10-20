"""Main FastAPI application — AegisWatch AI Surveillance."""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os, logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

from backend.src.database import init_db
from backend.src.routers import auth, cameras, incidents, responders, evidence, analytics, zones, stream
from backend.src.routers.surveillance import router as surveillance_router
from backend.src.services.alert_service import manager
from backend.src.services.incident_service import create_incident

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────
    logger.info("AegisWatch starting up...")

    # Create required directories
    for d in ["data/evidence", "data/uploads", "data/videos/demo", "data/logs"]:
        os.makedirs(os.path.join(PROJECT_ROOT, d), exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Preload AI model (non-blocking — failure is logged, not fatal)
    model_key = os.getenv("MODEL_NAME", "yolov8")
    try:
        from backend.src.services.ai_service import preload_model
        success = preload_model(model_key)
        if success:
            logger.info(f"✅ AI model [{model_key}] preloaded")
        else:
            logger.warning(f"⚠️  AI model [{model_key}] could not load — running without detections")
    except Exception as e:
        logger.error(f"AI preload error: {e}")

    logger.info(f"🚀 AegisWatch running at http://0.0.0.0:{os.getenv('PORT', '8000')}")
    yield

    # ── Shutdown ───────────────────────────────────────────
    logger.info("AegisWatch shutting down")


app = FastAPI(
    title="AegisWatch AI Surveillance API",
    description="AI-Powered Smart Public Surveillance & Incident Response System",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(incidents.router)
app.include_router(responders.router)
app.include_router(evidence.router)
app.include_router(analytics.router)
app.include_router(zones.router)
app.include_router(stream.router)
app.include_router(surveillance_router)

# ── Static Files ───────────────────────────────────────────
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "data", "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
app.mount("/data/evidence", StaticFiles(directory=EVIDENCE_DIR), name="evidence")

UPLOADS_DIR = os.path.join(PROJECT_ROOT, "data", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/data/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── Routes ─────────────────────────────────────────────────
@app.get("/")
async def root():
    return RedirectResponse(url="/frontend/index.html")


@app.get("/api/health")
async def health_check():
    from backend.src.services.ai_service import get_model_status
    from backend.src.database import AsyncSessionLocal
    from sqlalchemy import text

    db_ok = True
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    model_info = get_model_status()

    import sys, platform
    try:
        import torch
        device = "CUDA" if torch.cuda.is_available() else "CPU"
        cuda_info = f"CUDA {torch.version.cuda}" if torch.cuda.is_available() else "Not available"
    except Exception:
        device = "CPU"
        cuda_info = "torch not installed"

    return {
        "status": "ok",
        "service": "AegisWatch AI Surveillance API",
        "version": "2.0.0",
        "api": "ok",
        "db": "ok" if db_ok else "error",
        "ai": model_info.get("status", "unavailable"),
        "model": model_info.get("model") or model_info.get("model_name"),
        "model_name": model_info.get("model_name") or model_info.get("model"),
        "hf_model_id": model_info.get("hf_id"),
        "license": model_info.get("license"),
        "device": device,
        "cuda": cuda_info,
        "python": sys.version,
        "platform": platform.platform(),
    }


@app.get("/api/models")
async def list_models():
    """List all available AI models and their status."""
    from models.model_manager import list_models
    return list_models()


@app.post("/api/models/switch")
async def switch_model(body: dict):
    """
    Hot-swap the active AI detector without restarting.
    Body: { "model": "yolov8" | "detr" }
    The new model is loaded into the model_manager cache and then set
    as the active detector in ai_service.
    """
    model_key = body.get("model", "").strip().lower()
    if not model_key:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": "model key required"})

    from models.model_manager import load_model, AVAILABLE_MODELS, _loaded_models, _active_model_name
    if model_key not in AVAILABLE_MODELS:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={
            "error": f"Unknown model '{model_key}'. Available: {list(AVAILABLE_MODELS.keys())}"
        })

    try:
        detector = load_model(model_key)
        if detector is None:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=500, content={"error": f"Failed to load model '{model_key}'"})

        # Inject into ai_service globals
        import backend.src.services.ai_service as ai_svc
        ai_svc._detector = detector
        ai_svc._model_name = model_key
        ai_svc._model_loaded = True
        ai_svc._model_error = None

        logger.info(f"Active model switched to [{model_key}] — {detector.model_name}")
        return {
            "success": True,
            "active_model": model_key,
            "model_name": detector.model_name,
            "license": detector.license,
        }
    except Exception as e:
        logger.error(f"Model switch failed: {e}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    logger.info(f"WebSocket client connected: {client_id}")
    try:
        while True:
            data = await websocket.receive_text()
            # Echo keepalive pings
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected: {client_id}")


@app.post("/api/ai/incident")
async def ai_webhook(incident_data: dict):
    """
    Webhook for the AI engine / E2E tests to push new incidents.

    Accepts the short camera_id string (e.g. 'CAM-001') OR the UUID;
    resolves it to the FK-compatible UUID before persisting.
    Also normalises involved_track_ids (list → JSON string).
    """
    from backend.src.database import AsyncSessionLocal
    from backend.src.models.camera import Camera
    from sqlalchemy.future import select
    import json as _json

    async with AsyncSessionLocal() as db:
        # ── Resolve camera_id → UUID ───────────────────────────
        raw_cam = incident_data.get("camera_id", "")
        resolved_cam_id = None
        resolved_location = incident_data.get("location_name", "Unknown")
        resolved_lat = incident_data.get("latitude", 28.6139)
        resolved_lon = incident_data.get("longitude", 77.2090)

        try:
            cam_q = await db.execute(
                select(Camera).where(
                    (Camera.camera_id == raw_cam) | (Camera.id == raw_cam)
                ).limit(1)
            )
            cam = cam_q.scalars().first()
            if cam:
                resolved_cam_id = cam.id
                if not incident_data.get("location_name"):
                    resolved_location = cam.location_name or "Unknown"
                if not incident_data.get("latitude"):
                    resolved_lat = cam.latitude or 28.6139
                if not incident_data.get("longitude"):
                    resolved_lon = cam.longitude or 77.2090
        except Exception as cam_err:
            logger.warning(f"Camera lookup failed for '{raw_cam}': {cam_err}")

        # ── Normalise involved_track_ids ───────────────────────
        track_ids = incident_data.get("involved_track_ids", [])
        if isinstance(track_ids, list):
            track_ids = _json.dumps(track_ids)

        payload = {
            **incident_data,
            "camera_id": resolved_cam_id,
            "location_name": resolved_location,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "involved_track_ids": track_ids,
        }

        try:
            inc = await create_incident(db, payload)

            # ── WebSocket broadcast ────────────────────────────
            try:
                await manager.broadcast({
                    "type": "incident_alert",
                    "data": {
                        "id": inc.get("id"),
                        "incident_id": inc.get("incident_id"),
                        "incident_type": inc.get("incident_type"),
                        "severity": inc.get("severity"),
                        "risk_score": inc.get("risk_score"),
                        "camera_id": raw_cam,
                        "location_name": inc.get("location_name"),
                        "description": inc.get("description"),
                        "timestamp": inc.get("created_at") or "",
                    },
                })
            except Exception as ws_err:
                logger.warning(f"WebSocket broadcast failed: {ws_err}")

            return inc
        except Exception as e:
            logger.error(f"Incident webhook error: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": str(e)})



@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Frontend not found"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.src.main:app", host="0.0.0.0", port=port, reload=False)
