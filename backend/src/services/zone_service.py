"""
Zone Intrusion Service
======================
Provides geometry utilities and database helpers for detecting when a tracked
person enters a restricted zone polygon.

Geometry: Ray-casting point-in-polygon (Shimrat 1962) — pure Python, no extra
dependencies.

Usage (from ai_service.process_frame):
    from backend.src.services.zone_service import check_zone_intrusions
    events = await check_zone_intrusions(camera_id, persons, db)
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.src.models.zone import Zone

logger = logging.getLogger(__name__)


# ── Geometry ───────────────────────────────────────────────────────────────────

def point_in_polygon(px: float, py: float, polygon: list) -> bool:
    """
    Ray-casting point-in-polygon test.

    Args:
        px, py  : test point
        polygon : list of [x, y] or (x, y) vertices (closed or open ring)

    Returns True if the point is strictly inside the polygon.
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])

        # Ray from point going rightward crosses edge i→j ?
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def person_foot_point(det: dict) -> tuple:
    """
    Return the bottom-centre of a detection bounding box — a reasonable proxy
    for where a person is standing on the ground plane.
    """
    bbox = det.get("bbox", [0, 0, 0, 0])
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, float(y2))


def parse_polygon(polygon_json: str) -> Optional[list]:
    """
    Parse a zone's polygon_json field.
    Accepts:
      - JSON array of [x, y] pairs:  [[10,20],[100,20],[100,200],[10,200]]
      - JSON array of {x, y} dicts:  [{"x":10,"y":20}, ...]
    Returns list of (x, y) tuples, or None on parse error.
    """
    try:
        raw = json.loads(polygon_json)
        if not isinstance(raw, list) or len(raw) < 3:
            return None
        pts = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pts.append((float(item[0]), float(item[1])))
            elif isinstance(item, dict):
                pts.append((float(item.get("x", 0)), float(item.get("y", 0))))
            else:
                return None
        return pts
    except Exception:
        return None


# ── Zone cache (per-request, lightweight) ─────────────────────────────────────

async def get_active_zones_for_camera(camera_id: str, db: AsyncSession) -> List[Zone]:
    """
    Fetch all active zones associated with a camera.
    Matches on both camera.id (UUID) and camera.camera_id (e.g. 'CAM-001').
    """
    try:
        # First try matching on the cameras table via join is expensive;
        # zones.camera_id stores the Camera.id UUID (see Zone model FK).
        # But we also support callers that pass the short camera_id string.
        # To handle both, we also look up the Camera row.
        from backend.src.models.camera import Camera
        cam_q = await db.execute(
            select(Camera).where(
                (Camera.camera_id == camera_id) | (Camera.id == camera_id)
            ).limit(1)
        )
        cam = cam_q.scalars().first()
        if cam is None:
            return []

        zone_q = await db.execute(
            select(Zone).where(
                Zone.camera_id == cam.id,
                Zone.is_active == True,  # noqa: E712
            )
        )
        return zone_q.scalars().all()
    except Exception as e:
        logger.warning(f"Could not fetch zones for camera {camera_id}: {e}")
        return []


# ── Main intrusion check ───────────────────────────────────────────────────────

class ZoneIntrusionEvent:
    """Lightweight value object returned per intrusion detected."""
    __slots__ = (
        "zone_id", "zone_name", "zone_type",
        "track_id", "confidence", "description",
    )

    def __init__(self, zone_id, zone_name, zone_type, track_id, confidence, description):
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.zone_type = zone_type
        self.track_id = track_id
        self.confidence = confidence
        self.description = description


async def check_zone_intrusions(
    camera_id: str,
    persons: list,
    db: AsyncSession,
    already_triggered: set = None,
) -> List[ZoneIntrusionEvent]:
    """
    Check all active RESTRICTED zones for the camera and return intrusion events
    for any person whose foot-point is inside a restricted polygon.

    Args:
        camera_id        : live camera_id string or UUID
        persons          : list of detection dicts (class_name == 'person')
        db               : async DB session
        already_triggered: set of (zone_id, track_id) pairs already fired this
                           frame to avoid duplicate events for the same person/zone

    Returns list of ZoneIntrusionEvent (may be empty).
    """
    if not persons:
        return []

    zones = await get_active_zones_for_camera(camera_id, db)
    restricted = [z for z in zones if (z.zone_type or "").upper() == "RESTRICTED"]
    if not restricted:
        return []

    if already_triggered is None:
        already_triggered = set()

    events = []
    for zone in restricted:
        polygon = parse_polygon(zone.polygon_json or "")
        if polygon is None:
            logger.debug(f"Zone {zone.id} ({zone.zone_name}) has invalid polygon — skipping")
            continue

        for person in persons:
            tid = person.get("track_id", 0)
            key = (zone.id, tid)
            if key in already_triggered:
                continue

            px, py = person_foot_point(person)
            if point_in_polygon(px, py, polygon):
                conf = person.get("confidence", 0.80)
                desc = (
                    f"Person #{tid} entered restricted zone '{zone.zone_name}'. "
                    f"Foot position: ({px:.0f}, {py:.0f})."
                )
                events.append(ZoneIntrusionEvent(
                    zone_id=zone.id,
                    zone_name=zone.zone_name,
                    zone_type=zone.zone_type,
                    track_id=tid,
                    confidence=conf,
                    description=desc,
                ))
                already_triggered.add(key)

    return events
