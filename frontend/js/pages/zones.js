const zonesPage = {
  _zones: [],
  _cameras: [],
  
  async render() {
    return `
      <div class="fade-in">
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
          <h2>Virtual Zones</h2>
          <button class="btn btn-primary" onclick="window.zonesPage.openAddModal()">+ Add Zone</button>
        </div>
        
        <div id="zones-container">
          <div style="text-align:center;padding:40px;color:#8fa3bf;">Loading zones...</div>
        </div>
      </div>
      
      <!-- Zone Modal -->
      <div id="zone-modal" class="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;">
        <div class="modal-content card" style="width:100%;max-width:500px;margin:auto;">
          <h3 id="zone-modal-title" style="margin-top:0;">Add Zone</h3>
          <form id="zone-form" onsubmit="window.zonesPage.saveZone(event)">
            <input type="hidden" id="zone-id">
            
            <div style="margin-bottom:12px;">
              <label>Camera</label>
              <select id="zone-cam" class="input" required style="width:100%">
                <option value="" disabled selected>Select a camera</option>
              </select>
            </div>
            
            <div style="margin-bottom:12px;">
              <label>Zone Name</label>
              <input type="text" id="zone-name" class="input" required style="width:100%" placeholder="e.g. Server Room Entrance">
            </div>
            
            <div style="display:flex;gap:12px;margin-bottom:12px;">
              <div style="flex:1;">
                <label>Zone Type</label>
                <select id="zone-type" class="input" style="width:100%" required>
                  <option value="RESTRICTED">Restricted</option>
                  <option value="MONITORING">Monitoring</option>
                  <option value="SAFE">Safe</option>
                </select>
              </div>
              <div style="flex:1;">
                <label>Loitering Threshold (s)</label>
                <input type="number" id="zone-thresh" class="input" style="width:100%" value="30" min="0">
              </div>
            </div>
            
            <div style="margin-bottom:12px;">
              <label>Polygon Points (JSON Array)</label>
              <textarea id="zone-pts" class="input" style="width:100%;height:80px;font-family:monospace;" required placeholder="[[100,100], [200,100], [200,200], [100,200]]"></textarea>
              <small style="color:#a0aec0;display:block;margin-top:4px;">Hint: For the demo, use pixel coordinates relative to camera resolution.</small>
            </div>
            
            <div style="margin-bottom:24px;">
              <label>Color</label>
              <div style="display:flex;gap:8px;margin-top:8px;">
                <input type="color" id="zone-color" value="#fc4545" style="width:40px;height:40px;padding:0;border:none;background:none;cursor:pointer;">
              </div>
            </div>
            
            <div style="display:flex;justify-content:flex-end;gap:12px;">
              <button type="button" class="btn" onclick="document.getElementById('zone-modal').style.display='none'">Cancel</button>
              <button type="submit" class="btn btn-primary">Save Zone</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },
  
  async init() {
    await this.loadData();
  },
  
  async loadData() {
    try {
      [this._zones, this._cameras] = await Promise.all([
        window.api.getZones().catch(()=>[]),
        window.api.getCameras().catch(()=>[])
      ]);
      
      const sel = document.getElementById('zone-cam');
      if (sel) {
        sel.innerHTML = '<option value="" disabled selected>Select a camera</option>';
        this._cameras.forEach(c => {
          sel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
        });
      }
      
      this.renderZones();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to load zones');
    }
  },
  
  renderZones() {
    const container = document.getElementById('zones-container');
    if (!container) return;
    
    if (this._zones.length === 0) {
      container.innerHTML = '<div class="card" style="text-align:center;color:#a0aec0;">No zones configured</div>';
      return;
    }
    
    // Group by camera
    const grouped = {};
    this._zones.forEach(z => {
      if (!grouped[z.camera_id]) grouped[z.camera_id] = [];
      grouped[z.camera_id].push(z);
    });
    
    let html = '';
    for (const [camId, zones] of Object.entries(grouped)) {
      const cam = this._cameras.find(c => c.id === camId) || { name: 'Unknown Camera', camera_id: camId };
      
      html += `
        <div class="card" style="margin-bottom:24px;">
          <h3 style="margin-top:0;border-bottom:1px solid #2d3748;padding-bottom:12px;margin-bottom:16px;">📷 ${cam.name} <span style="font-size:14px;color:#a0aec0;font-weight:normal;margin-left:8px;">${cam.camera_id}</span></h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(300px,1fr));gap:16px;">
            ${zones.map(z => `
              <div style="border:1px solid #2d3748;border-radius:8px;padding:16px;background:rgba(255,255,255,0.02);position:relative;border-left:4px solid ${z.color || '#fc4545'};">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                  <h4 style="margin:0;">${z.name}</h4>
                  <span class="badge" style="background:#4a5568">${z.type}</span>
                </div>
                <div style="font-size:13px;color:#a0aec0;margin-bottom:16px;">
                  <p style="margin:4px 0;"><strong>Active:</strong> ${z.is_active ? '<span style="color:#68d391">Yes</span>' : '<span style="color:#fc4545">No</span>'}</p>
                  <p style="margin:4px 0;"><strong>Points:</strong> ${Array.isArray(z.polygon_points) ? z.polygon_points.length : 0} vertices</p>
                  ${z.loitering_threshold ? `<p style="margin:4px 0;"><strong>Loitering Threshold:</strong> ${z.loitering_threshold}s</p>` : ''}
                </div>
                <div style="display:flex;gap:8px;">
                  <button class="btn btn-sm" onclick="window.zonesPage.openEditModal('${z.id}')">Edit</button>
                  <button class="btn btn-sm" onclick="window.zonesPage.toggleActive('${z.id}', ${!z.is_active})">${z.is_active ? 'Deactivate' : 'Activate'}</button>
                  <button class="btn btn-sm" style="color:#fc4545;margin-left:auto;" onclick="window.zonesPage.deleteZone('${z.id}')">Delete</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }
    
    container.innerHTML = html;
  },
  
  openAddModal() {
    document.getElementById('zone-modal-title').innerText = 'Add Zone';
    document.getElementById('zone-form').reset();
    document.getElementById('zone-id').value = '';
    document.getElementById('zone-pts').value = '[[10,10], [90,10], [90,90], [10,90]]';
    document.getElementById('zone-modal').style.display = 'flex';
  },
  
  openEditModal(id) {
    const z = this._zones.find(x => x.id === id);
    if (!z) return;
    
    document.getElementById('zone-modal-title').innerText = 'Edit Zone';
    document.getElementById('zone-id').value = z.id;
    document.getElementById('zone-cam').value = z.camera_id;
    document.getElementById('zone-name').value = z.name;
    document.getElementById('zone-type').value = z.type;
    document.getElementById('zone-thresh').value = z.loitering_threshold || 30;
    document.getElementById('zone-pts').value = typeof z.polygon_points === 'string' ? z.polygon_points : JSON.stringify(z.polygon_points);
    document.getElementById('zone-color').value = z.color || '#fc4545';
    
    document.getElementById('zone-modal').style.display = 'flex';
  },
  
  async saveZone(e) {
    e.preventDefault();
    const id = document.getElementById('zone-id').value;
    
    let pts;
    try {
      pts = JSON.parse(document.getElementById('zone-pts').value);
      if (!Array.isArray(pts)) throw new Error('Must be an array');
    } catch(err) {
      alert('Invalid polygon points JSON. Please check format.');
      return;
    }
    
    const payload = {
      camera_id: document.getElementById('zone-cam').value,
      name: document.getElementById('zone-name').value,
      type: document.getElementById('zone-type').value,
      loitering_threshold: parseInt(document.getElementById('zone-thresh').value, 10),
      polygon_points: pts,
      color: document.getElementById('zone-color').value
    };
    
    try {
      if (id) {
        await window.api.updateZone(id, payload);
        if(window.showSuccessToast) window.showSuccessToast('Zone updated');
      } else {
        await window.api.createZone(payload);
        if(window.showSuccessToast) window.showSuccessToast('Zone created');
      }
      document.getElementById('zone-modal').style.display = 'none';
      await this.loadData();
    } catch(err) {
      if(window.showErrorToast) window.showErrorToast('Failed to save zone');
    }
  },
  
  async toggleActive(id, activate) {
    try {
      await window.api.updateZone(id, { is_active: activate });
      await this.loadData();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to update zone status');
    }
  },
  
  async deleteZone(id) {
    if (!confirm('Are you sure you want to delete this zone?')) return;
    try {
      await window.api.deleteZone(id);
      if(window.showSuccessToast) window.showSuccessToast('Zone deleted');
      await this.loadData();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to delete zone');
    }
  },
  
  destroy() {}
};

window.zonesPage = zonesPage;
