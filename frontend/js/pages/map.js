const mapPage = {
  _map: null,
  _markers: [],
  _refreshTimer: null,
  
  async render() {
    return `
      <style>
        .map-page-layout { display: flex; height: calc(100vh - 80px); margin: -24px; }
        #surveillance-map { flex: 1; height: 100%; background: #111; }
        .map-sidebar { width: 320px; background: #1a202c; border-left: 1px solid #2d3748; display: flex; flex-direction: column; overflow-y: auto; }
        .leaflet-tile { filter: brightness(0.5) saturate(0.6) hue-rotate(180deg); }
        .sidebar-section { padding: 16px; border-bottom: 1px solid #2d3748; }
        .sidebar-item { padding: 8px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px; }
        .sidebar-item:hover { background: #2d3748; }
        .map-popup-title { font-weight: bold; font-size: 16px; margin-bottom: 8px; }
        .map-popup-meta { font-size: 13px; color: #666; margin-bottom: 4px; }
      </style>
      <div class="map-page-layout fade-in">
        <div id="surveillance-map"></div>
        <div class="map-sidebar">
          <div class="sidebar-section" style="display:flex;justify-content:space-between;align-items:center;">
            <h3 style="margin:0;">Map Layers</h3>
            <button class="btn btn-sm" onclick="window.mapPage.loadData()">↻ Refresh</button>
          </div>
          <div class="sidebar-section">
            <h4 style="margin:0 0 12px 0;">Legend & Filters</h4>
            <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
              <input type="checkbox" id="layer-cameras" checked onchange="window.mapPage.renderMarkers()"> 
              <span style="color:#63b3ed">📷 Cameras</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
              <input type="checkbox" id="layer-incidents" checked onchange="window.mapPage.renderMarkers()"> 
              <span style="color:#fc4545">🚨 Active Incidents</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;">
              <input type="checkbox" id="layer-responders" checked onchange="window.mapPage.renderMarkers()"> 
              <span style="color:#68d391">👮 Responders</span>
            </label>
          </div>
          <div class="sidebar-section" style="flex:1;">
            <h4 style="margin:0 0 12px 0;color:#fc4545;">Active Incidents</h4>
            <div id="map-sidebar-incidents">Loading...</div>
          </div>
        </div>
      </div>
    `;
  },
  
  async init() {
    if (typeof L === 'undefined') {
      const link = document.createElement('link');
      link.rel = 'stylesheet'; link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);
      
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => this.setupMap();
      document.head.appendChild(script);
    } else {
      this.setupMap();
    }
  },
  
  setupMap() {
    this._map = L.map('surveillance-map').setView([28.6139, 77.2090], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(this._map);
    
    this.loadData();
    this._refreshTimer = setInterval(() => this.loadData(), 60000);
  },
  
  async loadData() {
    try {
      const [cameras, incidents, responders] = await Promise.all([
        window.api.getCameras().catch(()=>[]),
        window.api.getIncidents({status: 'NEW,UNDER_REVIEW,VERIFIED'}).catch(()=>[]),
        window.api.getResponders().catch(()=>[])
      ]);
      
      this._data = { cameras, incidents, responders };
      this.renderMarkers();
      this.renderSidebar();
    } catch(e) {
      console.error('Map data load error', e);
    }
  },
  
  renderMarkers() {
    if (!this._map || !this._data) return;
    
    // Clear old
    this._markers.forEach(m => m.remove());
    this._markers = [];
    
    const showCams = document.getElementById('layer-cameras')?.checked;
    const showIncs = document.getElementById('layer-incidents')?.checked;
    const showReps = document.getElementById('layer-responders')?.checked;
    
    if (showCams) {
      this._data.cameras.forEach(c => {
        if (!c.latitude || !c.longitude) return;
        const icon = L.divIcon({
          html: `<div style="background:#1a4d9b;border:2px solid #63b3ed;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:12px;box-shadow:0 0 10px #63b3ed;">📷</div>`,
          iconSize: [28, 28], iconAnchor: [14, 14], className: ''
        });
        const m = L.marker([c.latitude, c.longitude], {icon}).bindPopup(`
          <div class="map-popup-title">${c.name}</div>
          <div class="map-popup-meta">ID: ${c.camera_id}</div>
          <div class="map-popup-meta">Status: ${c.status}</div>
          <a href="#/live?camera=${c.id}" style="color:#1a4d9b;">View Live Feed</a>
        `).addTo(this._map);
        this._markers.push(m);
      });
    }
    
    if (showIncs) {
      this._data.incidents.forEach(i => {
        if (!i.latitude || !i.longitude) return;
        const icon = L.divIcon({
          html: `<div style="background:#742a2a;border:2px solid #fc4545;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 0 15px #fc4545;animation:pulse 1.5s infinite;">🚨</div>`,
          iconSize: [32, 32], iconAnchor: [16, 16], className: ''
        });
        const m = L.marker([i.latitude, i.longitude], {icon}).bindPopup(`
          <div class="map-popup-title">🚨 ${i.type}</div>
          <div class="map-popup-meta">Camera: ${i.camera_name || i.camera_id}</div>
          <div class="map-popup-meta">Risk: ${Math.round(i.risk_score||0)}%</div>
          <div class="map-popup-meta">Status: ${i.status}</div>
          <a href="#/incidents/${i.id}" style="display:inline-block;margin-top:8px;padding:6px 12px;background:#1a4d9b;color:#fff;text-decoration:none;border-radius:4px;">View Incident</a>
        `).addTo(this._map);
        this._markers.push(m);
      });
    }
    
    if (showReps) {
      this._data.responders.forEach(r => {
        if (!r.latitude || !r.longitude) return;
        const icon = L.divIcon({
          html: `<div style="background:#22543d;border:2px solid #68d391;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:12px;box-shadow:0 0 10px #68d391;">👮</div>`,
          iconSize: [28, 28], iconAnchor: [14, 14], className: ''
        });
        const m = L.marker([r.latitude, r.longitude], {icon}).bindPopup(`
          <div class="map-popup-title">👮 ${r.name}</div>
          <div class="map-popup-meta">Role: ${r.role}</div>
          <div class="map-popup-meta">Status: ${r.availability_status}</div>
        `).addTo(this._map);
        this._markers.push(m);
      });
    }
  },
  
  renderSidebar() {
    const sb = document.getElementById('map-sidebar-incidents');
    if (!sb) return;
    
    const incs = this._data.incidents;
    if (!incs || incs.length === 0) {
      sb.innerHTML = '<div style="color:#a0aec0;font-size:14px;">No active incidents</div>';
      return;
    }
    
    sb.innerHTML = incs.map(i => `
      <div class="sidebar-item" onclick="window.mapPage.panTo(${i.latitude}, ${i.longitude})">
        <span style="font-size:16px;">🚨</span>
        <div style="flex:1;overflow:hidden;">
          <div style="font-weight:bold;white-space:nowrap;text-overflow:ellipsis;">${i.type}</div>
          <div style="font-size:12px;color:#a0aec0;white-space:nowrap;text-overflow:ellipsis;">${i.location || i.camera_id}</div>
        </div>
      </div>
    `).join('');
  },
  
  panTo(lat, lng) {
    if (this._map) {
      this._map.flyTo([lat, lng], 17);
    }
  },
  
  destroy() {
    clearInterval(this._refreshTimer);
    if (this._map) {
      this._map.remove();
      this._map = null;
    }
  }
};

// CSS for pulse animation
const style = document.createElement('style');
style.innerHTML = `@keyframes pulse { 0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(252, 69, 69, 0.7); } 70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(252, 69, 69, 0); } 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(252, 69, 69, 0); } }`;
document.head.appendChild(style);

window.mapPage = mapPage;
