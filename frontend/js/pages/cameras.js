const camerasPage = {
  _cameras: [],
  
  async render() {
    return `
      <div class="fade-in cameras-page">
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
          <h2>Cameras</h2>
          <button class="btn btn-primary" onclick="window.camerasPage.openAddModal()">+ Add Camera</button>
        </div>
        
        <div class="filter-bar" style="display:flex;gap:16px;margin-bottom:24px;background:#1a202c;padding:16px;border-radius:8px;">
          <input type="text" id="camera-search" class="input" placeholder="Search by name or ID..." style="flex:1;" onkeyup="window.camerasPage.applyFilters()">
          <select id="camera-status-filter" class="input" onchange="window.camerasPage.applyFilters()">
            <option value="ALL">All Status</option>
            <option value="ONLINE">Online</option>
            <option value="OFFLINE">Offline</option>
            <option value="ERROR">Error</option>
          </select>
        </div>
        
        <div id="camera-grid" class="camera-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:20px;">
          <div style="grid-column:1/-1;text-align:center;">Loading cameras...</div>
        </div>
      </div>
      
      <!-- Modal -->
      <div id="camera-modal" class="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;">
        <div class="modal-content card" style="width:100%;max-width:500px;margin:auto;margin-top:10vh;">
          <h3 id="camera-modal-title" style="margin-top:0;">Add Camera</h3>
          <form id="camera-form" onsubmit="window.camerasPage.saveCamera(event)">
            <input type="hidden" id="camera-form-id">
            
            <div style="margin-bottom:12px;">
              <label>Camera ID (unique)</label>
              <input type="text" id="cam-id" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Name</label>
              <input type="text" id="cam-name" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Source Type</label>
              <select id="cam-type" class="input" style="width:100%">
                <option value="RTSP">RTSP</option>
                <option value="WEBCAM">Webcam</option>
                <option value="FILE">File</option>
                <option value="DEMO">Demo</option>
              </select>
            </div>
            <div style="margin-bottom:12px;">
              <label>Source URL</label>
              <input type="text" id="cam-url" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Location Name</label>
              <input type="text" id="cam-loc" class="input" required style="width:100%">
            </div>
            <div style="display:flex;gap:12px;margin-bottom:12px;">
              <div style="flex:1;">
                <label>Latitude</label>
                <input type="number" step="any" id="cam-lat" class="input" required style="width:100%">
              </div>
              <div style="flex:1;">
                <label>Longitude</label>
                <input type="number" step="any" id="cam-lng" class="input" required style="width:100%">
              </div>
            </div>
            <div style="margin-bottom:24px;">
              <label>Description</label>
              <textarea id="cam-desc" class="input" style="width:100%"></textarea>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:12px;">
              <button type="button" class="btn" onclick="document.getElementById('camera-modal').style.display='none'">Cancel</button>
              <button type="submit" class="btn btn-primary">Save Camera</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },
  
  async init() {
    await this.loadCameras();
  },
  
  async loadCameras() {
    try {
      if (window.api && window.api.getCameras) {
        this._cameras = await window.api.getCameras();
        this.applyFilters();
      }
    } catch(e) {
      console.error(e);
      if(window.showErrorToast) window.showErrorToast('Failed to load cameras');
    }
  },
  
  applyFilters() {
    const term = (document.getElementById('camera-search')?.value || '').toLowerCase();
    const status = document.getElementById('camera-status-filter')?.value || 'ALL';
    
    const filtered = this._cameras.filter(c => {
      const matchTerm = (c.name || '').toLowerCase().includes(term) || (c.camera_id || '').toLowerCase().includes(term);
      const matchStatus = status === 'ALL' || c.status === status;
      return matchTerm && matchStatus;
    });
    
    this._renderGrid(filtered);
  },
  
  _renderGrid(cameras) {
    const grid = document.getElementById('camera-grid');
    if (!grid) return;
    
    if (cameras.length === 0) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#8fa3bf;">No cameras found</div>';
      return;
    }
    
    grid.innerHTML = cameras.map(c => {
      const statusColor = c.status === 'ONLINE' ? '#68d391' : c.status === 'ERROR' ? '#fc4545' : '#a0aec0';
      const imgSrc = c.source_type === 'DEMO' ? '/frontend/js/assets/demo-feed.svg' : `/api/stream/${c.id}/snapshot`;
      return `
        <div class="card camera-card" style="padding:0;overflow:hidden;display:flex;flex-direction:column;">
          <div style="position:relative;height:180px;background:#1a202c;">
            <img src="${imgSrc}" style="width:100%;height:100%;object-fit:cover;" onerror="this.src='/frontend/js/assets/no-feed.svg'; this.onerror=null">
            <div style="position:absolute;top:10px;left:10px;background:rgba(0,0,0,0.6);padding:4px 8px;border-radius:4px;font-size:12px;font-family:monospace;">${c.camera_id}</div>
            <div style="position:absolute;top:10px;right:10px;background:rgba(0,0,0,0.6);padding:4px 8px;border-radius:4px;font-size:12px;display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${statusColor}"></span>
              ${c.status}
            </div>
            <div style="position:absolute;bottom:10px;right:10px;">
              <span class="badge" style="background:#4a5568">${c.source_type}</span>
            </div>
          </div>
          <div style="padding:16px;flex:1;">
            <h4 style="margin:0 0 8px 0;">${c.name}</h4>
            <div style="font-size:14px;color:#a0aec0;margin-bottom:16px;">📍 ${c.location_name || 'Unknown Location'}</div>
            <div style="display:flex;gap:8px;">
              <button class="btn btn-primary" style="flex:1;padding:6px 12px;" onclick="window.location.hash='#/live?camera=${c.id}'">Live Feed</button>
              <button class="btn" style="padding:6px 12px;" onclick="window.camerasPage.openEditModal('${c.id}')">Edit</button>
              <button class="btn" style="padding:6px 12px;color:#fc4545;" onclick="window.camerasPage.toggleDisable('${c.id}', ${c.status !== 'DISABLED'})">
                ${c.status === 'DISABLED' ? 'Enable' : 'Disable'}
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  },
  
  openAddModal() {
    document.getElementById('camera-modal-title').innerText = 'Add Camera';
    document.getElementById('camera-form').reset();
    document.getElementById('camera-form-id').value = '';
    document.getElementById('camera-modal').style.display = 'flex';
  },
  
  openEditModal(id) {
    const c = this._cameras.find(cam => cam.id === id);
    if (!c) return;
    document.getElementById('camera-modal-title').innerText = 'Edit Camera';
    document.getElementById('camera-form-id').value = c.id;
    document.getElementById('cam-id').value = c.camera_id || '';
    document.getElementById('cam-name').value = c.name || '';
    document.getElementById('cam-type').value = c.source_type || 'RTSP';
    document.getElementById('cam-url').value = c.source_url || '';
    document.getElementById('cam-loc').value = c.location_name || '';
    document.getElementById('cam-lat').value = c.latitude || '';
    document.getElementById('cam-lng').value = c.longitude || '';
    document.getElementById('cam-desc').value = c.description || '';
    document.getElementById('camera-modal').style.display = 'flex';
  },
  
  async saveCamera(e) {
    e.preventDefault();
    const id = document.getElementById('camera-form-id').value;
    const payload = {
      camera_id: document.getElementById('cam-id').value,
      name: document.getElementById('cam-name').value,
      source_type: document.getElementById('cam-type').value,
      source_url: document.getElementById('cam-url').value,
      location_name: document.getElementById('cam-loc').value,
      latitude: parseFloat(document.getElementById('cam-lat').value),
      longitude: parseFloat(document.getElementById('cam-lng').value),
      description: document.getElementById('cam-desc').value
    };
    
    try {
      if (id) {
        await window.api.updateCamera(id, payload);
        if(window.showSuccessToast) window.showSuccessToast('Camera updated');
      } else {
        await window.api.createCamera(payload);
        if(window.showSuccessToast) window.showSuccessToast('Camera added');
      }
      document.getElementById('camera-modal').style.display = 'none';
      await this.loadCameras();
    } catch(err) {
      console.error(err);
      if(window.showErrorToast) window.showErrorToast('Failed to save camera');
    }
  },
  
  async toggleDisable(id, disable) {
    if (!confirm(`Are you sure you want to ${disable ? 'disable' : 'enable'} this camera?`)) return;
    try {
      await window.api.updateCamera(id, { status: disable ? 'DISABLED' : 'ONLINE' });
      await this.loadCameras();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to change status');
    }
  },
  
  destroy() {
    // cleanup
  }
};

window.camerasPage = camerasPage;
