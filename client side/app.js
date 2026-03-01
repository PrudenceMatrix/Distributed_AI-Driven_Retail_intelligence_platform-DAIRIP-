// ===== STATE =====
let cart = [];
let total = 0;
let codeReader = null;
let scannerActive = false;

// ===== DOM REFERENCES =====
const barcodeInput = document.getElementById("barcodeInput");
const productDisplay = document.getElementById("productDisplay");
const cartList = document.getElementById("cartList");
const totalAmount = document.getElementById("totalAmount");

// ===== EVENT LISTENERS =====
document.getElementById("startScanBtn").addEventListener("click", startScanner);
document.getElementById("stopScanBtn").addEventListener("click", stopScanner);
document.getElementById("searchBtn").addEventListener("click", searchProduct);
document.getElementById("checkoutBtn").addEventListener("click", openCheckout);
document.getElementById("cancelCheckoutBtn").addEventListener("click", closeCheckout);
document.getElementById("confirmPaymentBtn").addEventListener("click", processPayment);

// ===== PRODUCT SEARCH (TEMP MOCK) =====
function searchProduct() {
    const barcode = barcodeInput.value.trim();
    if (!barcode) return;

    const product = {
        id: barcode,
        name: "Sample Product",
        price: 150,
        image: "https://via.placeholder.com/120"
    };

    displayProduct(product);
}

// ===== DISPLAY PRODUCT =====
function displayProduct(product) {
    productDisplay.innerHTML = "";

    const img = document.createElement("img");
    img.src = product.image;

    const name = document.createElement("h4");
    name.textContent = product.name;

    const price = document.createElement("p");
    price.textContent = `Price: KES ${product.price}`;

    const qtyInput = document.createElement("input");
    qtyInput.type = "number";
    qtyInput.value = 1;
    qtyInput.min = 1;

    const addBtn = document.createElement("button");
    addBtn.textContent = "Add to Cart";
    addBtn.addEventListener("click", () => {
        addToCart(product, parseInt(qtyInput.value));
    });

    productDisplay.append(img, name, price, qtyInput, addBtn);
}

// ===== ADD TO CART =====
function addToCart(product, quantity) {
    const itemTotal = product.price * quantity;

    cart.push({
        ...product,
        quantity,
        total: itemTotal
    });

    total += itemTotal;
    updateCart();
}

// ===== UPDATE CART =====
function updateCart() {
    cartList.innerHTML = "";

    cart.forEach(item => {
        const div = document.createElement("div");
        div.classList.add("cart-item");
        div.textContent = `${item.name} x${item.quantity} - KES ${item.total}`;
        cartList.appendChild(div);
    });

    totalAmount.textContent = total;
}

// ===== CHECKOUT =====
function openCheckout() {
    document.getElementById("modalTotal").textContent = total;
    document.getElementById("checkoutModal").style.display = "flex";
}

function closeCheckout() {
    document.getElementById("checkoutModal").style.display = "none";
}

function processPayment() {
    const phone = document.getElementById("phoneNumber").value;
    alert(`Payment request sent to ${phone}`);
    closeCheckout();
}

// ===== CAMERA SCANNER =====
function startScanner() {
    if (scannerActive) return;

    codeReader = new ZXing.BrowserMultiFormatReader();
    scannerActive = true;

    const constraints = {
        video: { facingMode: "environment" }
    };

    codeReader.decodeFromConstraints(constraints, "video", (result, err) => {
        if (result) {
            barcodeInput.value = result.text;
            stopScanner();
            searchProduct();
        }

        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.error(err);
        }
    });
}

function stopScanner() {
    if (codeReader) {
        codeReader.reset();
        scannerActive = false;
    }
}