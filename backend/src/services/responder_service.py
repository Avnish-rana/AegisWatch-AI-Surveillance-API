"""
Responder service — Haversine distance, nearest responder lookup, assignment.
"""
from math import radians, sin, cos, sqrt, atan2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.src.models.responder import Responder
from backend.src.models.incident import Incident
from backend.src.models.assignment import Assignment
import uuid, logging
from datetime import datetime

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS coordinates in km."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(R * c, 3)


async def find_nearest_responders(db: AsyncSession, incident_lat: float, incident_lon: float, limit: int = 5) -> list:
    """Return available responders sorted by distance from an incident location."""
    result = await db.execute(
        select(Responder).where(Responder.availability == "AVAILABLE")
    )
    responders = result.scalars().all()

    ranked = []
    for r in responders:
        if r.latitude is not None and r.longitude is not None:
            dist = haversine_distance(incident_lat, incident_lon, r.latitude, r.longitude)
        else:
            dist = 9999.0
        ranked.append({
            "id": r.id,
            "responder_id": r.responder_id,
            "name": r.name,
            "station": r.station,
            "availability": r.availability,
            "role": r.role,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "distance_km": dist,
        })

    ranked.sort(key=lambda x: x["distance_km"])
    return ranked[:limit]


async def assign_nearest_available(db: AsyncSession, incident_id: str, assigned_by_user_id: str) -> dict:
    """
    Find the nearest available responder and create an Assignment record.
    Also transitions the incident to ASSIGNED status.
    """
    # Resolve incident
    q = await db.execute(
        select(Incident).where(
            (Incident.incident_id == incident_id) | (Incident.id == incident_id)
        ).limit(1)
    )
    incident = q.scalars().first()
    if not incident:
        return {"error": f"Incident {incident_id} not found"}

    inc_lat = incident.latitude or 28.6139
    inc_lon = incident.longitude or 77.2090

    nearest = await find_nearest_responders(db, inc_lat, inc_lon, limit=1)
    if not nearest:
        return {"error": "No available responders found"}

    best = nearest[0]

    # Update responder to BUSY
    r_q = await db.execute(select(Responder).where(Responder.id == best["id"]).limit(1))
    responder = r_q.scalars().first()
    if responder:
        responder.availability = "BUSY"

    # Update incident
    incident.status = "ASSIGNED"
    incident.assigned_responder_id = best["id"]

    # Create assignment record
    assignment = Assignment(
        id=str(uuid.uuid4()),
        incident_id=incident.id,
        responder_id=best["id"],
        assigned_by=assigned_by_user_id,
        distance_km=best["distance_km"],
        assigned_at=datetime.utcnow(),
        status="PENDING",
    )
    db.add(assignment)
    await db.commit()

    return {
        "success": True,
        "incident_id": incident.incident_id,
        "responder": best,
        "distance_km": best["distance_km"],
        "assignment_id": assignment.id,
        "message": f"Assigned to {best['name']} ({best['station']}) — {best['distance_km']} km away",
    }
