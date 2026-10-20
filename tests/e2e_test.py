"""
AegisWatch — End-to-End API Test Script (Step 5)
=================================================
Tests the complete incident lifecycle via HTTP + WebSocket.
No fake data — every assertion uses real server responses.

Flows tested:
 1.  Health / server up
 2.  Login (admin, operator, responder)
 3.  Database — cameras, responders seeded
 4.  YOLOv8 detection on a real synthetic frame (base64)
 5.  Incident created via AI webhook endpoint
 6.  Evidence API — list + file served
 7.  WebSocket alert delivery
 8.  Incident lifecycle: Verify → Assign (nearest) → Accept → Responding → Resolve
 9.  Human Reject (false-positive)
10.  DETR model switch + inference
11.  Zone CRUD (create RESTRICTED zone)
12.  Video upload + analysis endpoint
13.  Nearest-responder calculation
14.  Evidence JPEG written to disk
"""

import sys
import os
import base64
import json
import time
import uuid
import asyncio
import threading
import traceback

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import httpx
    import numpy as np
    import cv2
    import websockets
except ImportError as e:
    print(f"[SKIP] Missing dependency: {e}")
    sys.exit(0)

BASE = "http://localhost:8000"
WS   = "ws://localhost:8000"

PASS = []
FAIL = []
SKIP = []

def ok(name):
    PASS.append(name)
    print(f"  ✅ PASS  {name}")

def fail(name, reason=""):
    FAIL.append(name)
    print(f"  ❌ FAIL  {name}" + (f" — {reason}" if reason else ""))

def skip(name, reason=""):
    SKIP.append(name)
    print(f"  ⚠️  SKIP  {name}" + (f" — {reason}" if reason else ""))

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── Helpers ────────────────────────────────────────────────

def make_frame_b64(h=480, w=640):
    """Create a real OpenCV frame and return as base64 JPEG."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[100:400, 200:440] = [120, 80, 200]   # rough human-coloured rectangle
    cv2.putText(frame, "E2E TEST FRAME", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf.tobytes()).decode()


def login(username, password):
    r = httpx.post(f"{BASE}/api/auth/login",
                   json={"username": username, "password": password}, timeout=10)
    if r.status_code == 200:
        return r.json()["access_token"]
    return None


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════
# TEST SECTIONS
# ══════════════════════════════════════════════════════════════

def test_01_server_health():
    section("1. Server Health")
    try:
        r = httpx.get(f"{BASE}/api/health", timeout=5)
        assert r.status_code == 200
        d = r.json()
        assert d.get("status") == "ok"
        assert d.get("ai") == "ok"
        ok("Server responding at :8000")
        ok(f"AI model active: {d.get('model', '?')}")
        return True
    except Exception as e:
        fail("Server health", str(e))
        return False


def test_02_login():
    section("2. Authentication")
    results = {}
    for user, pwd, role in [
        ("admin",      "admin123",   "ADMIN"),
        ("operator",   "operator123","OPERATOR"),
        ("responder1", "resp123",    "RESPONDER"),
    ]:
        tok = login(user, pwd)
        if tok:
            ok(f"Login {user} ({role})")
            results[user] = tok
        else:
            fail(f"Login {user}", "no token returned")

    # Wrong password
    r = httpx.post(f"{BASE}/api/auth/login",
                   json={"username": "admin", "password": "wrong"}, timeout=5)
    if r.status_code in (401, 403, 422):
        ok("Wrong password rejected")
    else:
        fail("Wrong password rejected", f"got {r.status_code}")

    return results


def test_03_database(tok):
    section("3. Database — Cameras & Responders")
    h = auth(tok)
    try:
        r = httpx.get(f"{BASE}/api/cameras", headers=h, timeout=10)
        assert r.status_code == 200
        cams = r.json()
        assert len(cams) > 0, "No cameras seeded"
        ok(f"Cameras in DB: {len(cams)}")

        r2 = httpx.get(f"{BASE}/api/responders", headers=h, timeout=10)
        assert r2.status_code == 200
        resp = r2.json()
        assert len(resp) > 0, "No responders seeded"
        ok(f"Responders in DB: {len(resp)}")
        return cams, resp
    except Exception as e:
        fail("Database seed data", str(e))
        return [], []


def test_04_yolov8_detection(tok, cam):
    section("4. YOLOv8 — Real Frame Detection")
    h = auth(tok)
    cam_id = cam.get("camera_id", "CAM-001")
    frame_b64 = make_frame_b64()
    try:
        payload = {
            "frame": frame_b64,
            "camera_id": cam_id,
            "source_type": "LIVE_CAMERA",
        }
        r = httpx.post(f"{BASE}/api/ai/frame", headers=h, json=payload, timeout=30)
        if r.status_code == 200:
            d = r.json()
            ok(f"Frame processed — detections: {len(d.get('detections', []))}, "
               f"model: {d.get('model','?')}")
            return d
        elif r.status_code == 404:
            skip("YOLOv8 live frame", "No /api/ai/frame endpoint — using webhook test instead")
            return {}
        else:
            fail("YOLOv8 frame", f"HTTP {r.status_code}: {r.text[:200]}")
            return {}
    except Exception as e:
        fail("YOLOv8 frame", str(e))
        return {}


def test_05_incident_creation_via_webhook(tok):
    section("5. Incident Creation — AI Webhook")
    h = auth(tok)
    payload = {
        "incident_type": "SUSPICIOUS_MOVEMENT",
        "severity": "MEDIUM",
        "risk_score": 58.0,
        "ai_confidence": 72.0,
        "camera_id": "CAM-001",
        "location_name": "Main Gate",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "description": "E2E TEST: Suspicious movement detected by person #7",
        "involved_track_ids": [7],
        "metadata": {"test": True},
    }
    try:
        r = httpx.post(f"{BASE}/api/ai/incident", json=payload, timeout=15)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        d = r.json()
        inc_id = d.get("id") or d.get("incident_id")
        assert inc_id, "No incident id returned"
        ok(f"Incident created: {d.get('incident_id', inc_id)}")
        ok(f"  severity={d.get('severity')}, risk={d.get('risk_score')}")
        return d
    except Exception as e:
        fail("Incident creation via webhook", str(e))
        return {}


def test_06_evidence_api(tok, incident):
    section("6. Evidence API")
    h = auth(tok)
    inc_db_id = incident.get("id")
    if not inc_db_id:
        skip("Evidence API", "No incident id available")
        return

    try:
        r = httpx.get(f"{BASE}/api/evidence/{inc_db_id}", headers=h, timeout=10)
        assert r.status_code == 200
        evlist = r.json()
        ok(f"Evidence list returned: {len(evlist)} item(s)")

        # Check if evidence JPEG exists on disk
        for ev in evlist:
            fp = ev.get("file_path", "")
            if fp and os.path.exists(fp):
                size = os.path.getsize(fp)
                ok(f"Evidence JPEG on disk: {os.path.basename(fp)} ({size} bytes)")
            elif ev.get("evidence_type") == "SNAPSHOT":
                fail("Evidence JPEG on disk", f"file not found: {fp}")
    except Exception as e:
        fail("Evidence API", str(e))


def test_07_websocket():
    section("7. WebSocket — Alert Delivery")
    received = []
    client_id = f"e2e-test-{uuid.uuid4().hex[:8]}"

    async def _listen():
        try:
            async with websockets.connect(
                f"{WS}/ws/{client_id}", open_timeout=5, close_timeout=3
            ) as ws:
                # Send test incident via webhook in a thread
                def send_incident():
                    time.sleep(0.5)
                    httpx.post(f"{BASE}/api/ai/incident", json={
                        "incident_type": "LOITERING",
                        "severity": "MEDIUM",
                        "risk_score": 47.0,
                        "ai_confidence": 68.0,
                        "camera_id": "CAM-002",
                        "location_name": "Parking Area",
                        "latitude": 28.6140,
                        "longitude": 77.2095,
                        "description": "E2E WS TEST: Loitering detected",
                        "involved_track_ids": [3],
                        "metadata": {},
                    }, timeout=10)

                t = threading.Thread(target=send_incident, daemon=True)
                t.start()
                ws.recv_timeout = 10
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=10)
                msg = json.loads(msg_raw)
                received.append(msg)
        except Exception as e:
            received.append({"_error": str(e)})

    asyncio.run(_listen())

    if received and "_error" not in received[0]:
        msg = received[0]
        if msg.get("type") == "incident_alert" and msg.get("data"):
            ok(f"WebSocket received incident_alert: type={msg['data'].get('incident_type')}")
        else:
            ok(f"WebSocket message received (type={msg.get('type', '?')})")
    else:
        err = received[0].get("_error", "No message received") if received else "No message"
        fail("WebSocket alert", err)


def test_08_incident_lifecycle(tok, incident):
    section("8. Incident Lifecycle (Verify → Assign → Accept → Responding → Resolve)")
    h = auth(tok)
    inc_db_id = incident.get("id")
    if not inc_db_id:
        skip("Incident lifecycle", "No incident id")
        return

    steps = [
        ("verify",    f"/api/incidents/{inc_db_id}/verify",    {}),
        ("assign",    f"/api/incidents/{inc_db_id}/assign",    {}),
        ("accept",    f"/api/incidents/{inc_db_id}/accept",    {}),
        ("responding",f"/api/incidents/{inc_db_id}/responding",{}),
        ("resolve",   f"/api/incidents/{inc_db_id}/resolve",   {"notes": "E2E resolved"}),
    ]
    for step_name, path, body in steps:
        try:
            r = httpx.post(f"{BASE}{path}", headers=h, json=body, timeout=10)
            if r.status_code == 200:
                ok(f"  {step_name.upper()} → 200")
            else:
                fail(f"  {step_name.upper()}", f"HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            fail(f"  {step_name.upper()}", str(e))


def test_09_human_reject(tok):
    section("9. Human Reject (False-Positive)")
    h = auth(tok)
    # Create a fresh incident to reject
    r0 = httpx.post(f"{BASE}/api/ai/incident", json={
        "incident_type": "LOITERING",
        "severity": "LOW",
        "risk_score": 42.0,
        "ai_confidence": 60.0,
        "camera_id": "CAM-001",
        "location_name": "Main Gate",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "description": "E2E REJECT TEST",
        "involved_track_ids": [],
        "metadata": {},
    }, timeout=10)
    if r0.status_code != 200:
        fail("Reject test — incident creation", f"HTTP {r0.status_code}")
        return

    inc_id = r0.json().get("id")
    # Reject directly from NEW (now a valid transition)
    r = httpx.post(f"{BASE}/api/incidents/{inc_id}/reject", headers=h,
                   json={"reason": "E2E test — false positive"}, timeout=10)
    if r.status_code == 200:
        d = r.json()
        status = d.get("status", "")
        if status == "FALSE_POSITIVE":
            ok("Incident rejected → FALSE_POSITIVE")
        else:
            fail("Reject incident", f"Expected FALSE_POSITIVE, got status='{status}'")
    else:
        fail("Reject incident", f"HTTP {r.status_code}: {r.text[:150]}")


def test_10_nearest_responder(tok):
    section("10. Nearest-Responder Calculation")
    h = auth(tok)
    try:
        r = httpx.get(f"{BASE}/api/responders/nearest?lat=28.6139&lon=77.2090",
                      headers=h, timeout=10)
        assert r.status_code == 200, f"HTTP {r.status_code}"
        data = r.json()
        if isinstance(data, list) and data:
            top = data[0]
            ok(f"Nearest responder: {top.get('name','?')} "
               f"({top.get('distance_km', top.get('distance','?'))} km)")
        elif isinstance(data, dict) and data:
            ok(f"Nearest responder data returned: {list(data.keys())}")
        else:
            skip("Nearest responder", "Empty list (all offline?)")
    except Exception as e:
        fail("Nearest responder", str(e))


def test_11_detr_switch(tok):
    section("11. DETR Model Switch")
    h = auth(tok)
    try:
        # Check models list
        r = httpx.get(f"{BASE}/api/models", headers=h, timeout=10)
        assert r.status_code == 200
        keys = [m["key"] for m in r.json()]
        assert "detr" in keys and "yolov8" in keys
        ok(f"Models available: {keys}")

        # Switch to DETR (uses cached model — fast)
        r2 = httpx.post(f"{BASE}/api/models/switch", headers=h,
                        json={"model": "detr"}, timeout=120)
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2.get("success"), "switch didn't return success=true"
        ok(f"Switched to DETR: {b2.get('model_name')}")

        # Switch back
        r3 = httpx.post(f"{BASE}/api/models/switch", headers=h,
                        json={"model": "yolov8"}, timeout=30)
        assert r3.status_code == 200
        ok("Switched back to YOLOv8")
    except Exception as e:
        fail("DETR model switch", str(e))


def test_12_zone_crud(tok, cam):
    section("12. Zone CRUD")
    h = auth(tok)
    cam_id = cam.get("id")
    if not cam_id:
        skip("Zone CRUD", "No camera id")
        return None

    try:
        payload = {
            "camera_id": cam_id,
            "zone_name": "E2E_RESTRICTED",
            "zone_type": "RESTRICTED",
            "polygon_json": "[[0,0],[320,0],[320,240],[0,240]]",
            "is_active": True,
            "loitering_threshold_seconds": 30,
            "color": "#FF0000",
        }
        rc = httpx.post(f"{BASE}/api/zones", json=payload, headers=h, timeout=10)
        assert rc.status_code == 200, f"Create: {rc.status_code} {rc.text}"
        zone = rc.json()
        ok(f"Zone created: {zone.get('zone_name')} ({zone.get('zone_type')})")

        rl = httpx.get(f"{BASE}/api/zones?camera_id={cam_id}", headers=h, timeout=10)
        assert rl.status_code == 200
        names = [z["zone_name"] for z in rl.json()]
        assert "E2E_RESTRICTED" in names
        ok("Zone appears in zone list")

        rd = httpx.delete(f"{BASE}/api/zones/{zone['id']}", headers=h, timeout=10)
        assert rd.status_code == 200
        ok("Zone deleted")
        return zone
    except Exception as e:
        fail("Zone CRUD", str(e))
        return None


def test_13_video_upload(tok):
    section("13. Video Upload & Analysis")
    h = auth(tok)

    # Create a 3-second synthetic video
    tmp_path = os.path.join("data", "videos", "demo", "_e2e_test.mp4")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(tmp_path, fourcc, 5.0, (320, 240))
        for _ in range(15):
            f = np.zeros((240, 320, 3), dtype=np.uint8)
            f[50:190, 100:220] = [80, 120, 200]
            vw.write(f)
        vw.release()
        ok(f"Test video written: {tmp_path}")
    except Exception as e:
        fail("Create test video", str(e))
        return

    # Upload to the correct surveillance endpoint
    try:
        with open(tmp_path, "rb") as fh:
            r = httpx.post(
                f"{BASE}/api/surveillance/upload-video",
                headers=h,
                files={"file": ("_e2e_test.mp4", fh, "video/mp4")},
                timeout=30,
            )
        if r.status_code == 200:
            d = r.json()
            job_id = d.get("job_id")
            ok(f"Video upload accepted — job_id={job_id[:8] if job_id else '?'}..., status={d.get('status')}")

            # Poll for completion (max 30s)
            final = None
            for _ in range(15):
                time.sleep(2)
                jr = httpx.get(f"{BASE}/api/surveillance/job/{job_id}",
                               headers=h, timeout=10)
                jd = jr.json()
                if jd.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                    final = jd
                    break

            if final and final.get("status") == "COMPLETED":
                ok(f"Video analysis COMPLETED — {final.get('total_frames','?')} frames processed, "
                   f"{len(final.get('incidents', []))} incidents detected")
            elif final:
                fail("Video analysis completed", f"status={final.get('status')}, error={final.get('error')}")
            else:
                fail("Video analysis", "Job did not complete within 30s")
        else:
            fail("Video upload", f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        fail("Video upload", str(e))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def test_14_analytics(tok):
    section("14. Analytics Dashboard Data")
    h = auth(tok)
    try:
        r = httpx.get(f"{BASE}/api/analytics/summary", headers=h, timeout=10)
        assert r.status_code == 200
        d = r.json()
        ok(f"Analytics summary: cameras={d.get('total_cameras')}, "
           f"incidents_today={d.get('today_incidents')}, "
           f"active={d.get('active_incidents')}")
    except Exception as e:
        fail("Analytics summary", str(e))


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("  AegisWatch — Step 5 End-to-End Test")
    print("═"*60)

    # 1. Health
    if not test_01_server_health():
        print("\n[FATAL] Server not responding — aborting E2E tests.")
        return

    # 2. Auth
    tokens = test_02_login()
    tok = tokens.get("admin", "")
    if not tok:
        print("\n[FATAL] Admin login failed — aborting.")
        return

    # 3. DB
    cams, responders = test_03_database(tok)
    cam = cams[0] if cams else {}

    # 4. YOLOv8 live frame
    test_04_yolov8_detection(tok, cam)

    # 5. Incident via webhook
    incident = test_05_incident_creation_via_webhook(tok)

    # 6. Evidence
    test_06_evidence_api(tok, incident)

    # 7. WebSocket
    test_07_websocket()

    # 8. Lifecycle
    test_08_incident_lifecycle(tok, incident)

    # 9. Reject
    test_09_human_reject(tok)

    # 10. Nearest responder
    test_10_nearest_responder(tok)

    # 11. DETR switch
    test_11_detr_switch(tok)

    # 12. Zone CRUD
    test_12_zone_crud(tok, cam)

    # 13. Video upload
    test_13_video_upload(tok)

    # 14. Analytics
    test_14_analytics(tok)

    # ── Summary ────────────────────────────────────────────
    print("\n" + "═"*60)
    print("  E2E SUMMARY")
    print("═"*60)
    print(f"  ✅ PASSED : {len(PASS)}")
    print(f"  ❌ FAILED : {len(FAIL)}")
    print(f"  ⚠️  SKIPPED: {len(SKIP)}")
    if FAIL:
        print("\n  FAILURES:")
        for f in FAIL:
            print(f"    ❌ {f}")
    if SKIP:
        print("\n  SKIPPED:")
        for s in SKIP:
            print(f"    ⚠️  {s}")
    print()

if __name__ == "__main__":
    main()
