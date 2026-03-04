/* ============================================================
   TRIPLE O — API.JS
   All backend calls go through nginx proxy at /api/v1
   NEVER call localhost:8000 directly from the browser
   ============================================================ */

const BASE_URL = '/api/v1';

async function request(method, path, body = null) {
  const token = sessionStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method, headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) { sessionStorage.clear(); window.location.href = '/login.html'; return null; }
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error(`API [${method} ${path}]:`, err);
    return { ok: false, status: 0, data: { detail: 'Network error. Is Docker running?' } };
  }
}

const get  = (path)       => request('GET',    path);
const post = (path, body) => request('POST',   path, body);
const put  = (path, body) => request('PUT',    path, body);
const del  = (path)       => request('DELETE', path);

const Auth = {
  async login(email, password) {
    try {
      const res = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
      });
      const data = await res.json();
      return { ok: res.ok, data };
    } catch (err) {
      return { ok: false, data: { detail: 'Cannot connect to server. Is Docker running?' } };
    }
  },
  register(fullName, email, password, role) {
    return post('/auth/register', { full_name: fullName, email, password, role, branch_id: 'branch-001' });
  },
  me() { return get('/auth/me'); },
};

const Products = {
  list(category = null, isPerishable = null) {
    let path = '/products';
    const params = [];
    if (category) params.push(`category=${category}`);
    if (isPerishable !== null) params.push(`is_perishable=${isPerishable}`);
    if (params.length) path += '?' + params.join('&');
    return get(path);
  },
  get(id)       { return get(`/products/${id}`); },
  create(body)  { return post('/products', body); },
  byBarcode(bc) { return get(`/products/barcode/${bc}`); },
};

const Inventory = {
  get(productId, branchId)                   { return get(`/inventory/${productId}/${branchId}`); },
  receive(productId, branchId, quantity)     { return post('/inventory/receive', { product_id: productId, branch_id: branchId, quantity }); },
  adjust(productId, branchId, delta, reason) { return post('/inventory/adjust',  { product_id: productId, branch_id: branchId, delta, reason }); },
};

const Orders = {
  create(branchId)                     { return post('/orders', { branch_id: branchId }); },
  scan(orderId, barcode, quantity = 1) { return post(`/orders/${orderId}/scan`, { barcode, quantity }); },
  checkout(orderId, paymentMethod)     { return post(`/orders/${orderId}/checkout`, { payment_method: paymentMethod }); },
  cancel(orderId, reason)              { return post(`/orders/${orderId}/cancel`, { reason }); },
  get(orderId)                         { return get(`/orders/${orderId}`); },
};

const Events = {
  recent(limit = 50, branchId = null) {
    let path = `/events/recent?limit=${limit}`;
    if (branchId) path += `&branch_id=${branchId}`;
    return get(path);
  },
};

const AI = {
  forecast(productId, branchId, horizonDays = 7) { return get(`/ai/forecast/${productId}/${branchId}?horizon_days=${horizonDays}`); },
  analyzeAllPerishables(branchId)                { return post(`/ai/perishable/analyze-all/${branchId}`, {}); },
  pricingRules(branchId)                         { return get(`/ai/pricing-rules/${branchId}`); },
};

const Health = {
  check() { return fetch('/health').then(r => r.ok ? r.json() : null).catch(() => null); },
};
