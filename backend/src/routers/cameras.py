"""Cameras router — CRUD, toggle, stream info."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.database import get_db
from backend.src.models.camera import Camera
from backend.src.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import uuid, logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cameras", tags=["cameras"])

def _serialize(c):
    if c is None:
        return None
    if isinstance(c, dict):
        return c
    d = {}
    for col in c.__table__.columns:
        val = getattr(c, col.name, None)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        d[col.name] = val
    return d

class CameraCreate(BaseModel):
    camera_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    source_type: str = "DEMO"          # RTSP | WEBCAM | FILE | DEMO
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    latitude: float = 28.6139
    longitude: float = 77.2090
    status: str = "ONLINE"
    is_enabled: bool = True

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    is_enabled: Optional[bool] = None

@router.get("")
async def get_cameras(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Camera)
    if status:
        query = query.where(Camera.status == status)
    result = await db.execute(query.order_by(Camera.camera_id))
    return [_serialize(c) for c in result.scalars().all()]

@router.post("")
async def create_camera(data: CameraCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    c = Camera(
        id=str(uuid.uuid4()),
        camera_id=data.camera_id or f"CAM-{str(uuid.uuid4())[:6].upper()}",
        name=data.name,
        description=data.description,
        source_type=data.source_type,
        source_url=data.source_url,
        location_name=data.location_name,
        latitude=data.latitude,
        longitude=data.longitude,
        status=data.status,
        is_enabled=data.is_enabled,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)

@router.get("/{camera_id}")
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, f"Camera {camera_id} not found")
    return _serialize(c)

@router.put("/{camera_id}")
async def update_camera(camera_id: str, data: CameraUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, "Camera not found")
    for k, v in data.model_dump(exclude_none=True).items():
        if hasattr(c, k):
            setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)

@router.delete("/{camera_id}")
async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, "Camera not found")
    c.is_enabled = False
    c.status = "OFFLINE"
    await db.commit()
    return {"message": "Camera disabled"}

@router.post("/{camera_id}/toggle")
async def toggle_camera(camera_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, "Camera not found")
    c.is_enabled = not c.is_enabled
    c.status = "ONLINE" if c.is_enabled else "OFFLINE"
    await db.commit()
    return {"camera_id": camera_id, "is_enabled": c.is_enabled, "status": c.status}

@router.get("/{camera_id}/stream-info")
async def stream_info(camera_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, "Camera not found")
    return {
        "camera_id": c.camera_id,
        "name": c.name,
        "source_type": c.source_type,
        "source_url": c.source_url,
        "stream_url": f"/api/stream/{c.camera_id}",
        "snapshot_url": f"/api/stream/{c.camera_id}/snapshot",
        "status": c.status,
    }

@router.get("/{camera_id}/zones")
async def camera_zones(camera_id: str, db: AsyncSession = Depends(get_db)):
    from backend.src.models.zone import Zone
    result = await db.execute(select(Camera).where(
        (Camera.camera_id == camera_id) | (Camera.id == camera_id)
    ).limit(1))
    c = result.scalars().first()
    if not c:
        raise HTTPException(404, "Camera not found")
    zones_q = await db.execute(select(Zone).where(Zone.camera_id == c.id))
    zones = zones_q.scalars().all()
    return [{col.name: getattr(z, col.name) for col in z.__table__.columns} for z in zones]
