"""Incidents router — full CRUD + status workflow."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from backend.src.database import get_db
from backend.src.models.incident import Incident
from backend.src.services.incident_service import create_incident, transition_status, get_incident_with_details
from backend.src.services.responder_service import assign_nearest_available
from backend.src.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/incidents", tags=["incidents"])

def _serialize(obj):
    """Convert SQLAlchemy ORM object to dict safely."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        d[col.name] = val
    return d

@router.get("")
async def get_incidents(
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    severity: Optional[str] = None,
    camera_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    query = select(Incident)
    if status:
        query = query.where(Incident.status == status)
    if incident_type:
        query = query.where(Incident.incident_type == incident_type)
    if severity:
        query = query.where(Incident.severity == severity)
    if camera_id:
        query = query.where(Incident.camera_id == camera_id)
    query = query.order_by(desc(Incident.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    incidents = result.scalars().all()
    return [_serialize(i) for i in incidents]

@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_incident_with_details(db, incident_id)
    if not result:
        raise HTTPException(404, f"Incident {incident_id} not found")
    return result

@router.post("")
async def create_new_incident(incident_data: dict, db: AsyncSession = Depends(get_db)):
    return await create_incident(db, incident_data)

@router.post("/{incident_id}/verify")
async def verify_incident(incident_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "VERIFIED", user.id, "Verified by operator")
    return _serialize(result) if result and not isinstance(result, dict) else result

class RejectReason(BaseModel):
    reason: str = "False positive"

@router.post("/{incident_id}/reject")
async def reject_incident(incident_id: str, data: RejectReason, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "FALSE_POSITIVE", user.id, data.reason)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(400, result["error"])
    serialized = _serialize(result) if result and not isinstance(result, dict) else result
    return serialized

class AssignData(BaseModel):
    responder_id: Optional[str] = None

@router.post("/{incident_id}/assign")
async def assign_incident(incident_id: str, data: AssignData, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if data.responder_id:
        result = await transition_status(db, incident_id, "ASSIGNED", user.id, f"Assigned to {data.responder_id}")
        return _serialize(result) if result and not isinstance(result, dict) else result
    else:
        return await assign_nearest_available(db, incident_id, user.id)

@router.post("/{incident_id}/dispatch")
async def dispatch_incident(incident_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Find and assign nearest available responder, then mark DISPATCHED."""
    assignment = await assign_nearest_available(db, incident_id, user.id)
    return assignment

@router.post("/{incident_id}/accept")
async def accept_incident(incident_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "ACCEPTED", user.id, "Responder accepted")
    return _serialize(result) if result and not isinstance(result, dict) else result

@router.post("/{incident_id}/responding")
async def responding_incident(incident_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "RESPONDING", user.id, "Responder en route")
    return _serialize(result) if result and not isinstance(result, dict) else result

class ResolveData(BaseModel):
    notes: str = "Resolved"

@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: str, data: ResolveData, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "RESOLVED", user.id, data.notes)
    return _serialize(result) if result and not isinstance(result, dict) else result

@router.post("/{incident_id}/cancel")
async def cancel_incident(incident_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await transition_status(db, incident_id, "CANCELLED", user.id, "Cancelled manually")
    return _serialize(result) if result and not isinstance(result, dict) else result

@router.get("/{incident_id}/evidence")
async def get_incident_evidence(incident_id: str, db: AsyncSession = Depends(get_db)):
    from backend.src.models.evidence import Evidence
    # Look up by incident_id string OR uuid
    from backend.src.models.incident import Incident
    inc_q = await db.execute(select(Incident).where(
        (Incident.incident_id == incident_id) | (Incident.id == incident_id)
    ).limit(1))
    inc = inc_q.scalars().first()
    if not inc:
        return []
    result = await db.execute(select(Evidence).where(Evidence.incident_id == inc.id))
    evs = result.scalars().all()
    return [_serialize(e) for e in evs]

@router.get("/{incident_id}/history")
async def get_incident_history(incident_id: str, db: AsyncSession = Depends(get_db)):
    from backend.src.models.status_history import IncidentStatusHistory
    from backend.src.models.incident import Incident
    inc_q = await db.execute(select(Incident).where(
        (Incident.incident_id == incident_id) | (Incident.id == incident_id)
    ).limit(1))
    inc = inc_q.scalars().first()
    if not inc:
        return []
    result = await db.execute(
        select(IncidentStatusHistory)
        .where(IncidentStatusHistory.incident_id == inc.id)
        .order_by(IncidentStatusHistory.changed_at.asc())
    )
    return [_serialize(h) for h in result.scalars().all()]
