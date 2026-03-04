/* cashier.js */
requireAuth(['cashier', 'manager', 'admin']);
populateUserInfo();
startClock('clock');

const BRANCH = 'branch-001';
let orderId = null;
let cart = [];
let selectedPayment = 'mpesa';
let cameraActive = false;
let scannerControls = null;
let codeReader = null;

// Set cashier name in topbar
document.getElementById('cashierName').textContent =
  (getEmail() || 'cashier').split('@')[0];

// ── ORDER MANAGEMENT ──────────────────────────────────────
async function startNewOrder() {
  const res = await Orders.create(BRANCH);
  if (!res?.ok) { toast('Could not create order. Check connection.', 'error'); return; }
  orderId = res.data.data.order_id;
  cart = [];
  document.getElementById('orderIdDisplay').textContent =
    orderId.substring(0, 8).toUpperCase();
  document.getElementById('checkoutBtn').disabled = true;
  renderCart();
  focusScanInput();
}

// Auto-start on load
startNewOrder();

// Update date display
setInterval(() => {
  document.getElementById('checkoutDate').textContent =
    new Date().toLocaleDateString('en-KE', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
}, 1000);

// ── SCAN ──────────────────────────────────────────────────
async function handleScan() {
  const input = document.getElementById('barcodeInput');
  const barcode = input.value.trim();
  if (!barcode) return;
  if (!orderId) { await startNewOrder(); }

  input.value = '';

  const res = await Orders.scan(orderId, barcode, 1);

  if (!res) { showFeedback('error', '✕', 'Server error', ''); return; }

  if (!res.ok) {
    showFeedback('error', '✕', res.data?.detail || 'Product not found', barcode);
    toast(res.data?.detail || 'Product not found', 'error');
    return;
  }

  const d = res.data.data;
  showFeedback('success', '✓', d.product_name, `${formatKES(d.unit_price)} × ${d.quantity} = ${formatKES(d.line_total)}`);

  // Update local cart
  const existing = cart.find(i => i.barcode === barcode);
  if (existing) {
    existing.quantity = d.quantity;
    existing.line_total = d.line_total;
  } else {
    cart.push({
      barcode,
      product_name: d.product_name,
      sku: d.sku,
      quantity: d.quantity,
      unit_price: d.unit_price,
      line_total: d.line_total,
    });
  }

  renderCart();
  updateSummary(d.order_subtotal, d.order_total);
  document.getElementById('checkoutBtn').disabled = false;
  focusScanInput();
}

function showFeedback(type, icon, name, price) {
  const el = document.getElementById('scanFeedback');
  el.innerHTML = `<div class="feedback-inner ${type}">
    <span class="feedback-icon">${icon}</span>
    <div>
      <div class="feedback-name">${name}</div>
      ${price ? `<div class="feedback-price">${price}</div>` : ''}
    </div>
  </div>`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.innerHTML = ''; }, 3500);
}

function focusScanInput() {
  document.getElementById('barcodeInput').focus();
}

// Auto-focus scan input on any keypress
document.addEventListener('keydown', e => {
  const input = document.getElementById('barcodeInput');
  if (document.activeElement !== input && !e.ctrlKey && !e.metaKey && e.key.length === 1) {
    input.focus();
  }
});

// ── CART ──────────────────────────────────────────────────
function renderCart() {
  const el = document.getElementById('cartItems');
  const totalQty = cart.reduce((s, i) => s + i.quantity, 0);
  document.getElementById('cartCount').textContent =
    `${cart.length} item${cart.length !== 1 ? 's' : ''} · ${totalQty} unit${totalQty !== 1 ? 's' : ''}`;

  if (!cart.length) {
    el.innerHTML = `<div class="cart-empty">
      <div style="font-size:36px;opacity:0.3;margin-bottom:8px;">🛒</div>
      <div style="font-size:13px;font-weight:500;color:var(--text-secondary);">Your cart is empty</div>
      <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">Scan a barcode to add items</div>
    </div>`;

    // Reset summary
    document.getElementById('summaryItems').textContent = '0';
    document.getElementById('summarySubtotal').textContent = 'KES 0.00';
    document.getElementById('summaryVat').textContent = 'KES 0.00';
    document.getElementById('summaryTotal').textContent = '0.00';
    document.getElementById('checkoutBtn').disabled = true;
    return;
  }

  el.innerHTML = cart.map((item, i) => `
    <div class="cart-row">
      <div class="cart-num">${i + 1}</div>
      <div class="cart-item-info">
        <div class="cart-item-name">${item.product_name}</div>
        <div class="cart-item-sub">▋ ${item.barcode} · ${formatKES(item.unit_price)} each</div>
      </div>
      <div class="qty-controls">
        <button class="qty-btn" onclick="adjustQty(${i}, -1)">−</button>
        <div class="qty-num">${item.quantity}</div>
        <button class="qty-btn" onclick="adjustQty(${i}, 1)">+</button>
      </div>
      <div class="cart-item-total">${formatKES(item.line_total)}</div>
      <button class="cart-item-remove" onclick="removeItem(${i})" title="Remove">✕</button>
    </div>
  `).join('');
}

function updateSummary(subtotal, total) {
  const vat = total - subtotal;
  const totalQty = cart.reduce((s, i) => s + i.quantity, 0);
  document.getElementById('summaryItems').textContent = totalQty;
  document.getElementById('summarySubtotal').textContent = formatKES(subtotal);
  document.getElementById('summaryVat').textContent = formatKES(vat);
  document.getElementById('summaryTotal').textContent =
    Number(total).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function recalcSummaryFromCart() {
  const subtotal = cart.reduce((s, i) => s + i.line_total, 0);
  const vat = subtotal * 0.16;
  const total = subtotal + vat;
  updateSummary(subtotal, total);
}

async function adjustQty(index, delta) {
  const item = cart[index];
  const newQty = item.quantity + delta;
  if (newQty < 1) { removeItem(index); return; }

  const res = await Orders.scan(orderId, item.barcode, delta > 0 ? 1 : -1);
  if (res?.ok) {
    item.quantity = newQty;
    item.line_total = item.unit_price * newQty;
    renderCart();
    recalcSummaryFromCart();
  } else {
    toast(res?.data?.detail || 'Could not update quantity.', 'error');
  }
}

function removeItem(index) {
  cart.splice(index, 1);
  renderCart();
  if (cart.length > 0) recalcSummaryFromCart();
}

// ── PAYMENT ───────────────────────────────────────────────
function selectPayment(method, el) {
  selectedPayment = method;
  document.querySelectorAll('.payment-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
}

// ── CHECKOUT ──────────────────────────────────────────────
async function doCheckout() {
  if (!orderId || !cart.length) return;
  const btn = document.getElementById('checkoutBtn');
  btn.disabled = true;
  btn.textContent = 'Processing...';

  const res = await Orders.checkout(orderId, selectedPayment);

  btn.textContent = 'Complete Sale';

  if (!res?.ok) {
    btn.disabled = false;
    toast(res?.data?.detail || 'Checkout failed. Try again.', 'error');
    return;
  }

  showReceipt(res.data.data.receipt);
}

function showReceipt(r) {
  document.getElementById('rcptOrderId').textContent = `#${r.order_id.substring(0,8).toUpperCase()}`;
  document.getElementById('rcptDate').textContent = new Date().toLocaleTimeString('en-KE');
  document.getElementById('rcptPaymentMethod').textContent =
    r.payment_method.charAt(0).toUpperCase() + r.payment_method.slice(1);

  document.getElementById('rcptItems').innerHTML = r.items.map(item => `
    <div class="receipt-item">
      <span class="receipt-item-name">${item.product_name}</span>
      <span class="receipt-item-qty">×${item.quantity}</span>
      <span class="receipt-item-price">${formatKES(item.line_total)}</span>
    </div>
  `).join('');

  document.getElementById('rcptSubtotal').textContent = formatKES(r.subtotal);
  document.getElementById('rcptVat').textContent = formatKES(r.tax_amount);
  document.getElementById('rcptTotal').textContent = formatKES(r.total_amount);

  openModal('receiptModal');
}

function closeSale() {
  closeModal('receiptModal');
  cart = [];
  orderId = null;
  renderCart();
  startNewOrder();
}

// ── CAMERA SCANNER ────────────────────────────────────────
async function toggleCamera() {
  if (cameraActive) { stopCamera(); return; }

  if (!window.ZXingBrowser) {
    toast('Barcode library not loaded.', 'error');
    return;
  }

  try {
    codeReader = new ZXingBrowser.BrowserMultiFormatReader();
    const devices = await ZXingBrowser.BrowserCodeReader.listVideoInputDevices();
    if (!devices.length) { toast('No camera found on this device.', 'error'); return; }

    document.getElementById('cameraContainer').classList.add('show');
    document.getElementById('cameraBtn').textContent = '⏹ Stop Camera';
    cameraActive = true;

    // Use back camera on mobile if available
    const deviceId = devices.find(d => d.label.toLowerCase().includes('back'))?.deviceId
      || devices[devices.length - 1].deviceId;

    scannerControls = await codeReader.decodeFromVideoDevice(
      deviceId,
      document.getElementById('cameraVideo'),
      (result, err) => {
        if (result) {
          document.getElementById('barcodeInput').value = result.getText();
          handleScan();
          stopCamera();
        }
      }
    );
  } catch (e) {
    toast('Camera access denied or unavailable.', 'error');
    stopCamera();
  }
}

function stopCamera() {
  if (scannerControls) { scannerControls.stop(); scannerControls = null; }
  if (codeReader) { codeReader.reset(); codeReader = null; }
  document.getElementById('cameraContainer').classList.remove('show');
  document.getElementById('cameraBtn').textContent = '📷 Use Camera';
  cameraActive = false;
}
