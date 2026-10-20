const respondersPage = {
  _responders: [],
  
  async render() {
    return `
      <div class="fade-in">
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
          <h2>Responders</h2>
          <button class="btn btn-primary" onclick="window.respondersPage.openAddModal()">+ Add Responder</button>
        </div>
        
        <div class="card" style="margin-bottom:24px;background:#2d3748;">
          <h3 style="margin-top:0;">Find Nearest Responders</h3>
          <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
            <div style="flex:1;min-width:150px;">
              <label>Latitude</label>
              <input type="number" step="any" id="find-lat" class="input" style="width:100%" placeholder="e.g. 28.6139">
            </div>
            <div style="flex:1;min-width:150px;">
              <label>Longitude</label>
              <input type="number" step="any" id="find-lng" class="input" style="width:100%" placeholder="e.g. 77.2090">
            </div>
            <button class="btn btn-primary" onclick="window.respondersPage.calculateNearest()">Calculate Nearest</button>
          </div>
          <div id="nearest-results" style="margin-top:16px;"></div>
        </div>
        
        <div class="filter-bar" style="display:flex;gap:16px;margin-bottom:24px;background:#1a202c;padding:16px;border-radius:8px;">
          <input type="text" id="resp-search" class="input" placeholder="Search by name or ID..." style="flex:1;" onkeyup="window.respondersPage.applyFilters()">
          <select id="resp-avail" class="input" onchange="window.respondersPage.applyFilters()">
            <option value="ALL">All Availability</option>
            <option value="AVAILABLE">Available</option>
            <option value="BUSY">Busy</option>
            <option value="OFFLINE">Offline</option>
          </select>
        </div>
        
        <div id="responder-grid" class="camera-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:20px;">
          <div style="grid-column:1/-1;text-align:center;">Loading responders...</div>
        </div>
      </div>
      
      <!-- Add Responder Modal -->
      <div id="responder-modal" class="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;">
        <div class="modal-content card" style="width:100%;max-width:500px;margin:auto;">
          <h3 style="margin-top:0;">Add Responder</h3>
          <form id="responder-form" onsubmit="window.respondersPage.saveResponder(event)">
            <div style="margin-bottom:12px;">
              <label>Name</label>
              <input type="text" id="resp-name" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Responder ID</label>
              <input type="text" id="resp-id" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Station</label>
              <input type="text" id="resp-station" class="input" required style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Phone</label>
              <input type="text" id="resp-phone" class="input" style="width:100%">
            </div>
            <div style="margin-bottom:12px;">
              <label>Role</label>
              <select id="resp-role" class="input" style="width:100%">
                <option value="SECURITY">Security</option>
                <option value="POLICE">Police</option>
                <option value="MEDICAL">Medical</option>
                <option value="FIRE">Fire</option>
              </select>
            </div>
            <div style="margin-bottom:12px;">
              <label>Availability</label>
              <select id="resp-status" class="input" style="width:100%">
                <option value="AVAILABLE">Available</option>
                <option value="BUSY">Busy</option>
                <option value="OFFLINE">Offline</option>
              </select>
            </div>
            <div style="display:flex;gap:12px;margin-bottom:24px;">
              <div style="flex:1;">
                <label>Latitude</label>
                <input type="number" step="any" id="resp-lat" class="input" required style="width:100%">
              </div>
              <div style="flex:1;">
                <label>Longitude</label>
                <input type="number" step="any" id="resp-lng" class="input" required style="width:100%">
              </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:12px;">
              <button type="button" class="btn" onclick="document.getElementById('responder-modal').style.display='none'">Cancel</button>
              <button type="submit" class="btn btn-primary">Save</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },
  
  async init() {
    await this.loadResponders();
  },
  
  async loadResponders() {
    try {
      this._responders = await window.api.getResponders();
      this.applyFilters();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to load responders');
    }
  },
  
  applyFilters() {
    const term = (document.getElementById('resp-search')?.value || '').toLowerCase();
    const status = document.getElementById('resp-avail')?.value || 'ALL';
    
    const filtered = this._responders.filter(r => {
      const matchTerm = (r.name || '').toLowerCase().includes(term) || (r.responder_id || '').toLowerCase().includes(term);
      const matchStatus = status === 'ALL' || r.availability_status === status;
      return matchTerm && matchStatus;
    });
    
    this._renderGrid(filtered);
  },
  
  _renderGrid(responders) {
    const grid = document.getElementById('responder-grid');
    if (!grid) return;
    
    if (responders.length === 0) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#8fa3bf;">No responders found</div>';
      return;
    }
    
    grid.innerHTML = responders.map(r => {
      const statusColor = r.availability_status === 'AVAILABLE' ? '#68d391' : r.availability_status === 'BUSY' ? '#f6ad55' : '#a0aec0';
      return `
        <div class="card" style="display:flex;flex-direction:column;gap:12px;">
          <div style="display:flex;align-items:center;gap:16px;">
            <div style="font-size:32px;background:#1a202c;width:60px;height:60px;display:flex;align-items:center;justify-content:center;border-radius:50%;">👮</div>
            <div style="flex:1;">
              <h4 style="margin:0;font-size:18px;">${r.name}</h4>
              <div style="font-size:14px;color:#a0aec0;font-family:monospace;">${r.responder_id}</div>
            </div>
          </div>
          <div>
            <span class="badge" style="background:#4a5568">${r.role}</span>
            <span class="badge" style="background:transparent;border:1px solid ${statusColor};color:${statusColor}">${r.availability_status}</span>
          </div>
          <div style="font-size:14px;color:#cbd5e0;">
            <p style="margin:4px 0;"><strong>Station:</strong> ${r.station}</p>
            <p style="margin:4px 0;"><strong>Phone:</strong> ${r.phone || 'N/A'}</p>
          </div>
          <div style="display:flex;gap:8px;margin-top:auto;">
            <select class="input" style="flex:1;padding:6px;" onchange="window.respondersPage.updateStatus('${r.id}', this.value)">
              <option value="" disabled selected>Update Status</option>
              <option value="AVAILABLE">Set Available</option>
              <option value="BUSY">Set Busy</option>
              <option value="OFFLINE">Set Offline</option>
            </select>
            <button class="btn" style="padding:6px 12px;">Assignments</button>
          </div>
        </div>
      `;
    }).join('');
  },
  
  openAddModal() {
    document.getElementById('responder-form').reset();
    document.getElementById('responder-modal').style.display = 'flex';
  },
  
  async saveResponder(e) {
    e.preventDefault();
    const payload = {
      name: document.getElementById('resp-name').value,
      responder_id: document.getElementById('resp-id').value,
      station: document.getElementById('resp-station').value,
      phone: document.getElementById('resp-phone').value,
      role: document.getElementById('resp-role').value,
      availability_status: document.getElementById('resp-status').value,
      latitude: parseFloat(document.getElementById('resp-lat').value),
      longitude: parseFloat(document.getElementById('resp-lng').value)
    };
    
    try {
      await window.api.createResponder(payload);
      if(window.showSuccessToast) window.showSuccessToast('Responder added');
      document.getElementById('responder-modal').style.display = 'none';
      await this.loadResponders();
    } catch(err) {
      if(window.showErrorToast) window.showErrorToast('Failed to add responder');
    }
  },
  
  async updateStatus(id, status) {
    if (!status) return;
    try {
      await window.api.updateResponderAvailability(id, status);
      if(window.showSuccessToast) window.showSuccessToast(`Status updated to ${status}`);
      await this.loadResponders();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to update status');
    }
  },
  
  async calculateNearest() {
    const lat = document.getElementById('find-lat').value;
    const lng = document.getElementById('find-lng').value;
    if (!lat || !lng) {
      if(window.showErrorToast) window.showErrorToast('Please enter latitude and longitude');
      return;
    }
    
    try {
      const res = await window.api.getNearestResponders(parseFloat(lat), parseFloat(lng));
      const resultsDiv = document.getElementById('nearest-results');
      if (!res || res.length === 0) {
        resultsDiv.innerHTML = '<p>No available responders found nearby.</p>';
        return;
      }
      
      resultsDiv.innerHTML = `
        <table class="table" style="width:100%;text-align:left;">
          <tr><th>Name</th><th>Role</th><th>Station</th><th>Distance</th><th>Action</th></tr>
          ${res.map(r => `
            <tr>
              <td>👮 ${r.name}</td>
              <td>${r.role}</td>
              <td>${r.station}</td>
              <td><strong>${(r.distance||0).toFixed(2)} km</strong></td>
              <td><button class="btn btn-sm">Alert</button></td>
            </tr>
          `).join('')}
        </table>
      `;
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to calculate nearest responders');
    }
  }
};

window.respondersPage = respondersPage;
