function showSection(sectionId){
    document.querySelectorAll('.section').forEach(section=>{
        section.classList.add('hidden');
    });

    document.getElementById(sectionId).classList.remove('hidden');
}

// Simulated product list (replace with backend fetch)
let products = [];

document.getElementById("productForm").addEventListener("submit", function(e){
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

function updateProductTable(){
    let table = document.getElementById("productTable");
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

    document.getElementById("totalProducts").innerText = products.length;
}

function deleteProduct(index){
    products.splice(index,1);
    updateProductTable();
}

function logout(){
    alert("Logging out...");
    window.location.href = "index.html";
}