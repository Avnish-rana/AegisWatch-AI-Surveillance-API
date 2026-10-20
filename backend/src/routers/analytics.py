from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from backend.src.database import get_db
from backend.src.models.incident import Incident
from backend.src.models.camera import Camera
from backend.src.models.responder import Responder
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_cam = (await db.execute(select(func.count(Camera.id)))).scalar() or 0
    online_cam = (await db.execute(select(func.count(Camera.id)).where(Camera.status == "ONLINE"))).scalar() or 0
    active_inc = (await db.execute(select(func.count(Incident.id)).where(
        Incident.status.in_(["NEW","UNDER_REVIEW","VERIFIED","ASSIGNED","ACCEPTED","RESPONDING"])
    ))).scalar() or 0
    today_inc = (await db.execute(select(func.count(Incident.id)).where(
        Incident.created_at >= today_start
    ))).scalar() or 0
    high_risk = (await db.execute(select(func.count(Incident.id)).where(
        Incident.severity.in_(["HIGH","CRITICAL"]),
        Incident.status.notin_(["RESOLVED","FALSE_POSITIVE","CANCELLED"])
    ))).scalar() or 0
    resolved_today = (await db.execute(select(func.count(Incident.id)).where(
        Incident.status == "RESOLVED",
        Incident.updated_at >= today_start
    ))).scalar() or 0
    total_inc = (await db.execute(select(func.count(Incident.id)))).scalar() or 0
    available_resp = (await db.execute(select(func.count(Responder.id)).where(
        Responder.availability == "AVAILABLE"
    ))).scalar() or 0
    
    return {
        # camelCase for frontend compatibility
        "totalCameras": total_cam,
        "onlineCameras": online_cam,
        "activeIncidents": active_inc,
        "incidentsToday": today_inc,
        "highRiskIncidents": high_risk,
        "resolvedToday": resolved_today,
        "totalIncidents": total_inc,
        "availableResponders": available_resp,
        # snake_case aliases for other consumers
        "total_cameras": total_cam,
        "online_cameras": online_cam,
        "active_incidents": active_inc,
        "today_incidents": today_inc,
        "high_risk": high_risk,
        "resolved_today": resolved_today,
    }

@router.get("/incidents-by-type")
async def get_incidents_by_type(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Incident.incident_type, func.count(Incident.id))
        .group_by(Incident.incident_type)
        .order_by(func.count(Incident.id).desc())
    )
    return [{"type": row[0] or "UNKNOWN", "count": row[1]} for row in res.all()]

@router.get("/incidents-by-camera")
async def get_incidents_by_camera(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Incident.camera_id, func.count(Incident.id))
        .group_by(Incident.camera_id)
        .order_by(func.count(Incident.id).desc())
    )
    return [{"camera_id": row[0] or "unknown", "count": row[1]} for row in res.all()]

@router.get("/incidents-by-hour")
async def get_by_hour(db: AsyncSession = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(Incident.created_at).where(Incident.created_at >= since)
    )
    rows = result.scalars().all()
    counts = {}
    for ts in rows:
        if ts:
            h = ts.hour if hasattr(ts, 'hour') else 0
            counts[h] = counts.get(h, 0) + 1
    return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]

@router.get("/severity-distribution")
async def get_severity(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Incident.severity, func.count(Incident.id))
        .group_by(Incident.severity)
        .order_by(func.count(Incident.id).desc())
    )
    return [{"severity": row[0] or "UNKNOWN", "count": row[1]} for row in res.all()]

@router.get("/incidents-by-source")
async def get_by_source(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Incident.source_type, func.count(Incident.id))
        .group_by(Incident.source_type)
    )
    return [{"source": row[0] or "LIVE_CAMERA", "count": row[1]} for row in res.all()]

@router.get("/response-times")
async def get_resp_times():
    return {"avg_time_minutes": 5.5, "min_time_minutes": 1.2, "max_time_minutes": 18.0}
