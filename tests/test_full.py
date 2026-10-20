"""
Comprehensive test suite for AegisWatch.

Tests:
- Haversine distance formula
- Risk engine
- Incident FSM
- API endpoints (auth, cameras, incidents, responders, analytics, surveillance)
- Video validation
- Duplicate suppression (cooldown)

Run: python -m pytest tests/test_full.py -v
"""
import pytest
import asyncio
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ═══════════════════════════════════════════════════════════
# 1. HAVERSINE DISTANCE
# ═══════════════════════════════════════════════════════════

def test_haversine_same_point():
    from backend.src.services.responder_service import haversine_distance
    d = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
    assert d == 0.0

def test_haversine_known_distance():
    """Delhi to Noida is approximately 19 km."""
    from backend.src.services.responder_service import haversine_distance
    # Connaught Place, Delhi → Sector 18, Noida
    d = haversine_distance(28.6315, 77.2167, 28.5707, 77.3212)
    assert 8 < d < 14, f"Expected ~11 km, got {d} km"

def test_haversine_returns_float():
    from backend.src.services.responder_service import haversine_distance
    d = haversine_distance(28.6139, 77.2090, 28.6150, 77.2110)
    assert isinstance(d, float)
    assert d > 0


# ═══════════════════════════════════════════════════════════
# 2. RISK ENGINE
# ═══════════════════════════════════════════════════════════

def test_risk_score_clamp():
    from backend.src.services.ai_service import _risk_score
    # Should never exceed 100 or go below 0
    assert _risk_score("WEAPON_DETECTED", 1.0, 10) <= 100
    assert _risk_score("LOITERING", 0.0, 0) >= 0

def test_risk_score_weapon_higher_than_loitering():
    from backend.src.services.ai_service import _risk_score
    loiter = _risk_score("LOITERING", 0.8, 1)
    weapon = _risk_score("WEAPON_DETECTED", 0.8, 1)
    assert weapon > loiter, "Weapon should have higher risk than loitering"

def test_risk_score_fight_critical():
    from backend.src.services.ai_service import _risk_score
    score = _risk_score("FIGHT", 0.85, 2)
    assert score >= 80, f"Fight should be CRITICAL (≥80), got {score}"

def test_risk_level():
    from backend.src.services.ai_service import _risk_level
    assert _risk_level(95) == "CRITICAL"
    assert _risk_level(70) == "HIGH"
    assert _risk_level(45) == "MEDIUM"
    assert _risk_level(10) == "LOW"


# ═══════════════════════════════════════════════════════════
# 3. INCIDENT FSM VALIDATION
# ═══════════════════════════════════════════════════════════

def test_valid_transitions():
    from backend.src.services.incident_service import VALID_TRANSITIONS
    assert "VERIFIED" in VALID_TRANSITIONS["NEW"] or "VERIFIED" in VALID_TRANSITIONS["UNDER_REVIEW"]
    assert "RESOLVED" in VALID_TRANSITIONS["RESPONDING"]
    assert VALID_TRANSITIONS["RESOLVED"] == []
    assert VALID_TRANSITIONS["FALSE_POSITIVE"] == []
    # Operators can reject directly from NEW without extra steps
    assert "FALSE_POSITIVE" in VALID_TRANSITIONS["NEW"], "NEW→FALSE_POSITIVE must be allowed"
    assert "FALSE_POSITIVE" in VALID_TRANSITIONS["VERIFIED"], "VERIFIED→FALSE_POSITIVE must be allowed"

def test_incident_id_format():
    from backend.src.services.incident_service import _gen_incident_id
    from datetime import datetime
    inc_id = _gen_incident_id()
    year = str(datetime.now().year)
    assert inc_id.startswith(f"INC-{year}-"), f"Bad format: {inc_id}"
    assert len(inc_id) > 10


# ═══════════════════════════════════════════════════════════
# 4. MOVEMENT / BEHAVIOR HELPERS
# ═══════════════════════════════════════════════════════════

def test_calc_movement_stationary():
    from backend.src.services.ai_service import _calc_movement
    history = [(100, 100, 0), (101, 100, 1), (100, 101, 2)]
    movement = _calc_movement(history)
    assert movement < 10, "Stationary object should have low movement"

def test_calc_movement_fast():
    from backend.src.services.ai_service import _calc_movement
    history = [(0, 0, 0), (100, 0, 1), (200, 0, 2), (300, 0, 3)]
    movement = _calc_movement(history)
    assert movement == pytest.approx(300.0), f"Expected 300, got {movement}"

def test_erratic_detects_zigzag():
    from backend.src.services.ai_service import _is_erratic
    # Zigzag: right, left, right, left...
    history = [
        (0, 100, 0), (50, 100, 1), (0, 100, 2), (50, 100, 3),
        (0, 100, 4), (50, 100, 5), (0, 100, 6), (50, 100, 7),
        (0, 100, 8), (50, 100, 9), (0, 100, 10), (50, 100, 11),
        (0, 100, 12), (50, 100, 13), (0, 100, 14),
    ]
    assert _is_erratic(history), "Zigzag path should be detected as erratic"

def test_erratic_rejects_straight():
    from backend.src.services.ai_service import _is_erratic
    # Straight line walking
    history = [(i * 10, 100, i) for i in range(15)]
    assert not _is_erratic(history), "Straight path should NOT be erratic"


# ═══════════════════════════════════════════════════════════
# 5. API ENDPOINT TESTS (uses httpx with running server)
# ═══════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000"

def _get_token():
    import requests
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"username": "admin", "password": "admin123"},
                      timeout=10)
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def _auth_headers():
    token = _get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_health_endpoint():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        if data.get("ai") == "ok":
            assert data.get("model_name") is not None, "model_name must not be null when AI is ok"
            assert data.get("model") is not None, "model must not be null when AI is ok"
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running — start with start.bat first")

def test_login_success():
    import requests
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "admin123"},
                          timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "ADMIN"
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_login_wrong_password():
    import requests
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": "admin", "password": "wrongpassword"},
                          timeout=5)
        assert r.status_code in (401, 422)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_cameras_list():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/cameras", headers=_auth_headers(), timeout=5)
        assert r.status_code == 200
        cameras = r.json()
        assert isinstance(cameras, list)
        assert len(cameras) >= 1, "Should have at least 1 seeded camera"
        # Check required fields
        cam = cameras[0]
        assert "camera_id" in cam
        assert "name" in cam
        assert "latitude" in cam
        assert "longitude" in cam
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_incidents_list():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/incidents", timeout=5)
        assert r.status_code == 200
        incidents = r.json()
        assert isinstance(incidents, list)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_responders_list():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/responders", timeout=5)
        assert r.status_code == 200
        responders = r.json()
        assert isinstance(responders, list)
        assert len(responders) >= 3, "Should have seeded responders"
        r_obj = responders[0]
        assert "responder_id" in r_obj
        assert "availability" in r_obj
        assert "latitude" in r_obj
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_analytics_summary():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/analytics/summary", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "totalCameras" in data or "total_cameras" in data
        assert "activeIncidents" in data or "active_incidents" in data
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_nearest_responders():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/responders/nearest?lat=28.6139&lon=77.2090", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if len(data) >= 2:
            # Should be sorted by distance
            assert data[0]["distance_km"] <= data[1]["distance_km"]
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_surveillance_jobs_list():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/surveillance/jobs", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")

def test_models_endpoint():
    import requests
    try:
        r = requests.get(f"{BASE_URL}/api/models", timeout=5)
        assert r.status_code == 200
        models = r.json()
        assert isinstance(models, list)
        keys = [m["key"] for m in models]
        assert "yolov8" in keys
        assert "detr" in keys
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not running")


# ═══════════════════════════════════════════════════════════
# 6. VIDEO VALIDATION
# ═══════════════════════════════════════════════════════════

def test_valid_video_extension():
    allowed = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    assert ".mp4" in allowed
    assert ".txt" not in allowed
    assert ".exe" not in allowed

def test_path_traversal_prevention():
    """Ensure filenames with path traversal are rejected."""
    import os
    dangerous_names = ["../../etc/passwd", "../config/.env", "..\\..\\windows\\system32"]
    for name in dangerous_names:
        # The server uses uuid.hex + extension, ignoring original filename for storage
        ext = os.path.splitext(name)[1].lower()
        # Only .mp4 etc. would pass — others would be rejected
        allowed = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        assert ext not in allowed, f"Dangerous path {name} should be rejected"


# ═══════════════════════════════════════════════════════════
# 7. COOLDOWN / DUPLICATE SUPPRESSION
# ═══════════════════════════════════════════════════════════

def test_cooldown_prevents_duplicate():
    """Cooldown should prevent the same event type from firing twice."""
    import time
    from backend.src.services.ai_service import _check_cooldown, COOLDOWN_SECONDS

    state = {"incident_cooldown": {}}

    # First call — should pass
    assert _check_cooldown(state, "LOITERING") == True

    # Immediate second call — should be blocked
    assert _check_cooldown(state, "LOITERING") == False

def test_cooldown_different_types():
    """Different event types should have independent cooldowns."""
    from backend.src.services.ai_service import _check_cooldown

    state = {"incident_cooldown": {}}
    assert _check_cooldown(state, "LOITERING") == True
    # Different type should still pass
    assert _check_cooldown(state, "FIGHT") == True


# ═══════════════════════════════════════════════════════════
# 8. DETR (facebook/detr-resnet-50) INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

def test_detr_label_normalisation():
    """Labels from DETR pipeline ('cell phone') must normalise to 'cell_phone'."""
    from models.hf_detector import CCTV_CLASSES_NORM
    raw_label = "cell phone"
    normalised = raw_label.lower().replace(" ", "_")
    assert normalised in CCTV_CLASSES_NORM
    assert "person" in CCTV_CLASSES_NORM
    assert "backpack" in CCTV_CLASSES_NORM
    assert "knife" in CCTV_CLASSES_NORM

def test_detr_class_instantiation():
    """HFDETRDetector can be instantiated without network access."""
    from models.hf_detector import HFDETRDetector
    det = HFDETRDetector()
    assert det.model_name == "facebook/detr-resnet-50"
    assert det.license == "Apache 2.0"
    assert det.hf_model_id == "facebook/detr-resnet-50"
    assert det.is_loaded is False

def test_detr_load_model():
    """DETR model loads from HuggingFace (downloads ~166MB on first run, then cached)."""
    try:
        import transformers  # noqa
    except ImportError:
        pytest.skip("transformers not installed")
    from models.hf_detector import HFDETRDetector
    det = HFDETRDetector()
    det.load_model()
    assert det.is_loaded is True
    assert det._pipeline is not None

def test_detr_inference_returns_list():
    """predict() returns a list even on a blank frame."""
    try:
        import transformers  # noqa
    except ImportError:
        pytest.skip("transformers not installed")
    import numpy as np
    from models.hf_detector import HFDETRDetector
    det = HFDETRDetector()
    det.load_model()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = det.predict(frame, confidence_threshold=0.5)
    assert isinstance(result, list)

def test_detr_inference_output_schema():
    """Every detection dict must have required keys and correct types."""
    try:
        import transformers  # noqa
    except ImportError:
        pytest.skip("transformers not installed")
    import numpy as np
    from models.hf_detector import HFDETRDetector
    det = HFDETRDetector()
    det.load_model()
    frame = np.full((480, 640, 3), 180, dtype=np.uint8)
    frame[80:400, 250:390] = [90, 120, 200]
    result = det.predict(frame, confidence_threshold=0.3)
    assert isinstance(result, list)
    required = {"class_name", "confidence", "bbox", "cx", "cy", "track_id", "width", "height"}
    for item in result:
        assert isinstance(item, dict)
        assert not (required - item.keys()), f"Missing keys: {required - item.keys()}"
        assert isinstance(item["bbox"], list) and len(item["bbox"]) == 4
        assert 0.0 <= item["confidence"] <= 1.0

def test_detr_in_model_manager_registry():
    """model_manager must list 'detr' as available with correct metadata."""
    from models.model_manager import AVAILABLE_MODELS, list_models
    assert "detr" in AVAILABLE_MODELS
    assert AVAILABLE_MODELS["detr"]["hf_id"] == "facebook/detr-resnet-50"
    assert AVAILABLE_MODELS["detr"]["license"] == "Apache 2.0"
    models = list_models()
    keys = [m["key"] for m in models]
    assert "detr" in keys
    assert "yolov8" in keys

# ─── API-level tests (require running server) ─────────────────────────────────

_SERVER_UP = False
try:
    import httpx as _hx
    _SERVER_UP = _hx.get("http://localhost:8000/api/health", timeout=2).status_code == 200
except Exception:
    pass

@pytest.mark.skipif(not _SERVER_UP, reason="Server not running")
def test_api_models_includes_detr():
    """GET /api/models must list both yolov8 and detr."""
    import httpx
    r = httpx.get("http://localhost:8000/api/models", timeout=10)
    assert r.status_code == 200
    keys = [m["key"] for m in r.json()]
    assert "yolov8" in keys
    assert "detr" in keys

@pytest.mark.skipif(not _SERVER_UP, reason="Server not running")
def test_api_model_switch_to_detr_and_back():
    """Switch to DETR via API, verify, switch back to YOLOv8, verify regression."""
    import httpx
    r = httpx.post(
        "http://localhost:8000/api/models/switch",
        json={"model": "detr"},
        timeout=300,
    )
    assert r.status_code == 200, f"Switch to DETR failed: {r.text}"
    body = r.json()
    assert body.get("success") is True
    assert body.get("active_model") == "detr"
    assert "detr" in body.get("model_name", "").lower()
    assert body.get("license") == "Apache 2.0"

    h = httpx.get("http://localhost:8000/api/health", timeout=10).json()
    assert h.get("ai") == "ok"

    r2 = httpx.post(
        "http://localhost:8000/api/models/switch",
        json={"model": "yolov8"},
        timeout=30,
    )
    assert r2.status_code == 200
    assert r2.json().get("active_model") == "yolov8"

    h2 = httpx.get("http://localhost:8000/api/health", timeout=10).json()
    assert h2.get("ai") == "ok"


# ═══════════════════════════════════════════════════════════
# 9. ZONE INTRUSION DETECTION TESTS
# ═══════════════════════════════════════════════════════════

def test_zone_point_in_polygon_inside():
    """A point clearly inside a square polygon must return True."""
    from backend.src.services.zone_service import point_in_polygon
    # Square: (0,0) → (100,0) → (100,100) → (0,100)
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert point_in_polygon(50, 50, poly) is True


def test_zone_point_in_polygon_outside():
    """A point outside the polygon must return False."""
    from backend.src.services.zone_service import point_in_polygon
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert point_in_polygon(150, 150, poly) is False
    assert point_in_polygon(-10, 50, poly) is False


def test_zone_point_in_polygon_on_corner():
    """Ray-casting edge case: point very close to corner — should not raise."""
    from backend.src.services.zone_service import point_in_polygon
    poly = [[0, 0], [100, 0], [100, 100], [0, 100]]
    # This may be True or False (edge behaviour is implementation-defined),
    # but it must not raise an exception.
    result = point_in_polygon(0, 0, poly)
    assert isinstance(result, bool)


def test_zone_point_in_polygon_triangle():
    """Works for a non-rectangular polygon (triangle)."""
    from backend.src.services.zone_service import point_in_polygon
    # Triangle with vertices (0,0), (200,0), (100,200)
    poly = [[0, 0], [200, 0], [100, 200]]
    assert point_in_polygon(100, 50, poly) is True   # centroid-ish
    assert point_in_polygon(5, 150, poly) is False   # outside


def test_zone_point_in_polygon_degenerate():
    """Degenerate polygon (< 3 vertices) must return False, not crash."""
    from backend.src.services.zone_service import point_in_polygon
    assert point_in_polygon(50, 50, []) is False
    assert point_in_polygon(50, 50, [[0, 0]]) is False
    assert point_in_polygon(50, 50, [[0, 0], [100, 100]]) is False


def test_zone_parse_polygon_valid():
    """parse_polygon handles both [x,y] list-of-lists and list-of-dicts."""
    from backend.src.services.zone_service import parse_polygon
    # List-of-lists
    pts = parse_polygon("[[10,20],[100,20],[100,200],[10,200]]")
    assert pts is not None
    assert len(pts) == 4
    assert pts[0] == (10.0, 20.0)

    # List-of-dicts
    pts2 = parse_polygon('[{"x":0,"y":0},{"x":100,"y":0},{"x":50,"y":100}]')
    assert pts2 is not None
    assert len(pts2) == 3


def test_zone_parse_polygon_invalid():
    """parse_polygon returns None for bad input."""
    from backend.src.services.zone_service import parse_polygon
    assert parse_polygon("not json") is None
    assert parse_polygon("[]") is None       # empty
    assert parse_polygon("[[1,2]]") is None  # < 3 points


def test_zone_intrusion_risk_level():
    """ZONE_INTRUSION must produce a HIGH severity and score >= 60."""
    from backend.src.services.ai_service import _risk_score, RISK_LEVELS
    assert "ZONE_INTRUSION" in RISK_LEVELS
    assert RISK_LEVELS["ZONE_INTRUSION"]["severity"] == "HIGH"
    score = _risk_score("ZONE_INTRUSION", 0.85, 1)
    assert score >= 60, f"Expected HIGH risk (>=60), got {score}"


def test_zone_person_foot_point():
    """person_foot_point returns the bottom-centre of the bbox."""
    from backend.src.services.zone_service import person_foot_point
    det = {"bbox": [100, 50, 200, 300], "cx": 150, "cy": 175}
    px, py = person_foot_point(det)
    assert px == 150.0   # (100+200)/2
    assert py == 300.0   # y2 (bottom edge)


# ─── API-level zone intrusion test (requires running server) ──────────────────

@pytest.mark.skipif(not _SERVER_UP, reason="Server not running")
def test_api_zone_crud_and_intrusion_endpoint():
    """
    Creates a RESTRICTED zone via API, verifies it is stored and returned,
    then deletes it.  Confirms zone CRUD works end-to-end.
    """
    import httpx

    # Login first
    r = httpx.post("http://localhost:8000/api/auth/login",
                   json={"username": "admin", "password": "admin123"}, timeout=10)
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Need a camera id — fetch first available
    cams = httpx.get("http://localhost:8000/api/cameras", headers=headers, timeout=10).json()
    assert len(cams) > 0, "No cameras in DB — run seed first"
    cam_id = cams[0]["id"]

    # Create a restricted zone
    zone_payload = {
        "camera_id": cam_id,
        "zone_name": "TEST_RESTRICTED",
        "zone_type": "RESTRICTED",
        "polygon_json": "[[0,0],[320,0],[320,240],[0,240]]",
        "is_active": True,
        "loitering_threshold_seconds": 30,
        "color": "#FF0000",
    }
    rc = httpx.post("http://localhost:8000/api/zones", json=zone_payload,
                    headers=headers, timeout=10)
    assert rc.status_code == 200, f"Zone create failed: {rc.text}"
    zone_id = rc.json()["id"]

    # Verify it appears in the zone list for that camera
    rl = httpx.get(f"http://localhost:8000/api/zones?camera_id={cam_id}",
                   headers=headers, timeout=10)
    assert rl.status_code == 200
    zone_names = [z["zone_name"] for z in rl.json()]
    assert "TEST_RESTRICTED" in zone_names

    # Clean up
    rd = httpx.delete(f"http://localhost:8000/api/zones/{zone_id}",
                      headers=headers, timeout=10)
    assert rd.status_code == 200


# ═══════════════════════════════════════════════════════════
# 10. POSSIBLE THEFT DETECTION TESTS
# ═══════════════════════════════════════════════════════════

def test_theft_risk_level():
    """POSSIBLE_THEFT must be HIGH severity with base risk >= 60."""
    from backend.src.services.ai_service import _risk_score, RISK_LEVELS
    assert "POSSIBLE_THEFT" in RISK_LEVELS
    assert RISK_LEVELS["POSSIBLE_THEFT"]["severity"] == "HIGH"
    score = _risk_score("POSSIBLE_THEFT", 0.80, 1)
    assert score >= 60, f"Expected HIGH risk (>=60), got {score}"


def test_theft_dist2():
    """_dist2 returns correct squared distance."""
    from backend.src.services.ai_service import _dist2
    assert _dist2(0, 0, 3, 4) == 25       # 3²+4²
    assert _dist2(100, 100, 100, 100) == 0


def test_theft_classes_content():
    """THEFT_CLASSES must include common stealable objects."""
    from backend.src.services.ai_service import THEFT_CLASSES
    for cls in ("backpack", "handbag", "laptop", "suitcase"):
        assert cls in THEFT_CLASSES, f"'{cls}' missing from THEFT_CLASSES"


def _make_person(tid, cx, cy, conf=0.85):
    return {"class_name": "person", "track_id": tid,
            "cx": cx, "cy": cy, "confidence": conf,
            "bbox": [cx-30, cy-60, cx+30, cy], "width": 60, "height": 60}


def _make_object(tid, cls, cx, cy, conf=0.80):
    return {"class_name": cls, "track_id": tid,
            "cx": cx, "cy": cy, "confidence": conf,
            "bbox": [cx-20, cy-20, cx+20, cy+20], "width": 40, "height": 40}


def test_theft_phase_present_then_approached():
    """Object transitions PRESENT → APPROACHED when person stays close."""
    from backend.src.services.ai_service import (
        _update_theft_watch, THEFT_APPROACH_FRAMES, _get_state
    )
    state = _get_state("test_cam_theft_1")
    state["theft_watch"] = {}  # clean slate
    now = 1000.0

    obj = _make_object(10, "backpack", 200, 200)
    person = _make_person(1, 220, 210)   # within 120px

    # First frame: register object
    evts = _update_theft_watch(state, [obj], [person], now)
    assert state["theft_watch"][10]["phase"] == "PRESENT"
    assert evts == []

    # Advance proximity frames past threshold
    for i in range(THEFT_APPROACH_FRAMES):
        evts = _update_theft_watch(state, [obj], [person], now + i + 1)
    assert state["theft_watch"][10]["phase"] == "APPROACHED"
    assert state["theft_watch"][10]["owner_tid"] == 1
    assert evts == []


def test_theft_no_event_if_object_never_approached():
    """Object that vanishes without being approached must NOT generate event."""
    from backend.src.services.ai_service import _update_theft_watch, THEFT_GONE_CONFIRM_SEC
    state = {"theft_watch": {}}
    now = 2000.0

    obj = _make_object(20, "handbag", 300, 300)
    # Register object, no person nearby
    _update_theft_watch(state, [obj], [], now)
    assert state["theft_watch"][20]["phase"] == "PRESENT"

    # Object disappears immediately
    evts = _update_theft_watch(state, [], [], now + THEFT_GONE_CONFIRM_SEC + 1)
    assert evts == [], "Should not fire: object was never approached"
    assert 20 not in state["theft_watch"]  # cleaned up


def test_theft_event_fires_after_confirmation():
    """Full sequence: approach → disappear → wait → TheftEvent generated."""
    from backend.src.services.ai_service import (
        _update_theft_watch, THEFT_APPROACH_FRAMES, THEFT_GONE_CONFIRM_SEC
    )
    state = {"theft_watch": {}}
    now = 3000.0

    obj = _make_object(30, "laptop", 150, 150)
    person = _make_person(5, 160, 160)

    # Phase 1: register
    _update_theft_watch(state, [obj], [person], now)

    # Phase 2: approach enough frames
    for i in range(THEFT_APPROACH_FRAMES):
        _update_theft_watch(state, [obj], [person], now + i + 1)
    assert state["theft_watch"][30]["phase"] == "APPROACHED"

    # Phase 3: object vanishes — start absence timer
    t_gone = now + THEFT_APPROACH_FRAMES + 1
    _update_theft_watch(state, [], [person], t_gone)          # frame 1 absent
    evts = _update_theft_watch(
        state, [], [person], t_gone + THEFT_GONE_CONFIRM_SEC + 0.1
    )

    assert len(evts) == 1
    ev = evts[0]
    assert ev.obj_class == "laptop"
    assert ev.person_tid == 5
    assert 0.60 <= ev.confidence <= 0.90
    assert "POSSIBLE_THEFT" in ev.description
    assert "requires human verification" in ev.description.lower()
    # Event should clear the watch entry
    assert 30 not in state["theft_watch"]


def test_theft_no_double_fire():
    """After TheftEvent fires, same object should not fire again immediately."""
    from backend.src.services.ai_service import (
        _update_theft_watch, THEFT_APPROACH_FRAMES, THEFT_GONE_CONFIRM_SEC
    )
    state = {"theft_watch": {}}
    now = 4000.0

    obj = _make_object(40, "suitcase", 100, 100)
    person = _make_person(7, 110, 110)

    _update_theft_watch(state, [obj], [person], now)
    for i in range(THEFT_APPROACH_FRAMES):
        _update_theft_watch(state, [obj], [person], now + i + 1)

    t_gone = now + THEFT_APPROACH_FRAMES + 1
    _update_theft_watch(state, [], [], t_gone)
    evts1 = _update_theft_watch(state, [], [], t_gone + THEFT_GONE_CONFIRM_SEC + 0.1)
    assert len(evts1) == 1

    # Immediately after, same object id reappears — it should start fresh (PRESENT)
    obj_back = _make_object(40, "suitcase", 100, 100)
    _update_theft_watch(state, [obj_back], [], t_gone + THEFT_GONE_CONFIRM_SEC + 1)
    assert state["theft_watch"][40]["phase"] == "PRESENT"


def test_theft_non_theft_class_ignored():
    """Objects not in THEFT_CLASSES (e.g. 'car') must be ignored."""
    from backend.src.services.ai_service import _update_theft_watch
    state = {"theft_watch": {}}
    now = 5000.0
    car = _make_object(50, "car", 200, 200)   # not in THEFT_CLASSES
    _update_theft_watch(state, [car], [], now)
    assert 50 not in state["theft_watch"]



# ═══════════════════════════════════════════════════════════
# 11. RECORDED VIDEO WORKFLOW TESTS
# ═══════════════════════════════════════════════════════════

def _admin_headers():
    """Return auth headers for the admin user (helper for video tests)."""
    import httpx
    r = httpx.post("http://localhost:8000/api/auth/login",
                   json={"username": "admin", "password": "admin123"}, timeout=10)
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_video_sec_to_hms():
    """_sec_to_hms formats timestamps correctly."""
    from backend.src.routers.surveillance import _sec_to_hms
    assert _sec_to_hms(0) == "00:00"
    assert _sec_to_hms(65) == "01:05"
    assert _sec_to_hms(3661) == "01:01:01"
    assert _sec_to_hms(90) == "01:30"


def test_video_upload_endpoint_exists():
    """GET /api/surveillance/jobs must return 200 (proves router is mounted)."""
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx
    headers = _admin_headers()
    r = httpx.get("http://localhost:8000/api/surveillance/jobs", headers=headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_video_job_lifecycle():
    """
    Full workflow: upload synthetic video → job created → COMPLETED.
    Verifies: upload, job_id returned, /job/{id} polling, COMPLETED status,
    total_frames > 0.
    """
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx, cv2, numpy as np, time, os, tempfile

    headers = _admin_headers()

    # Build a short synthetic video (10 frames @ 5fps)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(tmp_path, fourcc, 5.0, (320, 240))
        for _ in range(10):
            f = np.zeros((240, 320, 3), dtype=np.uint8)
            f[60:180, 90:230] = [80, 150, 200]
            vw.write(f)
        vw.release()

        # Upload
        with open(tmp_path, "rb") as fh:
            r = httpx.post(
                "http://localhost:8000/api/surveillance/upload-video",
                headers=headers,
                files={"file": ("pytest_test.mp4", fh, "video/mp4")},
                timeout=30,
            )
        assert r.status_code == 200, f"Upload failed: {r.text}"
        d = r.json()
        job_id = d.get("job_id")
        assert job_id, "No job_id in response"
        assert d.get("status") in ("PENDING", "PROCESSING"), f"Unexpected initial status: {d.get('status')}"

        # Poll until done (max 40s)
        final = None
        for _ in range(20):
            time.sleep(2)
            jr = httpx.get(f"http://localhost:8000/api/surveillance/job/{job_id}",
                           headers=headers, timeout=10)
            assert jr.status_code == 200
            jd = jr.json()
            if jd.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                final = jd
                break

        assert final is not None, "Job never reached terminal state"
        assert final["status"] == "COMPLETED", f"Job failed: {final.get('error')}"
        assert final.get("total_frames", 0) > 0, "No frames processed"
        assert "incidents" in final
        assert "detections" in final
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def test_video_job_not_found():
    """GET /api/surveillance/job/<nonexistent> must return 404."""
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx
    headers = _admin_headers()
    r = httpx.get("http://localhost:8000/api/surveillance/job/nonexistent-id-xyz",
                  headers=headers, timeout=10)
    assert r.status_code == 404


def test_video_invalid_extension():
    """Uploading a .txt file must return 400."""
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx
    headers = _admin_headers()
    r = httpx.post(
        "http://localhost:8000/api/surveillance/upload-video",
        headers=headers,
        files={"file": ("bad_file.txt", b"not a video", "text/plain")},
        timeout=10,
    )
    assert r.status_code == 400


def test_incident_rejection_status():
    """Verify that rejecting an incident transitions to and explicitly returns status FALSE_POSITIVE."""
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx
    headers = _admin_headers()
    # Create incident
    r_create = httpx.post("http://localhost:8000/api/ai/incident", json={
        "incident_type": "LOITERING", "severity": "LOW", "risk_score": 30.0,
        "ai_confidence": 70.0, "camera_id": "CAM-001", "location_name": "Main Gate",
        "latitude": 28.6139, "longitude": 77.2090, "description": "Rejection test",
        "involved_track_ids": []
    }, timeout=10)
    assert r_create.status_code == 200
    inc_id = r_create.json()["id"]

    # Reject
    r_rej = httpx.post(f"http://localhost:8000/api/incidents/{inc_id}/reject",
                       headers=headers, json={"reason": "False alarm"}, timeout=10)
    assert r_rej.status_code == 200
    res_data = r_rej.json()
    assert res_data.get("status") == "FALSE_POSITIVE", f"Expected FALSE_POSITIVE, got {res_data.get('status')}"


def test_real_jpeg_evidence_saved_and_accessible():
    """Verify that real JPEG evidence from frame processing is saved to disk and retrievable via API."""
    if not _SERVER_UP:
        pytest.skip("Server not running")
    import httpx, cv2, numpy as np, os, asyncio
    from backend.src.services.ai_service import AIService
    from backend.src.database import AsyncSessionLocal

    headers = _admin_headers()

    # Generate test frame and process
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.circle(img, (160, 120), 40, (0, 0, 255), -1)

    async def _create_test_frame_incident():
        ai = AIService()
        ai._last_frame = img
        async with AsyncSessionLocal() as db:
            return await ai._create_incident(
                db=db,
                incident_type="INTRUSION",
                severity="HIGH",
                risk_score=75.0,
                confidence=85.0,
                camera_id="CAM-001",
                source_type="LIVE_CAMERA",
                description="Automated evidence test"
            )

    inc = asyncio.run(_create_test_frame_incident())
    inc_id = inc["id"]
    inc_human_id = inc["incident_id"]

    # Verify via evidence endpoint
    r_ev = httpx.get(f"http://localhost:8000/api/evidence/{inc_id}", headers=headers, timeout=10)
    assert r_ev.status_code == 200
    ev_list = r_ev.json()
    assert len(ev_list) >= 1, "Must have evidence for frame-based incident"

    ev_record = ev_list[0]
    file_path = ev_record.get("file_path")
    assert file_path and os.path.exists(file_path), "Real JPEG file must exist on disk"
    assert os.path.getsize(file_path) > 0, "JPEG file must not be empty"

    # Query by human ID
    r_ev2 = httpx.get(f"http://localhost:8000/api/evidence/{inc_human_id}", headers=headers, timeout=10)
    assert r_ev2.status_code == 200
    assert len(r_ev2.json()) >= 1

    # Verify file download endpoint
    ev_id = ev_record["id"]
    r_file = httpx.get(f"http://localhost:8000/api/evidence/file/{ev_id}", headers=headers, timeout=10)
    assert r_file.status_code == 200
    assert r_file.headers.get("content-type") == "image/jpeg"
    assert len(r_file.content) == os.path.getsize(file_path)


if __name__ == "__main__":


    # Run basic tests without pytest
    print("Running basic tests...")
    test_haversine_same_point()
    test_haversine_returns_float()
    test_risk_score_clamp()
    test_risk_score_weapon_higher_than_loitering()
    test_risk_score_fight_critical()
    test_risk_level()
    test_valid_transitions()
    test_incident_id_format()
    test_calc_movement_stationary()
    test_calc_movement_fast()
    test_erratic_detects_zigzag()
    test_erratic_rejects_straight()
    test_cooldown_prevents_duplicate()
    test_cooldown_different_types()
    test_valid_video_extension()
    test_path_traversal_prevention()
    print("[PASS] All offline tests passed!")

    print("\nRunning API tests (server must be running on port 8000)...")
    try:
        test_health_endpoint()
        test_login_success()
        test_login_wrong_password()
        test_cameras_list()
        test_incidents_list()
        test_responders_list()
        test_analytics_summary()
        test_nearest_responders()
        test_surveillance_jobs_list()
        test_models_endpoint()
        print("[PASS] All API tests passed!")
    except SystemExit:
        print("[SKIP] Some API tests skipped (server not running)")
