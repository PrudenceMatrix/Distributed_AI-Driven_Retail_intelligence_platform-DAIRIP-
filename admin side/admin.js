function showSection(sectionId){
    document.querySelectorAll('.section').forEach(section=>{
        section.classList.add('hidden');
    });

    document.getElementById(sectionId).classList.remove('hidden');

    // Close sidebar automatically on mobile after clicking menu item
    if(window.innerWidth <= 768){
        const sidebar = document.getElementById("sidebar");
        if(sidebar){
            sidebar.classList.remove("active");
        }
    }
}

// =========================
// SIDEBAR TOGGLE LOGIC
// =========================
document.addEventListener("DOMContentLoaded", function(){

    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");

    if(menuToggle && sidebar){
        menuToggle.addEventListener("click", function(){

            if(window.innerWidth <= 768){
                // Mobile: slide in/out
                sidebar.classList.toggle("active");
            } else {
                // Desktop: collapse/expand
                sidebar.classList.toggle("collapsed");
            }

        });
    }

});

// =========================
// PRODUCT LOGIC
// =========================

// Simulated product list (replace with backend fetch)
let products = [];

const productForm = document.getElementById("productForm");

if(productForm){
    productForm.addEventListener("submit", function(e){
        e.preventDefault();

        let name = document.getElementById("productName").value;
        let barcode = document.getElementById("productBarcode").value;
        let price = document.getElementById("productPrice").value;
        let stock = document.getElementById("productStock").value;

        products.push({name, barcode, price, stock});

        updateProductTable();
        alert("Product added successfully!");

        this.reset();
    });
}

function updateProductTable(){
    let table = document.getElementById("productTable");

    if(!table) return;

    table.innerHTML = "";

    products.forEach((product, index)=>{
        table.innerHTML += `
            <tr>
                <td>${product.name}</td>
                <td>${product.barcode}</td>
                <td>KES ${product.price}</td>
                <td>${product.stock}</td>
                <td>
                    <button onclick="deleteProduct(${index})">Delete</button>
                </td>
            </tr>
        `;
    });

    const totalProducts = document.getElementById("totalProducts");
    if(totalProducts){
        totalProducts.innerText = products.length;
    }
}

function deleteProduct(index){
    products.splice(index,1);
    updateProductTable();
}

function logout(){
    alert("Logging out...");
    window.location.href = "index.html";
}