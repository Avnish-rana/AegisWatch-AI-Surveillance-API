/**
 * AegisWatch — Main Application Router & Bootstrap
 */

// ── Utility helpers (available globally) ──────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
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
  const s = (status || '').toLowerCase();
  return `<span class="badge status-${s}">${(status || '').replace(/_/g, ' ')}</span>`;
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
  return `<div class="risk-bar-container">
    <div class="risk-bar"><div class="risk-bar-fill ${s}" style="width:${score}%"></div></div>
    <span class="text-xs" style="min-width:35px">${Math.round(score)}%</span>
  </div>`;
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Make available globally
Object.assign(window, { formatDate, formatRelative, severityBadge, statusBadge, incidentTypeIcon, riskBar, escapeHtml });

// ── Router ──────────────────────────────────────────────────────────────────
const routes = {
  '/dashboard':  () => window.dashboardPage,
  '/cameras':    () => window.camerasPage,
  '/incidents':  () => window.incidentsPage,
  '/incidents/:id': () => window.incidentsPage,
  '/responders': () => window.respondersPage,
  '/analytics':  () => window.analyticsPage,
  '/map':        () => window.mapPage,
  '/live':       () => window.livePage,
  '/zones':      () => window.zonesPage,
  '/surveillance': () => window.surveillancePage,
};

const pageTitles = {
  dashboard: 'Dashboard',
  cameras: 'Camera Management',
  incidents: 'Incident Management',
  map: 'Live Surveillance Map',
  live: 'Live Feeds',
  responders: 'Responder Management',
  analytics: 'Analytics & Reports',
  zones: 'Zone Management',
  surveillance: 'AI Surveillance — Live & Video Analysis',
};

let _currentPage = null;
let _currentUser = null;

function getPage() {
  const hash = window.location.hash.replace('#/', '') || 'dashboard';
  const [page, param] = hash.split('/');
  return { page, param };
}

function getPageModule(page) {
  const key = `/${page}`;
  const factory = routes[key];
  return factory ? factory() : null;
}

async function navigate(page, param = null) {
  const mod = getPageModule(page);
  if (!mod) {
    page = 'dashboard';
    return navigate(page);
  }

  // Destroy current page
  if (_currentPage && _currentPage.destroy) {
    try { _currentPage.destroy(); } catch(e) {}
  }

  // Update active nav
  sidebar.setActivePage(page);

  // Update page title
  const title = pageTitles[page] || 'AegisWatch';
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-breadcrumb').textContent = `Home / ${title}`;
  document.title = `${title} — AegisWatch`;

  // Show loading
  const content = document.getElementById('page-content');
  content.innerHTML = `<div class="loading-screen"><div class="spinner-large"></div><p>Loading ${title}...</p></div>`;

  try {
    // Render page HTML
    const html = await mod.render(param);
    content.innerHTML = html;
    content.classList.add('fade-in');

    // Initialize page
    if (mod.init) await mod.init(param);

    _currentPage = mod;
  } catch (err) {
    console.error('[Router]', err);
    content.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <h3>Page Error</h3>
        <p>${escapeHtml(err.message)}</p>
        <button class="btn btn-primary mt-4" onclick="navigate('dashboard')">Return to Dashboard</button>
      </div>
    `;
  }
}

// ── Clock ────────────────────────────────────────────────────────────────────
function startClock() {
  function update() {
    const el = document.getElementById('topbar-time');
    if (el) {
      el.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  }
  update();
  setInterval(update, 1000);
}

// ── Auth flow ────────────────────────────────────────────────────────────────
async function checkAuth() {
  const token = api.getToken();
  if (!token) {
    showLogin();
    return false;
  }
  try {
    const user = await api.me();
    _currentUser = user;
    window.currentUser = user;
    sidebar.setUser(user);
    return true;
  } catch(e) {
    api.setToken(null);
    showLogin();
    return false;
  }
}

function showLogin() {
  document.getElementById('login-overlay').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');
}

function showApp() {
  document.getElementById('login-overlay').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
}

// ── Initialization ───────────────────────────────────────────────────────────
async function initApp() {
  // Sidebar
  sidebar.init();

  // Clock
  startClock();

  // Login form
  const loginForm = document.getElementById('login-form');
  const loginError = document.getElementById('login-error');

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const spinner = btn.querySelector('.btn-spinner');
    const text    = btn.querySelector('.btn-text');
    
    btn.disabled = true;
    spinner.classList.remove('hidden');
    text.classList.add('hidden');
    loginError.classList.add('hidden');

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      const data = await api.login(username, password);
      _currentUser = data.user || { username, role: 'OPERATOR' };
      window.currentUser = _currentUser;
      sidebar.setUser(_currentUser);
      showApp();
      ws.connect();
      
      // Navigate to initial route
      const { page, param } = getPage();
      await navigate(page || 'dashboard', param);
    } catch(err) {
      loginError.textContent = err.message || 'Invalid credentials. Try: admin / admin123';
      loginError.classList.remove('hidden');
    } finally {
      btn.disabled = false;
      spinner.classList.add('hidden');
      text.classList.remove('hidden');
    }
  });

  // Logout
  document.getElementById('logout-btn').addEventListener('click', () => {
    modal.confirm('Sign Out', 'Are you sure you want to sign out?', async () => {
      ws.disconnect();
      api.logout();
      showLogin();
    });
  });

  // Hash-based routing
  window.addEventListener('hashchange', () => {
    if (!api.getToken()) return;
    const { page, param } = getPage();
    navigate(page || 'dashboard', param);
  });

  // Auth logout event
  window.addEventListener('auth:logout', () => showLogin());

  // Check auth
  const authed = await checkAuth();
  if (authed) {
    showApp();
    ws.connect();
    
    // WebSocket events
    ws.on('incident_alert', (data) => {
      // Refresh active page if it's incidents or dashboard
      const { page } = getPage();
      if (page === 'incidents' && _currentPage?.loadData) {
        _currentPage.loadData();
      }
    });

    ws.on('incident_update', (data) => {
      const { page } = getPage();
      if (['incidents', 'dashboard'].includes(page) && _currentPage?.loadData) {
        _currentPage.loadData();
      }
    });

    // Navigate to initial route
    const { page, param } = getPage();
    await navigate(page || 'dashboard', param);
  } else {
    showLogin();
  }
}

// ── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initApp);

// Also expose navigate globally for use in page templates
window.navigate = navigate;
