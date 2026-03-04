/* dashboard.js */
requireAuth(['admin']);
populateUserInfo();
startClock('clock');

const BRANCH = 'branch-001';
let allProducts = [];

// ── NAVIGATION ────────────────────────────────────────────
function showSection(name, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(n => n.classList.remove('active'));
  document.getElementById(`sec-${name}`).classList.add('active');
  if (el) el.classList.add('active');
  document.getElementById('topbarTitle').textContent = {
    overview: 'Dashboard', products: 'Products', stock: 'Stock Levels',
    receive: 'Receive Stock', forecast: 'Demand Forecast',
    perishable: 'Perishable Alerts', pricing: 'Pricing Rules', events: 'Event Log'
  }[name] || name;

  // Load data on navigate
  const loaders = {
    overview: loadOverview,
    products: loadProducts,
    stock: loadStock,
    receive: () => loadProductsIntoSelect('receiveProductId'),
    forecast: () => loadProductsIntoSelect('forecastProductId'),
    perishable: () => {},
    pricing: loadPricingRules,
    events: loadEvents,
  };
  if (loaders[name]) loaders[name]();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── OVERVIEW ──────────────────────────────────────────────
async function loadOverview() {
  const products = await Products.list();
  if (products?.ok) {
    allProducts = products.data;
    document.getElementById('stat-products').textContent = products.data.length;
    document.getElementById('stat-perishable').textContent = products.data.filter(p => p.is_perishable).length;
  }
  const rules = await AI.pricingRules(BRANCH);
  if (rules?.ok) {
    document.getElementById('stat-discounts').textContent = rules.data.data?.rules?.length || 0;
  }
  await loadRecentEvents();
  await loadPricingRulesWidget();
}

async function loadRecentEvents() {
  const res = await Events.recent(10, BRANCH);
  const container = document.getElementById('recentEvents');
  const events = Array.isArray(res?.data) ? res.data : [];
  document.getElementById('stat-events').textContent = events.length;
  if (!events.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No events yet</div></div>';
    return;
  }
  container.innerHTML = events.map(renderEventItem).join('');
}

async function loadPricingRulesWidget() {
  const res = await AI.pricingRules(BRANCH);
  const container = document.getElementById('pricingWidget');
  const rules = res?.data?.data?.rules || [];
  if (!rules.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🏷</div><div class="empty-state-text">No active discounts</div><div class="empty-state-sub">Run perishable analysis to generate rules</div></div>';
    return;
  }
  container.innerHTML = `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Product</th><th>Discount</th><th>New Price</th></tr></thead>
    <tbody>${rules.map(r => `<tr>
      <td><strong>${r.product_name}</strong></td>
      <td><span class="badge badge-amber">-${r.discount_percentage.toFixed(0)}%</span></td>
      <td><span style="font-family:var(--font-mono);color:var(--warning);">${formatKES(r.discounted_price)}</span></td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderEventItem(e) {
  const meta = Object.entries(e.payload || {})
    .filter(([k]) => !['product_id','branch_id','order_id','cashier_id'].includes(k))
    .map(([k,v]) => `${k}: ${typeof v === 'number' ? (Number.isInteger(v) ? v : Number(v).toFixed(2)) : v}`)
    .slice(0, 3).join(' · ');
  return `<div class="event-item">
    <div class="event-dot ${e.event_type}"></div>
    <div class="event-body">
      <div class="event-type">${e.event_type}</div>
      <div class="event-meta">${meta || e.branch_id || ''}</div>
    </div>
    <div class="event-time">${timeAgo(e.created_at)}</div>
  </div>`;
}

// ── PRODUCTS ──────────────────────────────────────────────
async function loadProducts() {
  const res = await Products.list();
  if (!res?.ok) { renderTableError('productsTable', 7, 'Failed to load products'); return; }
  allProducts = res.data;
  renderProducts(res.data);
}

function renderProducts(list) {
  const tbody = document.getElementById('productsTable');
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><div class="empty-state-text">No products found</div></div></td></tr>';
    return;
  }
  tbody.innerHTML = list.map(p => `<tr>
    <td><strong>${p.name}</strong></td>
    <td><span class="td-mono">${p.sku}</span></td>
    <td><span class="td-mono">${p.barcode || '—'}</span></td>
    <td><span class="badge badge-grey">${p.category}</span></td>
    <td><span class="td-mono">${formatKES(p.base_price)}</span></td>
    <td><span class="td-mono" style="color:${p.current_price < p.base_price ? 'var(--warning)' : 'var(--text)'}">
      ${formatKES(p.current_price)}
      ${p.current_price < p.base_price ? '<span class="badge badge-amber" style="margin-left:4px;">Discounted</span>' : ''}
    </span></td>
    <td>${p.is_perishable ? '<span class="badge badge-amber">Perishable</span>' : '<span class="badge badge-green">Non-perishable</span>'}</td>
  </tr>`).join('');
}

function filterProducts(q) {
  const filtered = allProducts.filter(p =>
    p.name.toLowerCase().includes(q.toLowerCase()) ||
    p.sku.toLowerCase().includes(q.toLowerCase()) ||
    (p.barcode || '').includes(q)
  );
  renderProducts(filtered);
}

async function addProduct() {
  const body = {
    name: document.getElementById('p_name').value.trim(),
    sku: document.getElementById('p_sku').value.trim(),
    barcode: document.getElementById('p_barcode').value.trim() || undefined,
    category: document.getElementById('p_category').value,
    base_price: parseFloat(document.getElementById('p_price').value),
    is_perishable: document.getElementById('p_perishable').checked,
    expiry_days: parseInt(document.getElementById('p_expiry').value) || null,
  };
  if (!body.name || !body.sku || !body.base_price) { toast('Name, SKU and price are required.', 'error'); return; }
  const res = await Products.create(body);
  if (res?.ok) {
    toast(`"${body.name}" added successfully.`);
    closeModal('addProductModal');
    loadProducts();
  } else {
    toast(res?.data?.detail || 'Failed to add product.', 'error');
  }
}

// ── STOCK ─────────────────────────────────────────────────
async function loadStock() {
  if (!allProducts.length) await loadProducts();
  const tbody = document.getElementById('stockTable');
  tbody.innerHTML = '<tr><td colspan="6" class="td-loading"><span class="spinner spinner-sm"></span> Loading stock levels...</td></tr>';

  const rows = await Promise.all(allProducts.map(async p => {
    const inv = await Inventory.get(p.id, BRANCH);
    return { p, inv: inv?.data };
  }));

  tbody.innerHTML = rows.map(({ p, inv }) => {
    const qty = inv?.available_quantity ?? 0;
    const status = qty === 0 ? '<span class="badge badge-red">Out of Stock</span>'
      : qty < 10 ? '<span class="badge badge-amber">Low Stock</span>'
      : '<span class="badge badge-green">In Stock</span>';
    return `<tr>
      <td><strong>${p.name}</strong><br/><span class="td-mono" style="font-size:11px;">${p.sku}</span></td>
      <td><strong style="font-family:var(--font-mono);${qty < 10 ? 'color:var(--danger)' : 'color:var(--green)'}">${qty}</strong></td>
      <td><span class="td-mono">${inv?.reserved_quantity ?? 0}</span></td>
      <td><span class="td-mono">${formatKES(inv?.current_price ?? p.current_price)}</span></td>
      <td>${status}</td>
      <td>
        <div class="quick-receive">
          <input type="number" id="qr_${p.id}" placeholder="qty" min="1"/>
          <button class="btn btn-primary btn-sm" onclick="quickReceive('${p.id}')">+</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

async function quickReceive(productId) {
  const qty = parseInt(document.getElementById(`qr_${productId}`).value);
  if (!qty || qty < 1) { toast('Enter a valid quantity.', 'error'); return; }
  const res = await Inventory.receive(productId, BRANCH, qty);
  if (res?.ok) { toast(`${qty} units received.`); loadStock(); }
  else toast('Failed to receive stock.', 'error');
}

async function loadProductsIntoSelect(selectId) {
  if (!allProducts.length) await loadProducts();
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = '<option value="">Select a product...</option>' +
    allProducts.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join('');
}

async function doReceive() {
  const productId = document.getElementById('receiveProductId').value;
  const branchId  = document.getElementById('receiveBranchId').value;
  const quantity  = parseInt(document.getElementById('receiveQty').value);
  if (!productId) { toast('Select a product.', 'error'); return; }
  if (!quantity || quantity < 1) { toast('Enter a valid quantity.', 'error'); return; }
  const res = await Inventory.receive(productId, branchId, quantity);
  if (res?.ok) {
    toast(`${quantity} units received successfully.`);
    document.getElementById('receiveQty').value = '';
  } else toast('Failed to receive stock.', 'error');
}

// ── FORECAST ──────────────────────────────────────────────
async function doForecast() {
  const productId = document.getElementById('forecastProductId').value;
  const branchId  = document.getElementById('forecastBranchId').value;
  if (!productId) { toast('Select a product.', 'error'); return; }

  const res = await AI.forecast(productId, branchId, 7);
  if (!res?.ok) { toast('Forecast failed.', 'error'); return; }

  const d = res.data.data;
  const max = Math.max(...d.daily_forecasts.map(f => f.predicted_demand));

  document.getElementById('forecastBars').innerHTML = d.daily_forecasts.map(f => `
    <div class="forecast-row">
      <span class="forecast-day">${new Date(f.date).toLocaleDateString('en-KE', {weekday:'short', month:'short', day:'numeric'})}</span>
      <div class="forecast-track">
        <div class="forecast-fill" style="width:${((f.predicted_demand / max) * 100).toFixed(0)}%"></div>
      </div>
      <span class="forecast-qty">${f.predicted_demand}</span>
    </div>`).join('');

  document.getElementById('forecastMeta').innerHTML = `
    <div class="flex flex-col gap-16">
      <div><div class="stat-label">Current Stock</div><div class="stat-value">${d.current_stock}</div></div>
      <div><div class="stat-label">7-Day Predicted Demand</div><div class="stat-value info">${d.total_predicted_demand}</div></div>
      <div><div class="stat-label">Recommended Reorder</div><div class="stat-value green">${d.recommended_reorder_quantity} units</div></div>
      <div class="label">Source: ${d.data_source === 'augmented' ? 'AI-augmented baseline' : 'Real event data'}</div>
    </div>`;

  document.getElementById('forecastResult').style.display = 'block';
  toast('Forecast generated.');
}

// ── PERISHABLE ────────────────────────────────────────────
async function doPerishableAnalysis() {
  const tbody = document.getElementById('perishTable');
  tbody.innerHTML = '<tr><td colspan="6" class="td-loading"><span class="spinner spinner-sm"></span> Analyzing...</td></tr>';
  const res = await AI.analyzeAllPerishables(BRANCH);
  if (!res?.ok) { toast('Analysis failed.', 'error'); return; }

  const results = res.data.data.results;
  tbody.innerHTML = results.map(r => {
    const riskBadge = r.risk_score > 8 ? `<span class="badge badge-red">${r.risk_score.toFixed(2)}</span>`
      : r.risk_score > 3 ? `<span class="badge badge-amber">${r.risk_score.toFixed(2)}</span>`
      : `<span class="badge badge-green">${r.risk_score.toFixed(2)}</span>`;
    const action = r.action === 'discount_applied'
      ? `<span class="badge badge-amber">-${r.discount_percentage}% → ${formatKES(r.new_price)}</span>`
      : `<span class="badge badge-green">No action needed</span>`;
    return `<tr>
      <td><strong>${r.product_name}</strong></td>
      <td><span class="td-mono">${r.current_stock}</span></td>
      <td><span class="td-mono">${r.predicted_demand}</span></td>
      <td><span class="td-mono">${r.days_to_expiry}d</span></td>
      <td>${riskBadge}</td>
      <td>${action}</td>
    </tr>`;
  }).join('');

  toast(`${res.data.data.discounts_applied} discount(s) applied.`,
    res.data.data.discounts_applied > 0 ? 'warning' : 'success');
}

// ── PRICING RULES ─────────────────────────────────────────
async function loadPricingRules() {
  const res = await AI.pricingRules(BRANCH);
  const tbody = document.getElementById('pricingTable');
  const rules = res?.data?.data?.rules || [];
  if (!rules.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted);font-size:13px;">No active pricing rules. Run perishable analysis first.</td></tr>';
    return;
  }
  tbody.innerHTML = rules.map(r => `<tr>
    <td><strong>${r.product_name}</strong></td>
    <td><span class="td-mono">${r.sku}</span></td>
    <td><span class="td-mono">${formatKES(r.original_price)}</span></td>
    <td><span class="td-mono" style="color:var(--warning);">${formatKES(r.discounted_price)}</span></td>
    <td><span class="badge badge-amber">-${r.discount_percentage.toFixed(0)}%</span></td>
    <td><span class="badge badge-red">${r.risk_score.toFixed(2)}</span></td>
  </tr>`).join('');
}

// ── EVENTS ────────────────────────────────────────────────
async function loadEvents() {
  const res = await Events.recent(50, BRANCH);
  const container = document.getElementById('eventsList');
  const events = Array.isArray(res?.data) ? res.data : [];
  if (!events.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No events recorded yet</div></div>';
    return;
  }
  container.innerHTML = events.map(renderEventItem).join('');
}

// ── HELPERS ───────────────────────────────────────────────
function renderTableError(tbodyId, cols, msg) {
  document.getElementById(tbodyId).innerHTML =
    `<tr><td colspan="${cols}" style="text-align:center;padding:24px;color:var(--danger);font-size:13px;">${msg}</td></tr>`;
}

// ── INIT ──────────────────────────────────────────────────
loadOverview();
setInterval(loadRecentEvents, 20000);
