/**
 * AegisWatch — Modal Component
 */

const modal = {
  _stack: [],

  open(options = {}) {
    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-container');
    const titleEl = document.getElementById('modal-title');
    const bodyEl  = document.getElementById('modal-body');
    const footerEl = document.getElementById('modal-footer');

    if (!overlay) return;

    titleEl.textContent  = options.title  || '';
    bodyEl.innerHTML     = options.body   || '';
    footerEl.innerHTML   = '';

    // Size
    container.className = 'modal-container glass-card';
    if (options.size === 'lg') container.classList.add('modal-lg');
    if (options.size === 'sm') container.classList.add('modal-sm');

    // Footer buttons
    if (options.buttons && options.buttons.length) {
      options.buttons.forEach(btn => {
        const b = document.createElement('button');
        b.className = `btn ${btn.class || 'btn-secondary'}`;
        b.textContent = btn.label;
        b.id = btn.id || '';
        b.addEventListener('click', () => {
          if (btn.onClick) btn.onClick();
          if (btn.close !== false) modal.close();
        });
        footerEl.appendChild(b);
      });
    }

    overlay.classList.remove('hidden');
    overlay.style.display = 'flex';
    this._stack.push(options);

    // Wire close button
    document.getElementById('modal-close').onclick = () => modal.close();
    overlay.onclick = (e) => { if (e.target === overlay) modal.close(); };

    // Run onOpen callback
    if (options.onOpen) setTimeout(() => options.onOpen(bodyEl), 50);

    return bodyEl;
  },

  close() {
    const overlay = document.getElementById('modal-overlay');
    if (!overlay) return;
    overlay.classList.add('hidden');
    overlay.style.display = '';
    const opts = this._stack.pop();
    if (opts && opts.onClose) opts.onClose();
  },

  confirm(title, message, onConfirm, danger = false) {
    this.open({
      title,
      size: 'sm',
      body: `
        <div class="confirm-dialog">
          <div class="confirm-icon">${danger ? '⚠️' : '❓'}</div>
          <div class="confirm-title">${title}</div>
          <div class="confirm-message">${message}</div>
        </div>
      `,
      buttons: [
        { label: 'Cancel', class: 'btn-secondary' },
        {
          label: 'Confirm',
          class: danger ? 'btn-danger' : 'btn-primary',
          close: false,
          onClick: async () => {
            await onConfirm();
            modal.close();
          }
        }
      ]
    });
  },

  showLoading(title = 'Processing...') {
    this.open({
      title,
      size: 'sm',
      body: `<div class="loading-screen"><div class="spinner-large"></div><p>${title}</p></div>`,
      buttons: []
    });
  }
};

window.modal = modal;
