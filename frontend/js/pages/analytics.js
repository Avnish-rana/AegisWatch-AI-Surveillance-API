const analyticsPage = {
  _charts: {},
  
  async render() {
    return `
      <div class="fade-in">
        <h2 style="margin-bottom:24px;">Analytics</h2>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
          <div class="card">
            <h3 style="margin-top:0;">Incidents by Type</h3>
            <canvas id="chart-type" height="250"></canvas>
          </div>
          <div class="card">
            <h3 style="margin-top:0;">Incidents Last 24 Hours</h3>
            <canvas id="chart-time" height="250"></canvas>
          </div>
          <div class="card">
            <h3 style="margin-top:0;">Severity Distribution</h3>
            <canvas id="chart-severity" height="250"></canvas>
          </div>
          <div class="card">
            <h3 style="margin-top:0;">Top Cameras by Incidents</h3>
            <canvas id="chart-cameras" height="250"></canvas>
          </div>
        </div>
      </div>
    `;
  },
  
  async init() {
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js not loaded. Dynamically loading...');
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
      script.onload = () => this.setupCharts();
      document.head.appendChild(script);
    } else {
      this.setupCharts();
    }
  },
  
  async setupCharts() {
    // Global defaults for dark theme
    Chart.defaults.color = '#8fa3bf';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
    Chart.defaults.font.family = 'Inter, sans-serif';
    
    try {
      const [typeData, timeData, sevData, camData] = await Promise.all([
        window.api.getIncidentsByType().catch(() => []),
        window.api.getIncidentsByHour().catch(() => []),
        window.api.getSeverityDistribution().catch(() => []),
        window.api.getIncidentsByCamera().catch(() => [])
      ]);
      
      this.renderTypeChart(typeData);
      this.renderTimeChart(timeData);
      this.renderSeverityChart(sevData);
      this.renderCameraChart(camData);
    } catch(e) {
      console.error('Failed to load chart data', e);
    }
  },
  
  _destroyChart(id) {
    if (this._charts[id]) {
      this._charts[id].destroy();
    }
  },
  
  renderTypeChart(data) {
    this._destroyChart('type');
    const ctx = document.getElementById('chart-type');
    if (!ctx) return;
    
    const colors = {
      FIGHT: '#fc4545', THEFT: '#f6ad55', INTRUSION: '#63b3ed',
      LOITERING: '#9f7aea', ABANDONED_OBJECT: '#68d391', SUSPICIOUS_MOVEMENT: '#fbbf24'
    };
    
    this._charts['type'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(d => d.type),
        datasets: [{
          data: data.map(d => d.count),
          backgroundColor: data.map(d => colors[d.type] || '#a0aec0'),
          borderWidth: 0
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
    });
  },
  
  renderTimeChart(data) {
    this._destroyChart('time');
    const ctx = document.getElementById('chart-time');
    if (!ctx) return;
    
    this._charts['time'] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(d => d.hour + ':00'),
        datasets: [{
          label: 'Incidents',
          data: data.map(d => d.count),
          borderColor: '#63b3ed',
          backgroundColor: 'rgba(99,179,237,0.2)',
          fill: true,
          tension: 0.4
        }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
  },
  
  renderSeverityChart(data) {
    this._destroyChart('severity');
    const ctx = document.getElementById('chart-severity');
    if (!ctx) return;
    
    const colors = { CRITICAL: '#fc4545', HIGH: '#f6ad55', MEDIUM: '#fbbf24', LOW: '#68d391' };
    
    this._charts['severity'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.severity),
        datasets: [{
          label: 'Count',
          data: data.map(d => d.count),
          backgroundColor: data.map(d => colors[d.severity] || '#a0aec0')
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
  },
  
  renderCameraChart(data) {
    this._destroyChart('cameras');
    const ctx = document.getElementById('chart-cameras');
    if (!ctx) return;
    
    // Top 5
    const topData = data.slice(0, 5);
    
    this._charts['cameras'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: topData.map(d => d.camera_id),
        datasets: [{
          label: 'Incidents',
          data: topData.map(d => d.count),
          backgroundColor: '#9f7aea'
        }]
      },
      options: { 
        indexAxis: 'y',
        responsive: true, 
        maintainAspectRatio: false, 
        plugins: { legend: { display: false } } 
      }
    });
  },
  
  destroy() {
    Object.keys(this._charts).forEach(k => this._destroyChart(k));
  }
};

window.analyticsPage = analyticsPage;
