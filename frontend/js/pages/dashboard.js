// Helper functions
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function formatRelative(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function severityBadge(severity) {
  const s = (severity || '').toLowerCase();
  return `<span class="badge badge-${s}">${severity || 'UNKNOWN'}</span>`;
}

function statusBadge(status) {
  const s = (status || '').toLowerCase().replace(' ', '_');
  return `<span class="badge status-${s}">${(status || '').replace('_', ' ')}</span>`;
}

function incidentTypeIcon(type) {
  const icons = {
    FIGHT: '👊', THEFT: '💼', INTRUSION: '🚫',
    LOITERING: '⏱️', ABANDONED_OBJECT: '🎒',
    SUSPICIOUS_MOVEMENT: '🏃', WEAPON_DETECTED: '🔫'
  };
  return icons[type] || '⚠️';
}

function riskBar(score, severity) {
  const s = (severity || 'low').toLowerCase();
  return `<div class="risk-bar-container" style="display:flex;align-items:center;gap:8px;">
    <div class="risk-bar" style="flex:1;height:6px;background:#2d3748;border-radius:3px;overflow:hidden;">
      <div class="risk-bar-fill ${s}" style="width:${score}%;height:100%;background:var(--color-${s});"></div>
    </div>
    <span class="text-xs" style="min-width:35px">${Math.round(score)}%</span>
  </div>`;
}

const dashboardPage = {
  _refreshTimer: null,
  
  async render() {
    return `
      <div class="fade-in">
        <div class="ai-disclaimer" style="background:rgba(99,179,237,0.1);border:1px solid #63b3ed;color:#63b3ed;padding:12px;border-radius:6px;margin-bottom:24px;">
          <strong>AI Disclaimer:</strong> This system uses AI to detect incidents. All detections should be verified by human operators.
        </div>
        
        <div class="stats-grid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:20px;margin-bottom:32px;">
          <div class="stat-card">
            <div class="stat-icon">📷</div>
            <div class="stat-label">Total Cameras</div>
            <div class="stat-value" id="stat-total-cameras">-</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="color:#68d391">🟢</div>
            <div class="stat-label">Online Cameras</div>
            <div class="stat-value" id="stat-online-cameras">-</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="color:#fc4545">🚨</div>
            <div class="stat-label">Active Incidents</div>
            <div class="stat-value" id="stat-active-incidents">-</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📅</div>
            <div class="stat-label">Today's Incidents</div>
            <div class="stat-value" id="stat-today">-</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="color:#fc4545">🔥</div>
            <div class="stat-label">High-Risk Incidents</div>
            <div class="stat-value" id="stat-high-risk">-</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="color:#68d391">✅</div>
            <div class="stat-label">Resolved Today</div>
            <div class="stat-value" id="stat-resolved">-</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:3fr 1fr;gap:24px;">
          <div class="card">
            <h3 style="margin-top:0;margin-bottom:16px;">Recent Incidents</h3>
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
                  </tr>
                </thead>
                <tbody id="dashboard-incidents-tbody">
                  <tr><td colspan="8" style="text-align:center;">Loading...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <div class="card">
            <h3 style="margin-top:0;margin-bottom:16px;">System Status</h3>
            <div id="system-status-container">
              <div class="status-item" style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span id="status-api" style="color:#68d391">●</span> <span>Backend API</span>
              </div>
              <div class="status-item" style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span id="status-db" style="color:#68d391">●</span> <span>Database</span>
              </div>
              <div class="status-item" style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span id="status-ai" style="color:#68d391">●</span> <span>AI Engine</span>
              </div>
              <div class="status-item" style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span id="status-ws" style="color:#68d391">●</span> <span>WebSocket</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },
  
  async init() {
    await this.loadData();
    this.checkHealth();
    this._refreshTimer = setInterval(() => {
      this.loadData();
      this.checkHealth();
    }, 30000);
  },
  
  async loadData() {
    try {
      if (window.api && window.api.getAnalyticsSummary) {
        const summary = await window.api.getAnalyticsSummary();
        this._renderStats(summary);
      }
      
      if (window.api && window.api.getIncidents) {
        const incidents = await window.api.getIncidents({limit: 10, sort: 'created_at', order: 'desc'});
        this._renderIncidents(incidents);
      }
    } catch(e) {
      console.error('Failed to load dashboard data:', e);
    }
  },
  
  async checkHealth() {
    try {
      const res = await fetch('/api/health');
      const health = await res.json();
      document.getElementById('status-api').style.color = health.api === 'ok' ? '#68d391' : '#fc4545';
      document.getElementById('status-db').style.color = health.db === 'ok' ? '#68d391' : '#fc4545';
      document.getElementById('status-ai').style.color = health.ai === 'ok' ? '#68d391' : '#fc4545';
    } catch(e) {
      ['status-api', 'status-db', 'status-ai'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.style.color = '#fc4545';
      });
    }
    
    if (window.ws) {
      const wsStatus = document.getElementById('status-ws');
      if(wsStatus) wsStatus.style.color = window.ws.connected ? '#68d391' : '#fc4545';
    }
  },
  
  _renderStats(data) {
    if (!data) return;
    const s = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    s('stat-total-cameras', data.totalCameras || 0);
    s('stat-online-cameras', data.onlineCameras || 0);
    s('stat-active-incidents', data.activeIncidents || 0);
    s('stat-today', data.incidentsToday || 0);
    s('stat-high-risk', data.highRiskIncidents || 0);
    s('stat-resolved', data.resolvedToday || 0);
  },

  _renderIncidents(incidents) {
    const tbody = document.getElementById('dashboard-incidents-tbody');
    if (!tbody) return;
    if (!incidents || incidents.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">No recent incidents</td></tr>`;
      return;
    }
    
    tbody.innerHTML = incidents.map(inc => `
      <tr style="cursor:pointer;" onclick="window.location.hash='#/incidents/${inc.id}'">
        <td>#${inc.id.substring(0,8)}</td>
        <td>${incidentTypeIcon(inc.type)} ${inc.type}</td>
        <td>${severityBadge(inc.severity)}</td>
        <td>${inc.camera_name || inc.camera_id}</td>
        <td>${inc.location || '—'}</td>
        <td>${riskBar(inc.risk_score || 0, inc.severity)}</td>
        <td>${statusBadge(inc.status)}</td>
        <td>${formatRelative(inc.created_at)}</td>
      </tr>
    `).join('');
  },

  destroy() {
    clearInterval(this._refreshTimer);
  }
};

window.dashboardPage = dashboardPage;
