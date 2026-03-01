let codeReader = null;

function startScanner() {
    codeReader = new ZXing.BrowserMultiFormatReader();
    alert(codeReader);

    // Use default camera (usually back camera)
    const constraints = {
        video: {
            facingMode: "environment"  // back camera
        }
    };

    codeReader.decodeFromConstraints(constraints, 'video', (result, err) => {
        if (result) {
            
            const barcode = result.text;
            alert(result);
           
            document.getElementById("barcodeInput").value = barcode;
            console.log("Barcode detected:", barcode);
            
            // Optionally stop after first scan
            // stopScanner();
            
           // fetchProductFromBackend(barcode);
        }

        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.error(err);
        }
    });

    console.log("Scanner started. Point camera at barcode.");
}

function stopScanner() {
    if (codeReader) {
        codeReader.reset();  // stops camera
        console.log("Scanner stopped.");
    }
}

// function fetchProductFromBackend(barcode) {
//     fetch(`http://localhost:5000/products/${barcode}`)
//         .then(res => res.json())
//         .then(data => {
//             console.log("Product info:", data);
//             alert(`Product: ${data.name}\nPrice: KES ${data.price}`);
//         })
//         .catch(err => {
//             console.error("Error fetching product:", err);
//             alert("Product not found or server error");
//         });
// }