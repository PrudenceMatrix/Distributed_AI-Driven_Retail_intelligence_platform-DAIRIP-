/* index.js */
async function init() {
  const health = await Health.check();
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  if (health) {
    dot.className = 'status-dot green pulse';
    text.textContent = 'System Online';
    const products = await Products.list();
    if (products?.ok) {
      document.getElementById('strip-products').textContent = products.data.length;
    }
  } else {
    dot.className = 'status-dot red';
    text.textContent = 'System Offline';
    document.getElementById('strip-status').textContent = 'Offline';
  }
  if (getToken()) {
    document.querySelector('.btn-primary').textContent = 'Go to Dashboard →';
  }
}
init();
