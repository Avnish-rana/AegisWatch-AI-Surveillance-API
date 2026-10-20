"""
AI Service — orchestrates model loading, frame inference, behavior analysis,
evidence capture, and incident creation.

Architecture:
  Frame → Detector → Tracker (built-in YOLOv8) → Behavior Engine → Risk Engine → Incident
"""
import os
import base64
import json
import uuid
import logging
import time
from datetime import datetime
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Global singletons ──────────────────────────────────────
_detector = None          # The active detector instance
_model_loaded = False
_model_error: Optional[str] = None
_model_name: str = "none"

# Per-camera behavior state
_behavior_state: dict = {}

# Cooldown to avoid duplicate incidents
COOLDOWN_SECONDS = 30
FRAME_HISTORY_MAX = 150

# Classes of interest for CCTV
PERSON_CLASS = "person"
OBJECT_CLASSES = {"backpack", "handbag", "suitcase", "umbrella", "laptop", "cell phone"}
WEAPON_CLASSES = {"knife", "scissors"}


# ── Model Loading ──────────────────────────────────────────

def preload_model(model_key: str = "yolov8") -> bool:
    """Load the detector at application startup. Returns True on success."""
    global _detector, _model_loaded, _model_error, _model_name
    if _model_loaded:
        return _detector is not None

    try:
        from models.model_manager import load_model
        _detector = load_model(model_key)
        _model_name = model_key
        _model_loaded = True
        if _detector is None:
            _model_error = "No detector could be loaded"
            logger.warning("⚠️  AI running in NO-DETECTION mode (no model loaded)")
        else:
            logger.info(f"✅ AI detector active: {_detector.model_name}")
        return _detector is not None
    except Exception as e:
        _model_error = str(e)
        _model_loaded = True
        logger.error(f"Model load failed: {e}")
        return False


def get_model_status() -> dict:
    if not _model_loaded:
        return {"status": "not_loaded"}
    if _detector is None:
        return {"status": "unavailable", "error": _model_error}
    name = _detector.model_name or _model_name
    return {
        "status": "ok",
        "model": name,
        "model_name": name,          # alias so health endpoint can use either key
        "hf_id": getattr(_detector, "hf_model_id", None),
        "license": getattr(_detector, "license", None),
    }


# ── Behavior State ─────────────────────────────────────────

def _get_state(camera_id: str) -> dict:
    if camera_id not in _behavior_state:
        _behavior_state[camera_id] = {
            "track_history": {},    # track_id → [(cx, cy, ts), ...]
            "loitering_start": {},  # track_id → first_seen_ts
            "last_seen": {},        # track_id → last_ts
            "object_positions": {}, # oid → {cx,cy,class,first_seen}
            "incident_cooldown": {},# event_type → last_triggered_ts
            "frame_count": 0,
            # Theft state machine per object track id:
            # oid → {phase, owner_tid, prox_frames, last_cx, last_cy,
            #         class, first_seen, gone_since}
            "theft_watch": {},
        }
    return _behavior_state[camera_id]



def _check_cooldown(state: dict, event_type: str) -> bool:
    now = time.time()
    last = state["incident_cooldown"].get(event_type, 0)
    if now - last < COOLDOWN_SECONDS:
        return False
    state["incident_cooldown"][event_type] = now
    return True


def _calc_movement(history: list) -> float:
    if len(history) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(history)):
        dx = history[i][0] - history[i - 1][0]
        dy = history[i][1] - history[i - 1][1]
        total += (dx * dx + dy * dy) ** 0.5
    return total


def _is_erratic(history: list) -> bool:
    if len(history) < 6:
        return False
    changes = 0
    pdx, pdy = 0, 0
    for i in range(1, len(history)):
        dx = history[i][0] - history[i - 1][0]
        dy = history[i][1] - history[i - 1][1]
        if (dx * pdx < 0) or (dy * pdy < 0):
            changes += 1
        pdx, pdy = dx, dy
    return changes > len(history) * 0.4


# ── Theft Detection Helpers ────────────────────────────────

# Tuning constants — practical for a webcam demo at 640×480
THEFT_PROXIMITY_PX = 120      # pixels — person must be this close to "interact"
THEFT_APPROACH_FRAMES = 5     # frames person must stay close before "ownership"
THEFT_GONE_CONFIRM_SEC = 4.0  # seconds object must stay absent before alerting
THEFT_OBJECT_MOVE_PX = 60     # pixels — object moved this far = likely taken
THEFT_CLASSES = {             # objects that can plausibly be stolen
    "backpack", "handbag", "suitcase", "umbrella", "laptop", "cell_phone",
    "bottle", "cup",
}


def _dist2(ax, ay, bx, by):
    """Squared pixel distance between two centroids."""
    return (ax - bx) ** 2 + (ay - by) ** 2


class _TheftEvent:
    """Lightweight value object for a confirmed theft signal."""
    __slots__ = ("obj_id", "obj_class", "person_tid", "confidence", "description")

    def __init__(self, obj_id, obj_class, person_tid, confidence, description):
        self.obj_id = obj_id
        self.obj_class = obj_class
        self.person_tid = person_tid
        self.confidence = confidence
        self.description = description


def _update_theft_watch(
    state: dict,
    objects: list,
    persons: list,
    now_ts: float,
) -> list:
    """
    Advance the per-object theft state machine and return any _TheftEvent
    instances that have reached temporal confirmation.

    State machine per object track-id (stored in state["theft_watch"]):

      PRESENT   — object first seen; wait for a person to approach
      APPROACHED — a person has been within THEFT_PROXIMITY_PX for
                   THEFT_APPROACH_FRAMES consecutive frames
                   → object is now "associated" with that person
      GONE       — object track disappeared; wait THEFT_GONE_CONFIRM_SEC
                   to confirm it wasn't just a temporary occlusion
                   → emit _TheftEvent

    Returns list of _TheftEvent (may be empty).
    """
    tw = state["theft_watch"]
    current_obj_ids = set()
    events = []

    # ── Update state for currently visible objects ─────────
    for obj in objects:
        oid = obj.get("track_id")
        if oid is None:
            continue
        cls = obj["class_name"]
        if cls not in THEFT_CLASSES:
            continue

        current_obj_ids.add(oid)
        cx, cy = obj["cx"], obj["cy"]

        if oid not in tw:
            tw[oid] = {
                "phase": "PRESENT",
                "owner_tid": None,
                "prox_frames": 0,
                "last_cx": cx,
                "last_cy": cy,
                "class": cls,
                "first_seen": now_ts,
                "gone_since": None,
            }
            continue

        rec = tw[oid]
        rec["last_cx"] = cx
        rec["last_cy"] = cy
        rec["gone_since"] = None   # object is back / still visible

        if rec["phase"] == "PRESENT":
            # Check if any person is close enough to count as interaction
            for person in persons:
                if _dist2(cx, cy, person["cx"], person["cy"]) < THEFT_PROXIMITY_PX ** 2:
                    rec["prox_frames"] += 1
                    if rec["prox_frames"] >= THEFT_APPROACH_FRAMES:
                        rec["phase"] = "APPROACHED"
                        rec["owner_tid"] = person.get("track_id")
                    break
            else:
                # Nobody close — slowly decay counter
                rec["prox_frames"] = max(0, rec["prox_frames"] - 1)

        elif rec["phase"] == "APPROACHED":
            # Keep refreshing owner if a person is still close
            for person in persons:
                if _dist2(cx, cy, person["cx"], person["cy"]) < THEFT_PROXIMITY_PX ** 2:
                    rec["owner_tid"] = person.get("track_id")
                    break

    # ── Handle objects that vanished from this frame ───────
    for oid, rec in list(tw.items()):
        if oid in current_obj_ids:
            continue  # still visible

        if rec["phase"] != "APPROACHED":
            # Object vanished but was never approached — not suspicious
            del tw[oid]
            continue

        # Object was approached — start / continue absence timer
        if rec["gone_since"] is None:
            rec["gone_since"] = now_ts

        absent_sec = now_ts - rec["gone_since"]
        if absent_sec >= THEFT_GONE_CONFIRM_SEC:
            # Temporal confirmation: object was associated with a person
            # and has now been absent long enough → POSSIBLE_THEFT
            conf = min(0.90, 0.60 + absent_sec * 0.02)
            owner_tid = rec["owner_tid"]
            desc = (
                f"POSSIBLE_THEFT: {rec['class']} (track #{oid}) "
                f"disappeared after person #{owner_tid} approached it. "
                f"Object absent for {absent_sec:.1f}s. "
                f"AI signal only — requires human verification."
            )
            events.append(_TheftEvent(
                obj_id=oid,
                obj_class=rec["class"],
                person_tid=owner_tid,
                confidence=round(conf, 3),
                description=desc,
            ))
            del tw[oid]   # reset — don't keep firing for same event

    return events


# ── Risk Engine ────────────────────────────────────────────


RISK_LEVELS = {
    "LOITERING":           {"base": 45, "severity": "MEDIUM"},
    "SUSPICIOUS_MOVEMENT": {"base": 55, "severity": "MEDIUM"},
    "ABANDONED_OBJECT":    {"base": 65, "severity": "HIGH"},
    "FIGHT":               {"base": 85, "severity": "CRITICAL"},
    "WEAPON_DETECTED":     {"base": 92, "severity": "CRITICAL"},
    "INTRUSION":           {"base": 72, "severity": "HIGH"},
    "THEFT":               {"base": 78, "severity": "HIGH"},
    "ZONE_INTRUSION":      {"base": 72, "severity": "HIGH"},
    "POSSIBLE_THEFT":      {"base": 75, "severity": "HIGH"},
}



def _risk_score(event_type: str, confidence: float, n_persons: int = 1) -> float:
    base = RISK_LEVELS.get(event_type, {}).get("base", 50)
    # Confidence factor: ±10 points
    score = base + (confidence - 0.7) * 20
    # More people → slightly higher risk
    score += min(5, (n_persons - 1) * 2)
    return min(100.0, max(0.0, round(score, 1)))


# ── Main AIService ─────────────────────────────────────────

class AIService:
    """Facade that processes frames, runs AI, and creates incidents."""

    def __init__(self):
        # Lazy-load if not already done
        if not _model_loaded:
            preload_model()
        self._last_frame = None  # Holds the most-recent decoded frame for evidence capture

    async def process_frame(
        self,
        frame_base64: str,
        camera_id: str,
        db,
        timestamp_sec: float = None,
        video_name: str = None,
        source_type: str = "LIVE_CAMERA",
    ) -> dict:
        """Decode frame, run detection, analyze behavior, return results."""
        try:
            img_bytes = base64.b64decode(frame_base64)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            import cv2
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                return {"detections": [], "risk_score": 0, "incidents_created": []}
        except Exception as e:
            return {"detections": [], "risk_score": 0, "incidents_created": [], "error": str(e)}

        # Keep a reference for evidence capture
        self._last_frame = frame

        # Run detection
        detections = []
        if _detector is not None:
            try:
                detections = _detector.predict(frame, confidence_threshold=0.4)
            except Exception as e:
                logger.warning(f"Detection failed, skipping frame: {e}")
        # No detections = not an error, just an empty frame

        # Behavior analysis
        state = _get_state(camera_id)
        state["frame_count"] += 1
        now_ts = timestamp_sec if timestamp_sec is not None else time.time()

        # Update track history
        for det in detections:
            tid = det.get("track_id", 0)
            cx, cy = det.get("cx", 0), det.get("cy", 0)
            if tid not in state["track_history"]:
                state["track_history"][tid] = []
                state["loitering_start"][tid] = now_ts
            state["track_history"][tid].append((cx, cy, now_ts))
            state["last_seen"][tid] = now_ts
            if len(state["track_history"][tid]) > FRAME_HISTORY_MAX:
                state["track_history"][tid] = state["track_history"][tid][-FRAME_HISTORY_MAX:]

        # Classify detections
        persons = [d for d in detections if d["class_name"] == PERSON_CLASS]
        objects = [d for d in detections if d["class_name"] in OBJECT_CLASSES]
        weapons = [d for d in detections if d["class_name"] in WEAPON_CLASSES]

        incidents_created = []
        risk_score = 0
        incident_type = None

        # ── 1. WEAPON DETECTED ──────────────────────────────
        for w in weapons:
            if _check_cooldown(state, "WEAPON_DETECTED"):
                tid = w.get("track_id", 0)
                conf = w.get("confidence", 0.8)
                rs = _risk_score("WEAPON_DETECTED", conf, len(persons))
                inc = await self._create_incident(
                    db, "WEAPON_DETECTED", "CRITICAL", rs, conf * 100,
                    camera_id, source_type, video_name,
                    f"Possible weapon ({w['class_name']}) detected near Person #{tid}",
                    [tid],
                )
                if inc:
                    incidents_created.append(inc)
                    risk_score = max(risk_score, rs)
                    incident_type = "WEAPON_DETECTED"

        # ── 2. FIGHT / VIOLENCE ──────────────────────────────
        if len(persons) >= 2 and "WEAPON_DETECTED" not in incident_type if incident_type else True:
            for i, p1 in enumerate(persons):
                for p2 in persons[i + 1:]:
                    dist = ((p1["cx"] - p2["cx"]) ** 2 + (p1["cy"] - p2["cy"]) ** 2) ** 0.5
                    if dist < 90:
                        t1 = p1.get("track_id", 0)
                        t2 = p2.get("track_id", 1)
                        h1 = state["track_history"].get(t1, [])
                        h2 = state["track_history"].get(t2, [])
                        mov1 = _calc_movement(h1[-8:] if len(h1) >= 8 else h1)
                        mov2 = _calc_movement(h2[-8:] if len(h2) >= 8 else h2)
                        avg_conf = (p1.get("confidence", 0.8) + p2.get("confidence", 0.8)) / 2
                        if mov1 > 25 or mov2 > 25:
                            if _check_cooldown(state, "FIGHT"):
                                rs = _risk_score("FIGHT", avg_conf, 2)
                                inc = await self._create_incident(
                                    db, "FIGHT", "CRITICAL", rs, avg_conf * 100,
                                    camera_id, source_type, video_name,
                                    f"Possible violence/fight between Person #{t1} and #{t2}",
                                    [t1, t2],
                                )
                                if inc:
                                    incidents_created.append(inc)
                                    risk_score = max(risk_score, rs)
                                    incident_type = "FIGHT"

        # ── 3. LOITERING ────────────────────────────────────
        for p in persons:
            tid = p.get("track_id", 0)
            hist = state["track_history"].get(tid, [])
            if len(hist) >= 20:
                xs = [h[0] for h in hist[-20:]]
                ys = [h[1] for h in hist[-20:]]
                spread = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
                if spread < 80:
                    conf = p.get("confidence", 0.75)
                    if _check_cooldown(state, "LOITERING"):
                        rs = _risk_score("LOITERING", conf, 1)
                        inc = await self._create_incident(
                            db, "LOITERING", "MEDIUM", rs, conf * 100,
                            camera_id, source_type, video_name,
                            f"Person #{tid} loitering in area for extended period",
                            [tid],
                        )
                        if inc:
                            incidents_created.append(inc)
                            risk_score = max(risk_score, rs)
                            if not incident_type:
                                incident_type = "LOITERING"

        # ── 4. SUSPICIOUS MOVEMENT ──────────────────────────
        for p in persons:
            tid = p.get("track_id", 0)
            hist = state["track_history"].get(tid, [])
            if len(hist) >= 15 and _is_erratic(hist[-15:]):
                conf = p.get("confidence", 0.72)
                if _check_cooldown(state, "SUSPICIOUS_MOVEMENT"):
                    rs = _risk_score("SUSPICIOUS_MOVEMENT", conf, 1)
                    inc = await self._create_incident(
                        db, "SUSPICIOUS_MOVEMENT", "MEDIUM", rs, conf * 100,
                        camera_id, source_type, video_name,
                        f"Person #{tid} showing erratic/suspicious movement",
                        [tid],
                    )
                    if inc:
                        incidents_created.append(inc)
                        risk_score = max(risk_score, rs)
                        if not incident_type:
                            incident_type = "SUSPICIOUS_MOVEMENT"

        # ── 5. ABANDONED OBJECT ──────────────────────────────
        for obj in objects:
            oid = obj.get("track_id", 9000 + len(state["object_positions"]))
            if oid not in state["object_positions"]:
                state["object_positions"][oid] = {
                    "class": obj["class_name"], "cx": obj["cx"], "cy": obj["cy"],
                    "first_seen": now_ts,
                }

        for oid, opos in list(state["object_positions"].items()):
            age = now_ts - opos["first_seen"]
            if age > 25:
                near = any(
                    ((p["cx"] - opos["cx"]) ** 2 + (p["cy"] - opos["cy"]) ** 2) ** 0.5 < 150
                    for p in persons
                )
                if not near:
                    if _check_cooldown(state, "ABANDONED_OBJECT"):
                        rs = _risk_score("ABANDONED_OBJECT", 0.75, 0)
                        inc = await self._create_incident(
                            db, "ABANDONED_OBJECT", "HIGH", rs, 75.0,
                            camera_id, source_type, video_name,
                            f"Possible abandoned {opos['class']} — no owner nearby for {age:.0f}s",
                            [oid],
                        )
                        if inc:
                            incidents_created.append(inc)
                            risk_score = max(risk_score, rs)
                            if not incident_type:
                                incident_type = "ABANDONED_OBJECT"

        # ── 6. ZONE INTRUSION ────────────────────────────────
        try:
            from backend.src.services.zone_service import check_zone_intrusions
            zone_events = await check_zone_intrusions(camera_id, persons, db)
            for ev in zone_events:
                # Per-person-per-zone cooldown key (independent of global cooldown)
                cd_key = f"ZONE_INTRUSION:{ev.zone_id}:{ev.track_id}"
                if not _check_cooldown(state, cd_key):
                    continue
                rs = _risk_score("ZONE_INTRUSION", ev.confidence, 1)
                sev = RISK_LEVELS["ZONE_INTRUSION"]["severity"]
                inc = await self._create_incident(
                    db,
                    "POSSIBLE_RESTRICTED_ZONE_INTRUSION",
                    sev,
                    rs,
                    ev.confidence * 100,
                    camera_id,
                    source_type,
                    video_name,
                    ev.description,
                    [ev.track_id],
                )
                if inc:
                    incidents_created.append(inc)
                    risk_score = max(risk_score, rs)
                    if not incident_type:
                        incident_type = "ZONE_INTRUSION"
        except Exception as _zone_err:
            logger.warning(f"Zone intrusion check failed (non-fatal): {_zone_err}")

        # ── 7. POSSIBLE THEFT ────────────────────────────────
        try:
            # Filter to theft-relevant objects only (avoids noise from cars etc.)
            theft_objects = [
                o for o in objects if o["class_name"] in THEFT_CLASSES
            ]
            theft_events = _update_theft_watch(state, theft_objects, persons, now_ts)
            for ev in theft_events:
                cd_key = f"POSSIBLE_THEFT:{ev.obj_id}"
                if not _check_cooldown(state, cd_key):
                    continue
                rs = _risk_score("POSSIBLE_THEFT", ev.confidence, 1)
                sev = RISK_LEVELS["POSSIBLE_THEFT"]["severity"]
                inc = await self._create_incident(
                    db,
                    "POSSIBLE_THEFT",
                    sev,
                    rs,
                    ev.confidence * 100,
                    camera_id,
                    source_type,
                    video_name,
                    ev.description,
                    [ev.person_tid, ev.obj_id],
                )
                if inc:
                    incidents_created.append(inc)
                    risk_score = max(risk_score, rs)
                    if not incident_type:
                        incident_type = "POSSIBLE_THEFT"
        except Exception as _theft_err:
            logger.warning(f"Theft detection failed (non-fatal): {_theft_err}")

        return {
            "detections": detections,
            "risk_score": risk_score,
            "risk_level": _risk_level(risk_score),
            "incident_type": incident_type,
            "incidents_created": incidents_created,
            "person_count": len(persons),
            "object_count": len(objects),
            "frame_count": state["frame_count"],
            "model": _detector.model_name if _detector else "none",
        }

    async def _create_incident(
        self, db, incident_type, severity, risk_score, confidence,
        camera_id, source_type="LIVE_CAMERA", video_name=None,
        description="", track_ids=None
    ) -> dict:
        """Create incident in DB and broadcast WebSocket alert."""
        try:
            from backend.src.services.incident_service import create_incident
            from backend.src.services.alert_service import manager
            from sqlalchemy.future import select
            from backend.src.models.camera import Camera

            # Resolve camera DB row
            cam_q = await db.execute(select(Camera).where(
                (Camera.camera_id == camera_id) | (Camera.id == camera_id)
            ).limit(1))
            cam = cam_q.scalars().first()
            cam_db_id = cam.id if cam else None
            location = cam.location_name if cam else "Unknown"
            lat = cam.latitude if cam else 28.6139
            lon = cam.longitude if cam else 77.2090

            data = {
                "incident_type": incident_type,
                "severity": severity,
                "risk_score": risk_score,
                "ai_confidence": confidence,
                "camera_id": cam_db_id,
                "location_name": location,
                "latitude": lat,
                "longitude": lon,
                "description": description,
                "involved_track_ids": json.dumps(track_ids or []),
                "source_type": source_type,
                "video_name": video_name or "",
            }
            inc = await create_incident(db, data)

            # Save evidence snapshot (JPEG) and insert Evidence DB row
            inc_db_id = inc.get("id") if isinstance(inc, dict) else getattr(inc, "id", None)
            if inc_db_id:
                await _save_evidence_snapshot(
                    camera_id=camera_id,
                    incident_type=incident_type,
                    incident_db_id=inc_db_id,
                    frame=self._last_frame,
                    db=db,
                )

            # WebSocket broadcast — wrap payload in 'data' key so frontend's
            # const { type, data } = msg destructuring gets the incident object
            try:
                inc_id = inc.get("incident_id", "") if isinstance(inc, dict) else getattr(inc, "incident_id", "")
                payload = {
                    "incident_id": inc_id,
                    "id": inc_db_id,
                    "incident_type": incident_type,
                    "severity": severity,
                    "risk_score": risk_score,
                    "source_type": source_type,
                    "camera_id": camera_id,
                    "location_name": location,
                    "description": description,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await manager.broadcast({
                    "type": "incident_alert",
                    "data": payload,
                })
            except Exception:
                pass

            result = inc if isinstance(inc, dict) else {
                col.name: getattr(inc, col.name, None)
                for col in inc.__table__.columns
            }
            result["description"] = description
            return result

        except Exception as e:
            logger.error(f"Failed to create incident [{incident_type}]: {e}", exc_info=True)
            return {
                "incident_type": incident_type, "severity": severity,
                "risk_score": risk_score, "error": str(e),
            }


async def _save_evidence_snapshot(
    camera_id: str,
    incident_type: str,
    incident_db_id: str,
    frame=None,
    db=None,
) -> Optional[str]:
    """
    Save evidence for an incident:
      1. Write the frame as a real JPEG file (if frame is available).
      2. Always write a JSON metadata sidecar file.
      3. Insert an Evidence row in the database.
    """
    try:
        import cv2
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ev_dir = os.path.join("data", "evidence", camera_id.replace(":", "_"))
        os.makedirs(ev_dir, exist_ok=True)

        jpeg_path = None
        jpeg_name = None
        jpeg_size = 0

        # --- 1. Save JPEG if a frame is available ---
        if frame is not None:
            jpeg_name = f"{incident_type}_{ts}.jpg"
            jpeg_path = os.path.join(ev_dir, jpeg_name)
            success = cv2.imwrite(jpeg_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                jpeg_size = os.path.getsize(jpeg_path)
                logger.info(f"Evidence JPEG saved: {jpeg_path} ({jpeg_size} bytes)")
            else:
                logger.warning(f"cv2.imwrite failed for {jpeg_path}")
                jpeg_path = None

        # --- 2. JSON metadata sidecar ---
        meta = {
            "camera_id": camera_id,
            "incident_type": incident_type,
            "timestamp": datetime.utcnow().isoformat(),
            "jpeg_file": jpeg_name,
        }
        json_name = f"{incident_type}_{ts}_meta.json"
        json_path = os.path.join(ev_dir, json_name)
        with open(json_path, "w") as f:
            json.dump(meta, f)

        # --- 3. Insert Evidence DB row ---
        if db is not None and incident_db_id:
            try:
                from backend.src.models.evidence import Evidence
                import uuid
                from datetime import timezone

                if jpeg_path:
                    ev = Evidence(
                        id=str(uuid.uuid4()),
                        incident_id=incident_db_id,
                        evidence_type="SNAPSHOT",
                        file_path=jpeg_path,
                        file_name=jpeg_name,
                        file_size=jpeg_size,
                        timestamp=datetime.now(timezone.utc),
                        metadata_json=json.dumps(meta),
                    )
                    db.add(ev)
                    await db.commit()
                    logger.info(f"Evidence DB row created for incident {incident_db_id}")
            except Exception as ev_err:
                logger.warning(f"Evidence DB insert failed: {ev_err}")

        return jpeg_path or json_path
    except Exception as e:
        logger.error(f"_save_evidence_snapshot failed: {e}")
        return None


def _risk_level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"
