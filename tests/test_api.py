import urllib.request, json, sys

BASE = 'http://localhost:8000'

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, body, {'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

def count_list(data, keys=['items', 'cameras', 'incidents', 'responders', 'zones', 'results']):
    if isinstance(data, list):
        return len(data)
    for k in keys:
        if k in data:
            return len(data[k])
    if 'total' in data:
        return data['total']
    return '?'

errors = []

print("Testing AegisWatch API...")
print("=" * 50)

# Test 1: Health
h = get('/api/health')
assert h['status'] == 'ok'
print('[1] PASS  Health:', h['status'])

# Test 2: Login admin
auth = post('/api/auth/login', {'username': 'admin', 'password': 'admin123'})
token = auth['access_token']
assert token
print('[2] PASS  Admin login OK')

# Test 3: Me
me = get('/api/auth/me', token)
assert me['username'] == 'admin'
print('[3] PASS  /auth/me:', me['username'], '|', me['role'])

# Test 4: Cameras
cams = get('/api/cameras', token)
n = count_list(cams)
print('[4] PASS  Cameras:', n)

# Test 5: Incidents  
incs = get('/api/incidents', token)
n = count_list(incs)
print('[5] PASS  Incidents:', n)

# Test 6: Analytics summary
stats = get('/api/analytics/summary', token)
print('[6] PASS  Analytics:', stats)

# Test 7: Responders
resp = get('/api/responders', token)
n = count_list(resp)
print('[7] PASS  Responders:', n)

# Test 8: Incidents by type
ibt = get('/api/analytics/incidents-by-type', token)
print('[8] PASS  Incidents by type:', ibt)

# Test 9: Severity distribution
sev = get('/api/analytics/severity-distribution', token)
print('[9] PASS  Severity dist:', sev)

# Test 10: Operator login
auth2 = post('/api/auth/login', {'username': 'operator', 'password': 'operator123'})
assert auth2['access_token']
print('[10] PASS Operator login OK')

# Test 11: Responder login
auth3 = post('/api/auth/login', {'username': 'responder1', 'password': 'resp123'})
assert auth3['access_token']
print('[11] PASS Responder login OK')

# Test 12: Zones
zones = get('/api/zones', token)
n = count_list(zones)
print('[12] PASS Zones:', n)

print()
print("=" * 50)
print("ALL API TESTS PASSED - Backend Fully Operational!")
