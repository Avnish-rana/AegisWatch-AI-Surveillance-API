/**
 * AegisWatch — API Client
 * Centralized fetch wrapper with JWT authentication, error handling, and retry
 */

const API_BASE = '';  // same origin

class ApiClient {
  constructor() {
    this._token = localStorage.getItem('aegis_token') || null;
  }

  setToken(token) {
    this._token = token;
    if (token) {
      localStorage.setItem('aegis_token', token);
    } else {
      localStorage.removeItem('aegis_token');
    }
  }

  getToken() { return this._token; }

  _headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    if (this._token) h['Authorization'] = `Bearer ${this._token}`;
    return h;
  }

  async _fetch(method, path, body = null, opts = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
      method,
      headers: this._headers(opts.headers || {}),
    };
    if (body !== null) config.body = JSON.stringify(body);

    try {
      const resp = await fetch(url, config);
      
      if (resp.status === 401) {
        // Token expired or invalid
        this.setToken(null);
        window.location.hash = '#/login';
        throw new Error('Authentication required. Please log in again.');
      }

      if (resp.status === 204) return null;

      const data = await resp.json().catch(() => ({ detail: resp.statusText }));
      
      if (!resp.ok) {
        const msg = data.detail || data.message || `HTTP ${resp.status}`;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
      
      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('Cannot connect to server. Is the backend running?');
      }
      throw err;
    }
  }

  get(path, params = {}) {
    let url = path;
    const qs = new URLSearchParams(params).toString();
    if (qs) url = `${path}?${qs}`;
    return this._fetch('GET', url);
  }

  post(path, body = {}) { return this._fetch('POST', path, body); }
  put(path, body = {})  { return this._fetch('PUT',  path, body); }
  delete(path)          { return this._fetch('DELETE', path); }
  patch(path, body = {}) { return this._fetch('PATCH', path, body); }

  // ── Auth ────────────────────────────────────────────────
  async login(username, password) {
    const data = await this.post('/api/auth/login', { username, password });
    if (data.access_token) this.setToken(data.access_token);
    return data;
  }

  async me() { return this.get('/api/auth/me'); }

  logout() {
    this.setToken(null);
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }

  // ── Cameras ─────────────────────────────────────────────
  getCameras(params = {}) { return this.get('/api/cameras', params); }
  getCamera(id)           { return this.get(`/api/cameras/${id}`); }
  createCamera(data)      { return this.post('/api/cameras', data); }
  updateCamera(id, data)  { return this.put(`/api/cameras/${id}`, data); }
  deleteCamera(id)        { return this.delete(`/api/cameras/${id}`); }
  toggleCamera(id)        { return this.post(`/api/cameras/${id}/toggle`); }
  getStreamInfo(id)       { return this.get(`/api/cameras/${id}/stream-info`); }

  // ── Incidents ───────────────────────────────────────────
  getIncidents(params = {}) { return this.get('/api/incidents', params); }
  getIncident(id)            { return this.get(`/api/incidents/${id}`); }
  createIncident(data)       { return this.post('/api/incidents', data); }
  verifyIncident(id, notes = '') { return this.post(`/api/incidents/${id}/verify`, { notes }); }
  rejectIncident(id, reason)     { return this.post(`/api/incidents/${id}/reject`, { reason }); }
  assignIncident(id, responderId = null) {
    return this.post(`/api/incidents/${id}/assign`, responderId ? { responder_id: responderId } : {});
  }
  acceptIncident(id)             { return this.post(`/api/incidents/${id}/accept`); }
  respondingIncident(id)         { return this.post(`/api/incidents/${id}/responding`); }
  resolveIncident(id, notes)     { return this.post(`/api/incidents/${id}/resolve`, { notes }); }
  cancelIncident(id, reason)     { return this.post(`/api/incidents/${id}/cancel`, { reason }); }
  getIncidentEvidence(id)        { return this.get(`/api/incidents/${id}/evidence`); }
  getIncidentHistory(id)         { return this.get(`/api/incidents/${id}/history`); }

  // ── Responders ──────────────────────────────────────────
  getResponders(params = {}) { return this.get('/api/responders', params); }
  getResponder(id)            { return this.get(`/api/responders/${id}`); }
  createResponder(data)       { return this.post('/api/responders', data); }
  updateResponder(id, data)   { return this.put(`/api/responders/${id}`, data); }
  getNearestResponders(lat, lon) {
    return this.get('/api/responders/nearest', { lat, lon });
  }
  updateResponderAvailability(id, availability) {
    return this.post(`/api/responders/${id}/availability`, { availability });
  }

  // ── Zones ───────────────────────────────────────────────
  getZones(params = {}) { return this.get('/api/zones', params); }
  getZone(id)            { return this.get(`/api/zones/${id}`); }
  createZone(data)       { return this.post('/api/zones', data); }
  updateZone(id, data)   { return this.put(`/api/zones/${id}`, data); }
  deleteZone(id)         { return this.delete(`/api/zones/${id}`); }
  getCameraZones(cameraId) { return this.get(`/api/cameras/${cameraId}/zones`); }

  // ── Analytics ───────────────────────────────────────────
  getAnalyticsSummary()        { return this.get('/api/analytics/summary'); }
  getIncidentsByType()         { return this.get('/api/analytics/incidents-by-type'); }
  getIncidentsByCamera()       { return this.get('/api/analytics/incidents-by-camera'); }
  getIncidentsByHour()         { return this.get('/api/analytics/incidents-by-hour'); }
  getSeverityDistribution()    { return this.get('/api/analytics/severity-distribution'); }
  getResponseTimes()           { return this.get('/api/analytics/response-times'); }

  // ── Evidence ────────────────────────────────────────────
  getEvidenceUrl(evidenceId) { return `${API_BASE}/api/evidence/file/${evidenceId}`; }
  getSnapshotUrl(incidentId) { return `${API_BASE}/data/evidence/${incidentId}/snapshot.jpg`; }
  getVideoUrl(incidentId)    { return `${API_BASE}/data/evidence/${incidentId}/incident.mp4`; }

  // ── Surveillance ────────────────────────────────────────────
  getSurveillanceJobs()            { return this.get('/api/surveillance/jobs'); }
  getSurveillanceJob(jobId)        { return this.get(`/api/surveillance/job/${jobId}`); }
  cancelSurveillanceJob(jobId)     { return this.post(`/api/surveillance/cancel-job/${jobId}`); }
  pauseSurveillanceJob(jobId)      { return this.post(`/api/surveillance/job/${jobId}/pause`); }
  resumeSurveillanceJob(jobId)     { return this.post(`/api/surveillance/job/${jobId}/resume`); }
  sendWebcamFrame(b64, cameraId)   {
    return this.post('/api/surveillance/webcam-frame', { frame_base64: b64, camera_id: cameraId });
  }
}

// Global singleton
const api = new ApiClient();
window.api = api;
