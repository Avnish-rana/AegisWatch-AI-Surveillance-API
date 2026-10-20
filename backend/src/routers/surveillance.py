from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.database import get_db, AsyncSessionLocal
from backend.src.auth import get_current_user
from backend.src.services.ai_service import AIService
from pydantic import BaseModel
from typing import Optional, List
import uuid, os, json, time, base64, logging, asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/surveillance", tags=["surveillance"])

# In-memory job registry (good enough for prototype)
_jobs = {}

def _serialize_job(job: dict) -> dict:
    """Return job dictionary safe for JSON response (omit subscriber queues)."""
    return {k: v for k, v in job.items() if k != "subscribers"}

class WebcamFrameRequest(BaseModel):
    frame_base64: str  # base64 encoded JPEG
    camera_id: Optional[str] = "CAM-001"
    timestamp: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    detections: Optional[list] = None
    incidents: Optional[list] = None
    video_name: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

@router.post("/webcam-frame")
async def process_webcam_frame(req: WebcamFrameRequest, db: AsyncSession = Depends(get_db)):
    """Process a single webcam frame and return AI detections."""
    try:
        ai = AIService()
        result = await ai.process_frame(req.frame_base64, req.camera_id, db)
        return result
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
        return {"detections": [], "risk_score": 0, "incidents_created": [], "error": str(e)}

@router.post("/upload-video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """Upload a video file for AI analysis. Returns a job ID to poll or stream."""
    # Validate extension
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {allowed}")
    
    # Limit size: 500MB
    MAX_SIZE = 500 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "File too large. Max 500MB.")
    
    # Save to uploads directory
    upload_dir = os.path.join("data", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(contents)
    
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "PENDING",
        "progress": 0.0,
        "message": "Job queued",
        "video_name": file.filename,
        "file_path": file_path,
        "safe_filename": safe_name,
        "video_url": f"/data/uploads/{safe_name}",
        "detections": [],
        "incidents": [],
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error": None,
        "cancelled": False,
        "paused": False,
        "current_frame_b64": None,
        "current_detections": [],
        "current_risk_score": 0.0,
        "current_risk_level": "LOW",
        "current_timestamp_sec": 0.0,
        "current_timestamp_str": "00:00",
        "current_frame_num": 0,
        "total_frames": 0,
        "fps": 0.0,
        "video_fps": 25.0,
        "video_duration_sec": 0.0,
        "video_duration_str": "00:00",
        "subscribers": [],
    }
    
    background_tasks.add_task(_run_video_analysis, job_id, file_path, file.filename)
    return {
        "job_id": job_id,
        "status": "PENDING",
        "message": "Video analysis started",
        "video_name": file.filename,
        "video_url": f"/data/uploads/{safe_name}",
    }

@router.get("/job/{job_id}")
async def get_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    return _serialize_job(_jobs[job_id])

@router.get("/jobs")
async def list_jobs():
    return [_serialize_job(j) for j in reversed(list(_jobs.values()))]

@router.post("/cancel-job/{job_id}")
async def cancel_job(job_id: str, user=Depends(get_current_user)):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    _jobs[job_id]["cancelled"] = True
    _jobs[job_id]["status"] = "CANCELLED"
    _jobs[job_id]["message"] = "Job cancelled by user"
    _notify_subscribers(_jobs[job_id], {
        "type": "cancelled",
        "job_id": job_id,
        "status": "CANCELLED",
        "message": "Job cancelled by user"
    })
    return {"job_id": job_id, "status": "CANCELLED"}

@router.post("/job/{job_id}/cancel")
async def cancel_job_alias(job_id: str, user=Depends(get_current_user)):
    return await cancel_job(job_id, user)

@router.post("/job/{job_id}/pause")
async def pause_job(job_id: str, user=Depends(get_current_user)):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    _jobs[job_id]["paused"] = True
    _notify_subscribers(_jobs[job_id], {
        "type": "paused",
        "job_id": job_id,
        "paused": True,
        "status": "PAUSED"
    })
    return {"job_id": job_id, "status": "PAUSED", "paused": True}

@router.post("/job/{job_id}/resume")
async def resume_job(job_id: str, user=Depends(get_current_user)):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    _jobs[job_id]["paused"] = False
    _notify_subscribers(_jobs[job_id], {
        "type": "resumed",
        "job_id": job_id,
        "paused": False,
        "status": "PROCESSING"
    })
    return {"job_id": job_id, "status": "PROCESSING", "paused": False}

def _notify_subscribers(job: dict, event_data: dict):
    """Deliver event to all connected streaming client queues."""
    for q in list(job.get("subscribers", [])):
        if not q.full():
            try:
                q.put_nowait(event_data)
            except Exception:
                pass

@router.get("/job/{job_id}/stream")
async def stream_job_events(job_id: str):
    """Server-Sent Events (SSE) stream for real-time visible video analysis."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    
    job = _jobs[job_id]
    queue = asyncio.Queue(maxsize=15)
    if "subscribers" not in job:
        job["subscribers"] = []
    job["subscribers"].append(queue)

    async def event_generator():
        try:
            # Send initial current snapshot
            init_event = {
                "type": "state",
                "job_id": job_id,
                "status": job.get("status"),
                "progress": round(job.get("progress", 0.0), 1),
                "frame_b64": job.get("current_frame_b64"),
                "detections": job.get("current_detections", []),
                "risk_score": job.get("current_risk_score", 0.0),
                "risk_level": job.get("current_risk_level", "LOW"),
                "timestamp_sec": job.get("current_timestamp_sec", 0.0),
                "timestamp_str": job.get("current_timestamp_str", "00:00"),
                "total_duration_str": job.get("video_duration_str", "00:00"),
                "fps": job.get("fps", 0.0),
                "frame_num": job.get("current_frame_num", 0),
                "total_frames": job.get("total_frames", 0),
                "paused": job.get("paused", False),
                "incidents": job.get("incidents", []),
            }
            yield f"data: {json.dumps(init_event)}\n\n"

            while True:
                # If terminal state reached and queue drained, send final and exit
                if job.get("status") in ("COMPLETED", "FAILED", "CANCELLED") and queue.empty():
                    fin_event = {
                        "type": "finished",
                        "job_id": job_id,
                        "status": job.get("status"),
                        "progress": round(job.get("progress", 100.0), 1),
                        "message": job.get("message", ""),
                        "incidents": job.get("incidents", []),
                        "total_frames": job.get("total_frames", 0),
                    }
                    yield f"data: {json.dumps(fin_event)}\n\n"
                    break

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=1.5)
                    yield f"data: {json.dumps(msg)}\n\n"
                    if msg.get("type") in ("finished", "completed", "failed", "cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Heartbeat keepalive
                    yield f": ping\n\n"
        finally:
            if queue in job.get("subscribers", []):
                job["subscribers"].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

async def _run_video_analysis(job_id: str, file_path: str, original_name: str):
    """Background task: analyze video file frame by frame with real-time streaming."""
    job = _jobs[job_id]
    job["status"] = "PROCESSING"
    job["message"] = "Initializing AI engine..."
    
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {file_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if total_frames <= 0:
            total_frames = 1000  # estimate
        
        duration_sec = total_frames / fps
        job["total_frames"] = total_frames
        job["video_fps"] = fps
        job["video_duration_sec"] = duration_sec
        job["video_duration_str"] = _sec_to_hms(duration_sec)
        
        ai = AIService()
        frame_num = 0
        # Process every Nth frame for smooth visible playback while maintaining real-time performance
        process_every = max(1, int(fps // 5)) if fps > 10 else 1
        all_detections = []
        timeline_events = []
        
        calc_fps = 0.0
        last_frame_time = time.time()
        
        job["message"] = f"Analyzing video: {original_name}"
        
        async with AsyncSessionLocal() as db:
            while True:
                if job.get("cancelled"):
                    break
                
                # Support pause/resume
                while job.get("paused"):
                    if job.get("cancelled"):
                        break
                    await asyncio.sleep(0.1)
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_num += 1
                
                # Only process every Nth frame
                if frame_num % process_every != 0:
                    continue
                
                # Update progress
                progress = min(99.0, (frame_num / total_frames) * 100)
                job["progress"] = progress
                job["message"] = f"Frame {frame_num}/{total_frames} ({progress:.0f}%)"
                
                # Calculate processing FPS
                now = time.time()
                dt = now - last_frame_time
                last_frame_time = now
                if dt > 0:
                    instant_fps = 1.0 / dt
                    calc_fps = 0.8 * calc_fps + 0.2 * instant_fps if calc_fps > 0 else instant_fps
                
                # Encode frame to base64 for AI service and live browser player
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf.tobytes()).decode()
                
                timestamp_sec = frame_num / fps
                timestamp_str = _sec_to_hms(timestamp_sec)
                
                result = await ai.process_frame(
                    frame_b64, 
                    f"VIDEO:{original_name}",
                    db,
                    timestamp_sec=timestamp_sec,
                    video_name=original_name,
                    source_type="RECORDED_VIDEO"
                )
                
                frame_dets = result.get("detections", [])
                if frame_dets:
                    for det in frame_dets:
                        det["timestamp_sec"] = timestamp_sec
                        det["timestamp_str"] = timestamp_str
                        det["frame"] = frame_num
                        all_detections.append(det)
                
                new_incidents = result.get("incidents_created", [])
                if new_incidents:
                    for inc in new_incidents:
                        inc["timestamp_sec"] = timestamp_sec
                        inc["timestamp_str"] = timestamp_str
                        timeline_events.append(inc)
                        job["incidents"].append(inc)
                
                # Keep last 200 in job
                job["detections"] = all_detections[-200:]
                job["timeline"] = timeline_events
                
                # Update live state in job
                job["current_frame_b64"] = frame_b64
                job["current_detections"] = frame_dets
                job["current_risk_score"] = result.get("risk_score", 0.0)
                job["current_risk_level"] = result.get("risk_level", "LOW")
                job["current_timestamp_sec"] = timestamp_sec
                job["current_timestamp_str"] = timestamp_str
                job["current_frame_num"] = frame_num
                job["fps"] = round(calc_fps, 1)
                job["model"] = result.get("model", "yolov8")
                
                # Broadcast live frame event to streaming viewers
                frame_event = {
                    "type": "frame",
                    "job_id": job_id,
                    "status": "PROCESSING",
                    "progress": round(progress, 1),
                    "frame_b64": frame_b64,
                    "detections": frame_dets,
                    "risk_score": result.get("risk_score", 0.0),
                    "risk_level": result.get("risk_level", "LOW"),
                    "timestamp_sec": round(timestamp_sec, 2),
                    "timestamp_str": timestamp_str,
                    "total_duration_str": job["video_duration_str"],
                    "fps": round(calc_fps, 1),
                    "frame_num": frame_num,
                    "total_frames": total_frames,
                    "paused": False,
                    "model": result.get("model", "yolov8"),
                    "new_incidents": new_incidents,
                }
                _notify_subscribers(job, frame_event)
                # Yield control to event loop so SSE flushes and incoming requests are handled
                await asyncio.sleep(0.01)
        
        cap.release()
        
        if not job.get("cancelled"):
            job["status"] = "COMPLETED"
            job["progress"] = 100.0
            job["message"] = f"Analysis complete: {len(timeline_events)} events detected in {frame_num} frames"
            job["completed_at"] = datetime.utcnow().isoformat()
            job["total_frames"] = frame_num
            job["video_fps"] = fps
            
            _notify_subscribers(job, {
                "type": "finished",
                "job_id": job_id,
                "status": "COMPLETED",
                "progress": 100.0,
                "message": job["message"],
                "incidents": job["incidents"],
                "total_frames": frame_num,
                "video_fps": fps,
            })
    
    except Exception as e:
        logger.error(f"Video analysis error for job {job_id}: {e}", exc_info=True)
        job["status"] = "FAILED"
        job["error"] = str(e)
        job["message"] = f"Analysis failed: {e}"
        job["completed_at"] = datetime.utcnow().isoformat()
        _notify_subscribers(job, {
            "type": "failed",
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e),
            "message": f"Analysis failed: {e}",
        })

def _sec_to_hms(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
