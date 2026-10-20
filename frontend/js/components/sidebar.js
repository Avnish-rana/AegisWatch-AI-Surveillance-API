/**
 * AegisWatch — Sidebar Component
 */

const sidebar = {
  _collapsed: false,

  init() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggle());
    }

    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      });
    });
  },

  toggle() {
    this._collapsed = !this._collapsed;
    document.getElementById('app')?.classList.toggle('sidebar-collapsed', this._collapsed);
  },

  setActivePage(page) {
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });
  },

  setUser(user) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role-badge');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.textContent = user.username || user.name || 'User';
    if (roleEl) {
      roleEl.textContent = user.role || 'USER';
      roleEl.className = `badge badge-${user.role === 'ADMIN' ? 'danger' : user.role === 'OPERATOR' ? 'info' : 'success'}`;
    }
    if (avatarEl) avatarEl.textContent = (user.username || 'U')[0].toUpperCase();
  }
};

window.sidebar = sidebar;
