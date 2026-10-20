from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.database import get_db
from backend.src.models.evidence import Evidence
import os
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/api/evidence", tags=["evidence"])
EVIDENCE_DIR = os.path.join(os.getcwd(), "data", "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)


def _serialize_evidence(ev) -> dict:
    """Convert an Evidence ORM object to a JSON-safe dict."""
    if ev is None:
        return None
    if isinstance(ev, dict):
        return ev
    d = {}
    for col in ev.__table__.columns:
        val = getattr(ev, col.name, None)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        d[col.name] = val
    # Add a URL the frontend can use to display the image
    if d.get("file_path") and d.get("evidence_type") == "SNAPSHOT":
        fname = os.path.basename(d["file_path"])
        cam_folder = os.path.basename(os.path.dirname(d["file_path"]))
        d["file_url"] = f"/data/evidence/{cam_folder}/{fname}"
    return d


@router.get("/{incident_id}")
async def get_evidence_for_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    from backend.src.models.incident import Incident
    inc_q = await db.execute(select(Incident).where(
        (Incident.incident_id == incident_id) | (Incident.id == incident_id)
    ).limit(1))
    inc = inc_q.scalars().first()
    target_id = inc.id if inc else incident_id
    res = await db.execute(select(Evidence).where((Evidence.incident_id == target_id) | (Evidence.incident_id == incident_id)))
    rows = res.scalars().all()
    return [_serialize_evidence(ev) for ev in rows]


@router.get("/file/{evidence_id}")
async def serve_file(evidence_id: str, db: AsyncSession = Depends(get_db)):
    ev = await db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Evidence not found")
    if not ev.file_path or not os.path.exists(ev.file_path):
        raise HTTPException(404, "Evidence file not found on disk")
    ext = ev.file_path.rsplit(".", 1)[-1].lower()
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else (
        "image/png" if ext == "png" else "application/octet-stream"
    )
    return FileResponse(ev.file_path, media_type=media_type)


@router.post("/{incident_id}")
async def upload_evidence(incident_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    ext = (file.filename or "bin").split(".")[-1].lower()
    file_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(EVIDENCE_DIR, file_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    ev = Evidence(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        evidence_type="SNAPSHOT" if ext in ("jpg", "png", "jpeg") else "VIDEO_CLIP",
        file_path=file_path,
        file_name=file.filename,
        file_size=len(content),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return _serialize_evidence(ev)

