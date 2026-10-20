"""
Incident service — creation, FSM status transitions, detail retrieval.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.models.incident import Incident
from backend.src.models.status_history import IncidentStatusHistory
import uuid, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Valid status transitions (FSM)
VALID_TRANSITIONS = {
    "NEW":          ["UNDER_REVIEW", "VERIFIED", "FALSE_POSITIVE", "CANCELLED"],
    "UNDER_REVIEW": ["VERIFIED", "FALSE_POSITIVE", "CANCELLED"],
    "VERIFIED":     ["ASSIGNED", "FALSE_POSITIVE", "CANCELLED"],
    "ASSIGNED":     ["ACCEPTED", "CANCELLED"],
    "ACCEPTED":     ["RESPONDING", "CANCELLED"],
    "RESPONDING":   ["RESOLVED", "CANCELLED"],
    # Terminal states
    "RESOLVED":     [],
    "FALSE_POSITIVE": [],
    "CANCELLED":    [],
}


def _gen_incident_id() -> str:
    year = datetime.now().year
    return f"INC-{year}-{str(uuid.uuid4().int)[:5]}"


def _serialize(obj):
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


async def create_incident(db: AsyncSession, data: dict) -> dict:
    """Create a new incident + initial status history record."""
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=data.get("incident_id") or _gen_incident_id(),
        incident_type=data.get("incident_type", "SUSPICIOUS_MOVEMENT"),
        severity=data.get("severity", "MEDIUM"),
        risk_score=float(data.get("risk_score", 50.0)),
        ai_confidence=float(data.get("ai_confidence", 70.0)),
        camera_id=data.get("camera_id"),
        location_name=data.get("location_name", "Unknown"),
        latitude=data.get("latitude", 28.6139),
        longitude=data.get("longitude", 77.2090),
        description=data.get("description", ""),
        involved_track_ids=data.get("involved_track_ids", "[]"),
        status=data.get("status", "NEW"),
        source_type=data.get("source_type", "LIVE_CAMERA"),
        video_name=data.get("video_name"),
    )
    db.add(inc)
    await db.flush()  # Get generated id

    # Initial history record
    history = IncidentStatusHistory(
        id=str(uuid.uuid4()),
        incident_id=inc.id,
        from_status="",
        to_status=inc.status,
        changed_by=None,
        notes="Incident created by AI engine",
        changed_at=datetime.now(timezone.utc),
    )
    db.add(history)
    await db.commit()
    await db.refresh(inc)

    logger.info(f"Created incident {inc.incident_id} — {inc.incident_type} [{inc.severity}]")
    return _serialize(inc)


async def transition_status(db: AsyncSession, incident_id: str, new_status: str,
                             changed_by: str = None, notes: str = "") -> dict:
    """Transition an incident to a new status, validating the FSM."""
    q = await db.execute(select(Incident).where(
        (Incident.incident_id == incident_id) | (Incident.id == incident_id)
    ).limit(1))
    inc = q.scalars().first()

    if not inc:
        logger.warning(f"Incident {incident_id} not found for transition to {new_status}")
        return {"error": f"Incident {incident_id} not found"}

    current = inc.status
    allowed = VALID_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        # Allow CANCELLED from any non-terminal state
        if new_status == "CANCELLED" and current not in ("RESOLVED", "FALSE_POSITIVE", "CANCELLED"):
            pass
        else:
            logger.warning(f"Invalid transition {current} → {new_status} for {incident_id}")
            return {"error": f"Cannot transition from {current} to {new_status}"}

    old_status = inc.status
    inc.status = new_status

    if new_status == "RESOLVED":
        inc.resolved_at = datetime.now(timezone.utc)

    history = IncidentStatusHistory(
        id=str(uuid.uuid4()),
        incident_id=inc.id,
        from_status=old_status,
        to_status=new_status,
        changed_by=changed_by,
        notes=notes,
        changed_at=datetime.now(timezone.utc),
    )
    db.add(history)
    await db.commit()
    await db.refresh(inc)

    logger.info(f"Incident {incident_id}: {old_status} → {new_status}")
    return _serialize(inc)


async def get_incident_with_details(db: AsyncSession, incident_id: str) -> dict:
    """Fetch incident + evidence + history."""
    q = await db.execute(select(Incident).where(
        (Incident.incident_id == incident_id) | (Incident.id == incident_id)
    ).limit(1))
    inc = q.scalars().first()
    if not inc:
        return None

    from backend.src.models.evidence import Evidence
    from backend.src.models.status_history import IncidentStatusHistory

    evid_q = await db.execute(select(Evidence).where(Evidence.incident_id == inc.id))
    evidence = [_serialize(e) for e in evid_q.scalars().all()]

    hist_q = await db.execute(
        select(IncidentStatusHistory)
        .where(IncidentStatusHistory.incident_id == inc.id)
        .order_by(IncidentStatusHistory.changed_at.asc())
    )
    history = [_serialize(h) for h in hist_q.scalars().all()]

    result = _serialize(inc)
    result["evidence"] = evidence
    result["history"] = history
    return result
