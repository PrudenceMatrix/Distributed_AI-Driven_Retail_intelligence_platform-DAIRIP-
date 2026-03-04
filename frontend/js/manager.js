/* manager.js */
requireAuth(['manager', 'admin']);
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
    overview: 'Dashboard', stock: 'Stock Levels', receive: 'Receive Stock',
    forecast: 'Demand Forecast', perishable: 'Perishable Alerts',
    pricing: 'Pricing Rules', events: 'Event Log',
  }[name] || name;

  const loaders = {
    overview: loadOverview,
    stock: loadStock,
    receive: () => loadProductsIntoSelect('receiveProductId'),
    forecast: () => loadProductsIntoSelect('forecastProductId'),
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
  await loadProductList();
  document.getElementById('stat-products').textContent = allProducts.length;
  document.getElementById('stat-perishable').textContent = allProducts.filter(p => p.is_perishable).length;

  const rules = await AI.pricingRules(BRANCH);
  document.getElementById('stat-discounts').textContent = rules?.data?.data?.rules?.length || 0;

  await loadStockSummary();
  await loadRecentEvents();
}

async function loadStockSummary() {
  if (!allProducts.length) await loadProductList();
  const tbody = document.getElementById('overviewStock');
  tbody.innerHTML = `<tr><td colspan="4" class="td-loading"><span class="spinner spinner-sm"></span></td></tr>`;

  let lowStock = 0;
  const rows = await Promise.all(allProducts.map(async p => {
    const inv = await Inventory.get(p.id, BRANCH);
    const qty = inv?.data?.available_quantity ?? 0;
    if (qty < 10) lowStock++;
    return { p, qty, price: inv?.data?.current_price ?? p.current_price };
  }));

  document.getElementById('stat-lowstock').textContent = lowStock;

  tbody.innerHTML = rows.map(({ p, qty, price }) => {
    const status = qty === 0 ? '<span class="badge badge-red">Out of Stock</span>'
      : qty < 10 ? '<span class="badge badge-amber">Low Stock</span>'
      : '<span class="badge badge-green">In Stock</span>';
    return `<tr>
      <td><strong>${p.name}</strong></td>
      <td><strong style="font-family:var(--font-mono);${qty < 10 ? 'color:var(--danger)' : 'color:var(--green)'}">${qty}</strong></td>
      <td><span class="td-mono">${formatKES(price)}</span></td>
      <td>${status}</td>
    </tr>`;
  }).join('');
}

async function loadRecentEvents() {
  const res = await Events.recent(8, BRANCH);
  const container = document.getElementById('recentEvents');
  const events = Array.isArray(res?.data) ? res.data : [];
  if (!events.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No recent events</div></div>';
    return;
  }
  container.innerHTML = events.map(renderEventItem).join('');
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
async function loadProductList() {
  if (allProducts.length) return;
  const res = await Products.list();
  if (res?.ok) allProducts = res.data;
}

async function loadProductsIntoSelect(selectId) {
  await loadProductList();
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = '<option value="">Select a product...</option>' +
    allProducts.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join('');
}

// ── STOCK ─────────────────────────────────────────────────
async function loadStock() {
  await loadProductList();
  const tbody = document.getElementById('stockTable');
  tbody.innerHTML = `<tr><td colspan="6" class="td-loading"><span class="spinner spinner-sm"></span> Loading...</td></tr>`;

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

async function doReceive() {
  const productId = document.getElementById('receiveProductId').value;
  const quantity  = parseInt(document.getElementById('receiveQty').value);
  if (!productId) { toast('Select a product.', 'error'); return; }
  if (!quantity || quantity < 1) { toast('Enter a valid quantity.', 'error'); return; }
  const res = await Inventory.receive(productId, BRANCH, quantity);
  if (res?.ok) {
    toast(`${quantity} units received successfully.`);
    document.getElementById('receiveQty').value = '';
  } else toast('Failed to receive stock.', 'error');
}

// ── FORECAST ──────────────────────────────────────────────
async function doForecast() {
  const productId = document.getElementById('forecastProductId').value;
  if (!productId) { toast('Select a product.', 'error'); return; }

  const res = await AI.forecast(productId, BRANCH, 7);
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
  tbody.innerHTML = `<tr><td colspan="6" class="td-loading"><span class="spinner spinner-sm"></span> Analyzing...</td></tr>`;
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
  loadPricingRules();
}

// ── PRICING RULES ─────────────────────────────────────────
async function loadPricingRules() {
  const res = await AI.pricingRules(BRANCH);
  const tbody = document.getElementById('pricingTable');
  const rules = res?.data?.data?.rules || [];
  if (!rules.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);font-size:13px;">No active pricing rules. Run perishable analysis first.</td></tr>';
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

// ── INIT ──────────────────────────────────────────────────
loadOverview();
setInterval(loadRecentEvents, 20000);
