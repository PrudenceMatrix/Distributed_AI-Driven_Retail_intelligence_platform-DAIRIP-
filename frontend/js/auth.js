/* ============================================================
   TRIPLE O SUPERMARKET — AUTH.JS
   Login, logout, token management, route guard
   ============================================================ */

const BRANCH_ID = 'branch-001';

/* ─── TOKEN HELPERS ──────────────────────────────────────── */
function getToken()  { return sessionStorage.getItem('token'); }
function getRole()   { return sessionStorage.getItem('role'); }
function getEmail()  { return sessionStorage.getItem('email'); }
function getUserId() { return sessionStorage.getItem('userId'); }

function decodeToken(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch { return null; }
}

function saveSession(token, email) {
  const payload = decodeToken(token);
  sessionStorage.setItem('token',  token);
  sessionStorage.setItem('email',  email);
  sessionStorage.setItem('role',   payload?.role || '');
  sessionStorage.setItem('userId', payload?.sub  || '');
}

function clearSession() {
  sessionStorage.clear();
}

/* ─── ROUTE GUARD ────────────────────────────────────────── */
// Call this at the top of every protected page.
// allowedRoles: array of roles that can access this page.
// e.g. requireAuth(['admin']) or requireAuth(['admin','manager'])
function requireAuth(allowedRoles = []) {
  const token = getToken();
  if (!token) {
    window.location.href = '/login.html';
    return false;
  }

  const payload = decodeToken(token);
  if (!payload) {
    clearSession();
    window.location.href = '/login.html';
    return false;
  }

  // Check token expiry
  if (payload.exp && Date.now() / 1000 > payload.exp) {
    clearSession();
    window.location.href = '/login.html';
    return false;
  }

  // Check role
  if (allowedRoles.length && !allowedRoles.includes(payload.role)) {
    // Redirect to correct page for their role
    redirectByRole(payload.role);
    return false;
  }

  return true;
}

function redirectByRole(role) {
  if (role === 'admin') window.location.href = '/dashboard.html';
  else if (role === 'manager') window.location.href = '/manager.html';
  else window.location.href = '/cashier.html';
}

/* ─── LOGOUT ─────────────────────────────────────────────── */
function logout() {
  clearSession();
  window.location.href = '/login.html';
}

/* ─── POPULATE USER INFO IN UI ───────────────────────────── */
// Call on any page that shows user info in the header/sidebar.
function populateUserInfo() {
  const email = getEmail() || '';
  const role  = getRole()  || '';

  const emailEls = document.querySelectorAll('[data-user-email]');
  const roleEls  = document.querySelectorAll('[data-user-role]');
  const initEls  = document.querySelectorAll('[data-user-initial]');

  emailEls.forEach(el => el.textContent = email);
  roleEls.forEach(el  => el.textContent = role.charAt(0).toUpperCase() + role.slice(1));
  initEls.forEach(el  => el.textContent = email.charAt(0).toUpperCase());
}

/* ─── TOAST UTILITY ──────────────────────────────────────── */
// Used across all pages — single implementation here.
function toast(message, type = 'success', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ'}</span><span class="toast-text">${message}</span>`;
  container.prepend(t);

  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateX(10px)';
    t.style.transition = 'all 0.3s ease';
    setTimeout(() => t.remove(), 300);
  }, duration);
}

/* ─── MODAL HELPERS ──────────────────────────────────────── */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modal when clicking backdrop
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

/* ─── CLOCK ──────────────────────────────────────────────── */
function startClock(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const update = () => {
    el.textContent = new Date().toLocaleTimeString('en-KE', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };
  update();
  setInterval(update, 1000);
}

/* ─── FORMAT HELPERS ─────────────────────────────────────── */
function formatKES(amount) {
  return `KES ${Number(amount).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-KE', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('en-KE', {
    hour: '2-digit', minute: '2-digit'
  });
}

function formatDateTime(dateStr) {
  return `${formatDate(dateStr)}, ${formatTime(dateStr)}`;
}

function timeAgo(dateStr) {
  const seconds = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (seconds < 60)  return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds/60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds/3600)}h ago`;
  return `${Math.floor(seconds/86400)}d ago`;
}

/* ─── LOADING STATE ──────────────────────────────────────── */
function setLoading(btn, loading, originalText) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner spinner-sm"></span>`;
  } else {
    btn.disabled = false;
    btn.innerHTML = originalText || btn.dataset.originalText || 'Submit';
  }
}
