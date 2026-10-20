"""Quick probe: test the video upload endpoint end-to-end."""
import httpx, json, os, cv2, numpy as np, time, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

# Create a 4-second test video (20 frames @ 5fps)
path = os.path.join("data", "uploads", "_probe_step6.mp4")
os.makedirs(os.path.dirname(path), exist_ok=True)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
vw = cv2.VideoWriter(path, fourcc, 5.0, (320, 240))
for i in range(20):
    f = np.zeros((240, 320, 3), dtype=np.uint8)
    f[60:180, 90:230] = [80, 150, 200]   # rough person-shaped rectangle
    vw.write(f)
vw.release()
print(f"[OK] Test video written: {path} ({os.path.getsize(path)} bytes)")

# Auth
tok = httpx.post("http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin123"}, timeout=10).json()["access_token"]
headers = {"Authorization": f"Bearer {tok}"}

# Upload
with open(path, "rb") as fh:
    r = httpx.post(
        "http://localhost:8000/api/surveillance/upload-video",
        headers=headers,
        files={"file": ("probe_step6.mp4", fh, "video/mp4")},
        timeout=30,
    )
print(f"[UPLOAD] HTTP {r.status_code}")
d = r.json()
print(json.dumps(d, indent=2))
job_id = d.get("job_id")
if not job_id:
    print("[FAIL] No job_id returned")
    sys.exit(1)

# Poll
print("\n[POLLING] ...")
final = None
for i in range(40):
    time.sleep(2)
    jr = httpx.get(f"http://localhost:8000/api/surveillance/job/{job_id}",
                   headers=headers, timeout=10)
    jd = jr.json()
    status = jd.get("status", "?")
    prog = jd.get("progress", 0)
    msg = jd.get("message", "")[:70]
    print(f"  [{i*2:3d}s] {status:12s} {prog:5.1f}%  {msg}")
    if status in ("COMPLETED", "FAILED", "CANCELLED"):
        final = jd
        break

os.remove(path)

if not final:
    print("[FAIL] Job never completed")
    sys.exit(1)

print("\n[RESULT]")
print(f"  status         : {final.get('status')}")
print(f"  total_frames   : {final.get('total_frames', '?')}")
print(f"  incidents      : {len(final.get('incidents', []))}")
print(f"  detections kept: {len(final.get('detections', []))}")
print(f"  error          : {final.get('error')}")

if final.get("status") == "COMPLETED":
    print("[PASS] Video analysis workflow works correctly")
    sys.exit(0)
else:
    print("[FAIL] Job did not complete successfully")
    sys.exit(1)
