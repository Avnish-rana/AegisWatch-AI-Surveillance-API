/**
 * AegisWatch — WebSocket Client
 * Real-time incident alerts and notifications via WebSocket
 */

class AegisWebSocket {
  constructor() {
    this._ws = null;
    this._clientId = `browser-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    this._handlers = {};
    this._reconnectAttempts = 0;
    this._maxReconnects = 20;
    this._reconnectDelay = 2000;
    this._connected = false;
    this._intentionalClose = false;
  }

  connect() {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) return;
    
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/${this._clientId}`;
    
    this._updateStatus('connecting');
    
    try {
      this._ws = new WebSocket(url);
    } catch (e) {
      console.warn('[WS] Failed to create WebSocket:', e);
      this._scheduleReconnect();
      return;
    }

    this._ws.onopen = () => {
      console.log('[WS] Connected');
      this._connected = true;
      this._reconnectAttempts = 0;
      this._reconnectDelay = 2000;
      this._updateStatus('connected');
      this._emit('connected');
    };

    this._ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._handleMessage(msg);
      } catch (e) {
        console.warn('[WS] Invalid message:', event.data);
      }
    };

    this._ws.onclose = (event) => {
      this._connected = false;
      this._updateStatus('disconnected');
      
      if (!this._intentionalClose) {
        console.warn('[WS] Connection closed. Code:', event.code, 'Reconnecting...');
        this._scheduleReconnect();
      }
    };

    this._ws.onerror = (error) => {
      console.warn('[WS] Error:', error);
      this._updateStatus('disconnected');
    };
  }

  disconnect() {
    this._intentionalClose = true;
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  _scheduleReconnect() {
    if (this._reconnectAttempts >= this._maxReconnects) {
      console.warn('[WS] Max reconnect attempts reached.');
      return;
    }
    this._reconnectAttempts++;
    const delay = Math.min(this._reconnectDelay * this._reconnectAttempts, 30000);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  _handleMessage(msg) {
    const { type, data } = msg;
    
    switch (type) {
      case 'incident_alert':
        this._emit('incident_alert', data);
        this._showIncidentToast(data);
        this._updateIncidentBadge();
        break;
      case 'incident_update':
        this._emit('incident_update', data);
        break;
      case 'camera_status':
        this._emit('camera_status', data);
        break;
      case 'ping':
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
          this._ws.send(JSON.stringify({ type: 'pong' }));
        }
        break;
      default:
        this._emit(type, data);
    }
  }

  _showIncidentToast(incident) {
    if (window.showAlertToast) {
      const severity = (incident.severity || 'medium').toLowerCase();
      const title = `🚨 ${incident.severity || 'ALERT'} — ${incident.incident_type || 'INCIDENT'}`;
      const message = `${incident.location_name || 'Unknown location'} • Risk: ${Math.round(incident.risk_score || 0)}%`;
      
      window.showAlertToast({
        title,
        message,
        severity,
        incidentId: incident.id || incident.incident_id,
        actions: [
          {
            label: 'View',
            class: 'btn-primary btn-sm',
            onClick: () => {
              window.location.hash = `#/incidents/${incident.id || incident.incident_id}`;
            }
          }
        ]
      });
    }
  }

  _updateIncidentBadge() {
    api.getAnalyticsSummary().then(data => {
      const badge = document.getElementById('incident-badge');
      const count = document.getElementById('notif-count');
      if (badge && data.active_incidents > 0) {
        badge.textContent = data.active_incidents;
        badge.style.display = 'flex';
      }
      if (count) {
        count.textContent = data.active_incidents || 0;
        count.classList.toggle('hidden', !data.active_incidents);
      }
    }).catch(() => {});
  }

  _updateStatus(status) {
    const dot = document.getElementById('ws-status-dot');
    const text = document.getElementById('ws-status-text');
    if (!dot || !text) return;

    dot.className = 'status-dot';
    if (status === 'connected')    { dot.classList.add(''); text.textContent = 'System Online'; }
    if (status === 'connecting')   { dot.classList.add('connecting'); text.textContent = 'Connecting...'; }
    if (status === 'disconnected') { dot.classList.add('disconnected'); text.textContent = 'Disconnected'; }
  }

  on(event, handler) {
    if (!this._handlers[event]) this._handlers[event] = [];
    this._handlers[event].push(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (!this._handlers[event]) return;
    this._handlers[event] = this._handlers[event].filter(h => h !== handler);
  }

  _emit(event, data) {
    (this._handlers[event] || []).forEach(h => {
      try { h(data); } catch (e) { console.error('[WS] Handler error:', e); }
    });
  }

  get connected() { return this._connected; }
}

// Global singleton
const ws = new AegisWebSocket();
window.aegisWS = ws;
