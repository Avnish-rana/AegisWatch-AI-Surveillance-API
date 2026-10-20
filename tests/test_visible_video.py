import httpx, json, base64, cv2, numpy as np, time, sys

BASE = 'http://localhost:8000'

# 1. Login
tok = httpx.post(f'{BASE}/api/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=10).json()['access_token']
h = {'Authorization': f'Bearer {tok}'}

# 2. Upload one of our demo videos (e.g. data/videos/demo/normal.mp4)
video_path = 'data/videos/demo/normal.mp4'
with open(video_path, 'rb') as f:
    r = httpx.post(f'{BASE}/api/surveillance/upload-video', headers=h, files={'file': ('normal.mp4', f, 'video/mp4')}, timeout=30)
assert r.status_code == 200, f'Upload failed: {r.text}'
job = r.json()
job_id = job['job_id']
print(f'Uploaded: job_id={job_id}, status={job.get("status")}')

# 3. Test pause and resume endpoints
p_resp = httpx.post(f'{BASE}/api/surveillance/job/{job_id}/pause', headers=h, timeout=10)
assert p_resp.status_code == 200 and p_resp.json().get('paused') == True, f'Pause failed: {p_resp.text}'
print('Pause endpoint verified: paused = True')

r_resp = httpx.post(f'{BASE}/api/surveillance/job/{job_id}/resume', headers=h, timeout=10)
assert r_resp.status_code == 200 and r_resp.json().get('paused') == False, f'Resume failed: {r_resp.text}'
print('Resume endpoint verified: paused = False')

# 4. Connect to SSE stream and read events
print('Connecting to SSE stream...')
frames_received = 0
final_event = None

with httpx.stream('GET', f'{BASE}/api/surveillance/job/{job_id}/stream', headers=h, timeout=40) as response:
    assert response.status_code == 200, f'Stream failed: {response.status_code}'
    for line in response.iter_lines():
        if line.startswith('data: '):
            data_str = line[6:].strip()
            data = json.loads(data_str)
            msg_type = data.get('type')
            
            if msg_type in ('frame', 'state'):
                if data.get('frame_b64'):
                    frames_received += 1
                    # Verify decodable JPEG
                    img_bytes = base64.b64decode(data['frame_b64'])
                    arr = np.frombuffer(img_bytes, dtype=np.uint8)
                    frame_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    assert frame_img is not None, 'Frame must be a valid decoded JPEG!'
                    if frames_received <= 3 or frames_received % 10 == 0:
                        print(f'  [Frame #{data.get("frame_num")}] progress={data.get("progress")}% '
                              f'ts={data.get("timestamp_str")} fps={data.get("fps")} '
                              f'detections={len(data.get("detections", []))} '
                              f'shape={frame_img.shape}')
            elif msg_type == 'finished':
                print(f'Finished event received: status={data.get("status")}, total_frames={data.get("total_frames")}')
                final_event = data
                break

print(f'\nTotal frames streamed and verified: {frames_received}')
assert frames_received > 0, 'Must have received streamed frames!'
assert final_event is not None and final_event.get('status') == 'COMPLETED', 'Final event must be COMPLETED!'

# 5. Check REST endpoint status
job_final = httpx.get(f'{BASE}/api/surveillance/job/{job_id}', headers=h, timeout=10).json()
assert job_final['status'] == 'COMPLETED'
assert job_final['total_frames'] > 0
print(f'REST job status confirmed: {job_final["status"]} with {job_final["total_frames"]} frames.')

print('\nALL VISIBLE VIDEO STREAMING & CONTROL TESTS PASSED!')
