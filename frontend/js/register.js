/* register.js */

// Redirect if already logged in
if (getToken()) redirectByRole(getRole());

// Check system status
Health.check().then(h => {
  document.getElementById('sysStatus').textContent = h ? 'System Online' : 'System Offline';
});

async function doRegister() {
  const fullName       = document.getElementById('fullName').value.trim();
  const email          = document.getElementById('email').value.trim();
  const role           = document.getElementById('role').value;
  const password       = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  const btn            = document.getElementById('registerBtn');

  // Clear errors
  hideError();

  // Validate
  if (!fullName)             { showError('Please enter your full name.'); return; }
  if (!email)                { showError('Please enter your email address.'); return; }
  if (!email.includes('@'))  { showError('Please enter a valid email address.'); return; }
  if (!role)                 { showError('Please select your role.'); return; }
  if (!password)             { showError('Please enter a password.'); return; }
  if (password.length < 8)   { showError('Password must be at least 8 characters.'); return; }
  if (password !== confirmPassword) { showError('Passwords do not match.'); return; }

  setLoading(btn, true);

  const res = await post('/auth/register', {
    full_name: fullName,
    email,
    password,
    role,
    branch_id: 'branch-001',
  });

  setLoading(btn, false, 'Create Account');

  if (!res) {
    showError('Network error. Make sure the server is running.');
    return;
  }

  if (!res.ok) {
    showError(res.data?.detail || 'Registration failed. That email may already be in use.');
    return;
  }

  // Success
  document.getElementById('registerSuccess').style.display = 'flex';
  setTimeout(() => { window.location.href = 'login.html'; }, 2000);
}

function showError(msg) {
  const box  = document.getElementById('registerError');
  const text = document.getElementById('registerErrorText');
  text.textContent = msg;
  box.style.display = 'flex';
}

function hideError() {
  document.getElementById('registerError').style.display = 'none';
}

function togglePassword(fieldId) {
  const input = document.getElementById(fieldId);
  input.type = input.type === 'password' ? 'text' : 'password';
}
