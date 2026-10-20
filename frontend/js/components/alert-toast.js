/**
 * AegisWatch — Alert Toast Component
 * Real-time floating notifications
 */

const TOAST_DURATION = 8000;
const MAX_TOASTS = 5;
let _toastQueue = [];

function showAlertToast({ title, message, severity = 'info', actions = [], duration = TOAST_DURATION, incidentId = null }) {
  const container = document.getElementById('alert-container');
  if (!container) return;

  // Limit concurrent toasts
  if (_toastQueue.length >= MAX_TOASTS) {
    const oldest = _toastQueue.shift();
    oldest?.remove();
  }

  const toast = document.createElement('div');
  toast.className = `alert-toast ${severity}`;
  toast.setAttribute('role', 'alert');

  const severityEmoji = {
    critical: '🚨',
    high: '⚠️',
    medium: '🔔',
    low: 'ℹ️',
    info: 'ℹ️',
    success: '✅',
  }[severity] || '🔔';

  const actionsHtml = actions.map((action, i) => 
    `<button class="btn ${action.class || 'btn-secondary btn-sm'}" data-action-idx="${i}">${action.label}</button>`
  ).join('');

  toast.innerHTML = `
    <div class="toast-header">
      <div class="toast-title">
        <span>${severityEmoji}</span>
        <span>${title}</span>
      </div>
      <button class="toast-close" aria-label="Dismiss">✕</button>
    </div>
    <div class="toast-body">${message}</div>
    ${actionsHtml ? `<div class="toast-actions">${actionsHtml}</div>` : ''}
  `;

  container.appendChild(toast);
  _toastQueue.push(toast);

  // Wire action buttons
  actions.forEach((action, i) => {
    const btn = toast.querySelector(`[data-action-idx="${i}"]`);
    if (btn && action.onClick) btn.addEventListener('click', () => {
      action.onClick();
      removeToast(toast);
    });
  });

  // Close button
  toast.querySelector('.toast-close').addEventListener('click', () => removeToast(toast));

  // Auto-dismiss
  const timer = setTimeout(() => removeToast(toast), duration);
  toast._dismissTimer = timer;

  return toast;
}

function removeToast(toast) {
  clearTimeout(toast._dismissTimer);
  toast.style.animation = 'toastSlide 0.25s ease reverse forwards';
  setTimeout(() => {
    toast.remove();
    _toastQueue = _toastQueue.filter(t => t !== toast);
  }, 250);
}

// Export globally
window.showAlertToast = showAlertToast;
window.showSuccessToast = (msg) => showAlertToast({ title: 'Success', message: msg, severity: 'success', duration: 3000 });
window.showErrorToast   = (msg) => showAlertToast({ title: 'Error',   message: msg, severity: 'critical', duration: 5000 });
window.showInfoToast    = (msg) => showAlertToast({ title: 'Info',    message: msg, severity: 'info',   duration: 4000 });
