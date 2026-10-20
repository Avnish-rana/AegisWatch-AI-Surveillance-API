import httpx, json, base64, cv2, numpy as np

BASE = 'http://localhost:8000'
tok = httpx.post(f'{BASE}/api/auth/login', json={'username': 'admin', 'password': 'admin123'}, timeout=10).json()['access_token']
h = {'Authorization': f'Bearer {tok}'}

with open('data/videos/demo/person_demo.mp4', 'rb') as f:
    r = httpx.post(f'{BASE}/api/surveillance/upload-video', headers=h, files={'file': ('person_demo.mp4', f, 'video/mp4')}, timeout=30.0)
assert r.status_code == 200
job_id = r.json()['job_id']
print('Uploaded person_demo.mp4, job_id:', job_id)

detections_found = []
frames_streamed = 0

with httpx.stream('GET', f'{BASE}/api/surveillance/job/{job_id}/stream', headers=h, timeout=40.0) as s:
    for line in s.iter_lines():
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if data.get('type') in ('frame', 'state'):
                if data.get('frame_b64'):
                    frames_streamed += 1
                dets = data.get('detections', [])
                if dets:
                    detections_found.extend(dets)
                    for d in dets:
                        print(f'  [Frame #{data.get("frame_num")}] Found {d.get("class_name")} #{d.get("track_id")} '
                              f'conf={round(d.get("confidence", 0)*100, 1)}% bbox={d.get("bbox")}')
            elif data.get('type') == 'finished':
                print('Stream finished:', data.get('status'))
                break

print(f'\nTotal frames streamed: {frames_streamed}')
print(f'Total detections captured: {len(detections_found)}')

assert frames_streamed > 0, 'Must have received streamed frames'
assert len(detections_found) > 0, 'Must have captured real AI detections with bounding boxes!'
sample_det = detections_found[0]
assert 'class_name' in sample_det and sample_det['class_name'] == 'person'
assert 'confidence' in sample_det and sample_det['confidence'] > 0.5
assert 'bbox' in sample_det and len(sample_det['bbox']) == 4
assert 'track_id' in sample_det

print('\nCONFIRMED: Streaming delivers real AI bounding boxes with tracking IDs and confidence scores!')
