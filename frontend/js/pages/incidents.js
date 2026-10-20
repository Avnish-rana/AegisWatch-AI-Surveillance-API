// Helpers included directly for runtime consistency
function severityBadge(severity) { const s = (severity||'').toLowerCase(); return `<span class="badge badge-${s}">${severity||'UNKNOWN'}</span>`; }
function statusBadge(status) { const s = (status||'').toLowerCase().replace(' ','_'); return `<span class="badge status-${s}">${(status||'').replace('_',' ')}</span>`; }
function incidentTypeIcon(type) { const icons = { FIGHT:'👊',THEFT:'💼',INTRUSION:'🚫',LOITERING:'⏱️',ABANDONED_OBJECT:'🎒',SUSPICIOUS_MOVEMENT:'🏃',WEAPON_DETECTED:'🔫' }; return icons[type]||'⚠️'; }
function riskBar(score, severity) {
  const s = (severity || 'low').toLowerCase();
  return `<div class="risk-bar-container" style="display:flex;align-items:center;gap:8px;"><div class="risk-bar" style="flex:1;height:6px;background:#2d3748;border-radius:3px;overflow:hidden;"><div class="risk-bar-fill ${s}" style="width:${score}%;height:100%;background:var(--color-${s});"></div></div><span class="text-xs" style="min-width:35px">${Math.round(score)}%</span></div>`;
}

const incidentsPage = {
  _incidents: [],
  _currentIncident: null,
  
  async render() {
    return `
      <div class="fade-in">
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
          <h2>Incidents</h2>
          <button class="btn btn-primary" onclick="window.incidentsPage.createTestIncident()">+ Create Test Incident</button>
        </div>
        
        <div class="filter-bar" style="display:flex;gap:16px;margin-bottom:24px;background:#1a202c;padding:16px;border-radius:8px;flex-wrap:wrap;">
          <input type="text" id="inc-search" class="input" placeholder="Search ID/Location..." onkeyup="window.incidentsPage.applyFilters()">
          <select id="inc-status" class="input" onchange="window.incidentsPage.applyFilters()">
            <option value="ALL">All Statuses</option>
            <option value="NEW">New</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="VERIFIED">Verified</option>
            <option value="ASSIGNED">Assigned</option>
            <option value="RESPONDING">Responding</option>
            <option value="RESOLVED">Resolved</option>
            <option value="FALSE_POSITIVE">False Positive</option>
          </select>
          <select id="inc-severity" class="input" onchange="window.incidentsPage.applyFilters()">
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
        
        <div class="card">
          <div class="table-responsive">
            <table class="table" style="width:100%;text-align:left;">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Camera</th>
                  <th>Location</th>
                  <th>Risk Score</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="incidents-tbody">
                <tr><td colspan="9" style="text-align:center;">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <!-- Incident Detail Modal -->
      <div id="incident-modal" class="modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center;">
        <div class="modal-content card" style="width:90%;max-width:900px;max-height:90vh;overflow-y:auto;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;border-bottom:1px solid #2d3748;padding-bottom:12px;">
            <h2 style="margin:0;">Incident Detail <span id="modal-inc-id" style="font-size:16px;color:#a0aec0;font-family:monospace;margin-left:12px;"></span></h2>
            <button class="btn" onclick="document.getElementById('incident-modal').style.display='none'">✕ Close</button>
          </div>
          
          <div class="tabs" style="display:flex;gap:16px;margin-bottom:20px;border-bottom:1px solid #2d3748;">
            <button class="tab-btn active" onclick="window.incidentsPage.switchTab('overview')">Overview</button>
            <button class="tab-btn" onclick="window.incidentsPage.switchTab('evidence')">Evidence</button>
            <button class="tab-btn" onclick="window.incidentsPage.switchTab('history')">History</button>
            <button class="tab-btn" onclick="window.incidentsPage.switchTab('assignment')">Assignment</button>
          </div>
          
          <div id="tab-overview" class="tab-content" style="display:block;">
            <div class="ai-disclaimer" style="background:rgba(99,179,237,0.1);border:1px solid #63b3ed;color:#63b3ed;padding:12px;border-radius:6px;margin-bottom:20px;">
              <strong>AI Disclaimer:</strong> This system uses AI to detect incidents. Ensure verification.
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:24px;">
              <div>
                <p><strong>Type:</strong> <span id="det-type"></span></p>
                <p><strong>Severity:</strong> <span id="det-sev"></span></p>
                <p><strong>Status:</strong> <span id="det-status"></span></p>
                <p><strong>Risk Score:</strong> <span id="det-risk"></span></p>
              </div>
              <div>
                <p><strong>Camera:</strong> <span id="det-cam"></span></p>
                <p><strong>Location:</strong> <span id="det-loc"></span></p>
                <p><strong>Created:</strong> <span id="det-created"></span></p>
                <p><strong>AI Confidence:</strong> <span id="det-conf"></span></p>
              </div>
            </div>
            <div>
              <strong>Description:</strong>
              <p id="det-desc" style="background:#1a202c;padding:12px;border-radius:4px;"></p>
            </div>
            
            <div id="action-buttons" style="margin-top:24px;display:flex;gap:12px;border-top:1px solid #2d3748;padding-top:16px;">
              <!-- Dynamically populated -->
            </div>
          </div>
          
          <div id="tab-evidence" class="tab-content" style="display:none;">
            <div id="evidence-gallery" style="padding:16px;">
              <p style="color:#a0aec0;text-align:center;">Loading evidence...</p>
            </div>
          </div>
          
          <div id="tab-history" class="tab-content" style="display:none;">
            <ul id="history-list" style="list-style:none;padding:0;margin:0;"></ul>
          </div>
          
          <div id="tab-assignment" class="tab-content" style="display:none;">
            <div id="assignment-current"></div>
            <hr style="border:1px solid #2d3748;margin:24px 0;">
            <h3>Available Responders</h3>
            <button class="btn btn-primary" style="margin-bottom:16px;" onclick="window.incidentsPage.findNearest()">Find Nearest Available Responders</button>
            <div id="assignment-list"></div>
          </div>
        </div>
      </div>
    `;
  },
  
  async init() {
    await this.loadData();
    // Check if incident ID in hash
    const match = window.location.hash.match(/#\/incidents\/(.+)/);
    if (match && match[1]) {
      this.openDetail(match[1]);
    }
  },
  
  async loadData() {
    try {
      this._incidents = await window.api.getIncidents({limit: 100, sort: 'created_at', order: 'desc'});
      this.applyFilters();
    } catch(e) {
      console.error(e);
      if(window.showErrorToast) window.showErrorToast('Failed to load incidents');
    }
  },
  
  applyFilters() {
    const term = (document.getElementById('inc-search')?.value || '').toLowerCase();
    const status = document.getElementById('inc-status')?.value || 'ALL';
    const sev = document.getElementById('inc-severity')?.value || 'ALL';
    
    const filtered = this._incidents.filter(i => {
      const matchTerm = (i.id.toLowerCase().includes(term) || (i.location||'').toLowerCase().includes(term));
      const matchStatus = status === 'ALL' || i.status === status;
      const matchSev = sev === 'ALL' || i.severity === sev;
      return matchTerm && matchStatus && matchSev;
    });
    
    const tbody = document.getElementById('incidents-tbody');
    if (!tbody) return;
    
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;">No incidents found</td></tr>`;
      return;
    }
    
    tbody.innerHTML = filtered.map(inc => `
      <tr>
        <td style="font-family:monospace">${inc.id.substring(0,8)}</td>
        <td>${incidentTypeIcon(inc.type)} ${inc.type}</td>
        <td>${severityBadge(inc.severity)}</td>
        <td>${inc.camera_name || inc.camera_id}</td>
        <td>${inc.location || '—'}</td>
        <td>${riskBar(inc.risk_score || 0, inc.severity)}</td>
        <td>${statusBadge(inc.status)}</td>
        <td>${new Date(inc.created_at).toLocaleString()}</td>
        <td>
          <button class="btn btn-sm" onclick="window.incidentsPage.openDetail('${inc.id}')">View</button>
        </td>
      </tr>
    `).join('');
  },
  
  async openDetail(id) {
    const inc = this._incidents.find(i => i.id === id);
    if (!inc) return;
    this._currentIncident = inc;
    
    document.getElementById('modal-inc-id').innerText = '#' + inc.id;
    document.getElementById('det-type').innerHTML = `${incidentTypeIcon(inc.type)} ${inc.type}`;
    document.getElementById('det-sev').innerHTML = severityBadge(inc.severity);
    document.getElementById('det-status').innerHTML = statusBadge(inc.status);
    document.getElementById('det-risk').innerHTML = `${Math.round(inc.risk_score||0)}%`;
    document.getElementById('det-cam').innerText = inc.camera_name || inc.camera_id;
    document.getElementById('det-loc').innerText = inc.location || 'Unknown';
    document.getElementById('det-created').innerText = new Date(inc.created_at).toLocaleString();
    document.getElementById('det-conf').innerText = inc.ai_confidence ? `${Math.round(inc.ai_confidence*100)}%` : 'N/A';
    document.getElementById('det-desc').innerText = inc.description || 'No description available.';
    
    // Load evidence asynchronously
    window.api.get(`/api/evidence/${id}`)
      .then(evList => {
        const gallery = document.getElementById('evidence-gallery');
        if (!gallery) return;
        if (!evList || evList.length === 0) {
          gallery.innerHTML = '<p style="color:#a0aec0;text-align:center;padding:40px 0;">📁 No evidence captured yet for this incident.</p>';
          return;
        }
        gallery.innerHTML = evList.map(ev => {
          const isImage = ev.evidence_type === 'SNAPSHOT' && ev.file_url;
          return `
            <div style="margin-bottom:20px;background:#1a202c;border-radius:8px;padding:16px;">
              <div style="font-size:12px;color:#a0aec0;margin-bottom:8px;">
                ${ev.evidence_type || 'FILE'} &nbsp;·&nbsp; ${ev.file_name || 'unknown'} &nbsp;·&nbsp; ${ev.file_size ? (ev.file_size/1024).toFixed(1)+' KB' : ''} &nbsp;·&nbsp; ${ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}
              </div>
              ${isImage ? `
                <img src="${ev.file_url}" alt="Evidence snapshot"
                  style="max-width:100%;max-height:380px;border-radius:6px;cursor:pointer;display:block;margin:0 auto;"
                  onclick="window.open('${ev.file_url}','_blank')"
                  onerror="this.outerHTML='<p style=\'color:#a0aec0;\'>Image not available on disk</p>'">
                <div style="margin-top:10px;text-align:center;">
                  <a href="${ev.file_url}" download class="btn btn-sm btn-primary">⬇ Download JPEG</a>
                </div>
              ` : `
                <p style="color:#a0aec0;">📄 ${ev.file_name || 'Evidence file'} (${ev.evidence_type})</p>
                <a href="/api/evidence/file/${ev.id}" target="_blank" class="btn btn-sm">Open File</a>
              `}
            </div>
          `;
        }).join('');
      })
      .catch(() => {
        const gallery = document.getElementById('evidence-gallery');
        if (gallery) gallery.innerHTML = '<p style="color:#fc4545;text-align:center;">Failed to load evidence.</p>';
      });
    
    // Actions
    const actions = document.getElementById('action-buttons');
    actions.innerHTML = '';
    if (inc.status === 'NEW') {
      actions.innerHTML = `<button class="btn btn-primary" onclick="window.incidentsPage.updateStatus('${inc.id}', 'UNDER_REVIEW')">Mark Under Review</button>`;
    } else if (inc.status === 'UNDER_REVIEW') {
      actions.innerHTML = `
        <button class="btn btn-primary" onclick="window.incidentsPage.verifyIncident('${inc.id}')">Verify Incident</button>
        <button class="btn" style="color:#fc4545;" onclick="window.incidentsPage.rejectIncident('${inc.id}')">Mark as False Positive</button>
      `;
    } else if (inc.status === 'VERIFIED') {
      actions.innerHTML = `<button class="btn btn-primary" onclick="window.incidentsPage.switchTab('assignment')">Find & Assign Nearest Responder</button>`;
    } else if (inc.status === 'RESOLVED') {
      actions.innerHTML = `<span>Resolved. Resolution notes available in history.</span>`;
    }
    
    this.switchTab('overview');
    document.getElementById('incident-modal').style.display = 'flex';
    
    // Load history
    try {
      const history = await window.api.getIncidentHistory(id);
      document.getElementById('history-list').innerHTML = history.map(h => `
        <li style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #2d3748;">
          <div style="font-size:12px;color:#a0aec0;">${new Date(h.timestamp).toLocaleString()}</div>
          <div>Changed to <strong>${h.to_status}</strong> by ${h.changed_by}</div>
          ${h.notes ? `<div style="font-size:13px;margin-top:4px;color:#cbd5e0;">${h.notes}</div>` : ''}
        </li>
      `).join('');
    } catch(e) {
      document.getElementById('history-list').innerHTML = '<li>Failed to load history</li>';
    }
  },
  
  switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).style.display = 'block';
    event.currentTarget.classList.add('active');
  },
  
  async updateStatus(id, newStatus) {
    try {
      await window.api.updateIncidentStatus(id, newStatus, 'Status updated via dashboard');
      if(window.showSuccessToast) window.showSuccessToast(`Status updated to ${newStatus}`);
      await this.loadData();
      this.openDetail(id);
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to update status');
    }
  },
  
  async verifyIncident(id) {
    try {
      await window.api.verifyIncident(id);
      if(window.showSuccessToast) window.showSuccessToast('Incident verified');
      await this.loadData();
      this.openDetail(id);
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to verify incident');
    }
  },
  
  async rejectIncident(id) {
    const reason = prompt('Enter reason for false positive:');
    if (reason === null) return;
    try {
      await window.api.rejectIncident(id, reason || 'Marked false positive by operator');
      if(window.showSuccessToast) window.showSuccessToast('Marked as false positive');
      await this.loadData();
      this.openDetail(id);
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to update incident');
    }
  },
  
  async findNearest() {
    if (!this._currentIncident) return;
    try {
      const responders = await window.api.getNearestResponders(this._currentIncident.latitude, this._currentIncident.longitude);
      const list = document.getElementById('assignment-list');
      if (!responders || responders.length === 0) {
        list.innerHTML = '<p>No available responders found.</p>';
        return;
      }
      list.innerHTML = responders.map(r => `
        <div class="card" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding:12px;">
          <div>
            <strong>👮 ${r.name}</strong> (${r.role})<br>
            <span style="font-size:13px;color:#a0aec0;">Distance: ${(r.distance || 0).toFixed(2)} km | Station: ${r.station}</span>
          </div>
          <button class="btn btn-primary" onclick="window.incidentsPage.assignResponder('${this._currentIncident.id}', '${r.id}')">Assign</button>
        </div>
      `).join('');
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to fetch responders');
    }
  },
  
  async assignResponder(incidentId, responderId) {
    try {
      await window.api.assignIncident(incidentId, responderId);
      if(window.showSuccessToast) window.showSuccessToast('Responder assigned successfully');
      await this.loadData();
      this.openDetail(incidentId);
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to assign responder');
    }
  },
  
  async createTestIncident() {
    try {
      await window.api.createIncident({
        type: 'LOITERING', severity: 'MEDIUM', risk_score: 65,
        camera_id: 'CAM-001', location: 'Main Entrance',
        latitude: 28.6139, longitude: 77.2090,
        description: 'Test incident generated by operator'
      });
      if(window.showSuccessToast) window.showSuccessToast('Test incident created');
      await this.loadData();
    } catch(e) {
      if(window.showErrorToast) window.showErrorToast('Failed to create test incident');
    }
  }
};

window.incidentsPage = incidentsPage;
