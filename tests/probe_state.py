import httpx, json, sys
BASE = 'http://localhost:8000'

try:
    h = httpx.get(f'{BASE}/api/health', timeout=5).json()
    print('SERVER:', h.get('status'), '| AI:', h.get('ai'), '| Model:', h.get('model_name'), '| DB:', h.get('db'))
except Exception as e:
    print('SERVER DOWN:', e)
    sys.exit(1)

tok = httpx.post(f'{BASE}/api/auth/login', json={'username':'admin','password':'admin123'}, timeout=5).json()['access_token']
hdr = {'Authorization': f'Bearer {tok}'}

cams = httpx.get(f'{BASE}/api/cameras', headers=hdr, timeout=5).json()
incs_raw = httpx.get(f'{BASE}/api/incidents', headers=hdr, timeout=5).json()
incs = incs_raw if isinstance(incs_raw, list) else incs_raw.get('incidents', incs_raw.get('items', []))
resp = httpx.get(f'{BASE}/api/responders', headers=hdr, timeout=5).json()
zones = httpx.get(f'{BASE}/api/zones', headers=hdr, timeout=5).json()
jobs = httpx.get(f'{BASE}/api/surveillance/jobs', headers=hdr, timeout=5).json()
models = httpx.get(f'{BASE}/api/models', headers=hdr, timeout=5).json()
analytics = httpx.get(f'{BASE}/api/analytics/summary', headers=hdr, timeout=5).json()

print(f'CAMERAS: {len(cams)} | INCIDENTS: {len(incs)} | RESPONDERS: {len(resp)} | ZONES: {len(zones)}')
print(f'VIDEO JOBS (session): {len(jobs)}')
model_info = [m["key"] + "(" + ("loaded" if m["loaded"] else "cached") + ")" for m in models]
print(f'MODELS: {model_info}')
print(f'ANALYTICS: today_incidents={analytics.get("today_incidents")} active={analytics.get("active_incidents")} resolved={analytics.get("resolved_today")}')

if incs:
    statuses = {}
    types = {}
    for i in incs:
        s = i.get('status', '?')
        t = i.get('incident_type', '?')
        statuses[s] = statuses.get(s, 0) + 1
        types[t] = types.get(t, 0) + 1
    print('INCIDENT STATUSES:', statuses)
    print('INCIDENT TYPES:', types)

# Check evidence
if incs:
    for inc in incs[:3]:
        ev = httpx.get(f'{BASE}/api/evidence/{inc["id"]}', headers=hdr, timeout=5).json()
        print(f'  Evidence for {inc.get("incident_id","?")}: {len(ev)} item(s)')
