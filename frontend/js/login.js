/* login.js */

// Redirect if already logged in
if (getToken()) redirectByRole(getRole());

// Check API health
Health.check().then(h => {
  const el = document.getElementById('sysStatus');
  if (h) { el.textContent = 'System Online'; }
  else { el.textContent = 'System Offline — check Docker'; }
});

async function doLogin() {
  const email    = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const btn      = document.getElementById('loginBtn');
  const errBox   = document.getElementById('loginError');
  const errText  = document.getElementById('loginErrorText');

  if (!email || !password) {
    showError('Please enter your email and password.');
    return;
  }

  setLoading(btn, true);
  errBox.style.display = 'none';

  const res = await Auth.login(email, password);

  if (!res.ok) {
    showError(res.data?.detail || 'Incorrect email or password. Please try again.');
    setLoading(btn, false, 'Sign In');
    return;
  }

  saveSession(res.data.access_token, email);
  redirectByRole(getRole());
}

function showError(msg) {
  const errBox  = document.getElementById('loginError');
  const errText = document.getElementById('loginErrorText');
  errText.textContent = msg;
  errBox.style.display = 'flex';
  document.getElementById('password').classList.add('error');
  setTimeout(() => document.getElementById('password').classList.remove('error'), 2000);
}

function togglePassword() {
  const input = document.getElementById('password');
  input.type = input.type === 'password' ? 'text' : 'password';
}
