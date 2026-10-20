"""Responders router — list, CRUD, availability, nearest."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.database import get_db
from backend.src.models.responder import Responder
from backend.src.services.responder_service import find_nearest_responders
from backend.src.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import uuid, logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/responders", tags=["responders"])

def _serialize(r):
    if r is None:
        return None
    if isinstance(r, dict):
        return r
    d = {}
    for col in r.__table__.columns:
        val = getattr(r, col.name, None)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        d[col.name] = val
    return d

class ResponderCreate(BaseModel):
    responder_id: Optional[str] = None
    name: str
    station: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: float = 28.6139
    longitude: float = 77.2090
    availability: str = "AVAILABLE"
    role: str = "PATROL_OFFICER"
    status: str = "ON_DUTY"

class AvailabilityUpdate(BaseModel):
    availability: str  # AVAILABLE | BUSY | OFFLINE

@router.get("")
async def get_responders(availability: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Responder)
    if availability:
        query = query.where(Responder.availability == availability)
    result = await db.execute(query.order_by(Responder.name))
    return [_serialize(r) for r in result.scalars().all()]

@router.post("")
async def create_responder(data: ResponderCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    r = Responder(
        id=str(uuid.uuid4()),
        responder_id=data.responder_id or f"R-{str(uuid.uuid4())[:8].upper()}",
        name=data.name,
        station=data.station,
        phone=data.phone,
        email=data.email,
        latitude=data.latitude,
        longitude=data.longitude,
        availability=data.availability,
        role=data.role,
        status=data.status,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _serialize(r)

@router.get("/nearest")
async def nearest_responders(lat: float, lon: float, limit: int = 5, db: AsyncSession = Depends(get_db)):
    """Return available responders sorted by distance from given coordinates."""
    results = await find_nearest_responders(db, lat, lon, limit)
    return results

@router.get("/{responder_id}")
async def get_responder(responder_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Responder).where(
        (Responder.responder_id == responder_id) | (Responder.id == responder_id)
    ).limit(1))
    r = result.scalars().first()
    if not r:
        raise HTTPException(404, f"Responder {responder_id} not found")
    return _serialize(r)

@router.put("/{responder_id}")
async def update_responder(responder_id: str, data: dict, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Responder).where(
        (Responder.responder_id == responder_id) | (Responder.id == responder_id)
    ).limit(1))
    r = result.scalars().first()
    if not r:
        raise HTTPException(404, "Responder not found")
    for k, v in data.items():
        if hasattr(r, k):
            setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return _serialize(r)

@router.post("/{responder_id}/availability")
async def update_availability(responder_id: str, data: AvailabilityUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Responder).where(
        (Responder.responder_id == responder_id) | (Responder.id == responder_id)
    ).limit(1))
    r = result.scalars().first()
    if not r:
        raise HTTPException(404, "Responder not found")
    r.availability = data.availability
    await db.commit()
    return {"responder_id": responder_id, "availability": data.availability}

@router.get("/{responder_id}/assignments")
async def get_assignments(responder_id: str, db: AsyncSession = Depends(get_db)):
    from backend.src.models.assignment import Assignment
    result = await db.execute(select(Responder).where(
        (Responder.responder_id == responder_id) | (Responder.id == responder_id)
    ).limit(1))
    r = result.scalars().first()
    if not r:
        raise HTTPException(404, "Responder not found")
    asgn = await db.execute(select(Assignment).where(Assignment.responder_id == r.id))
    assignments = asgn.scalars().all()
    return [_serialize(a) for a in assignments]
