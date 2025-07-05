function checkProductCode() {
    const code = document.getElementById("product_code").value.trim();
    const item = document.getElementById("item_name").value.trim();
    if (!code) {
        return confirm(`No product code entered for "${item}". Generate one automatically?`);
    }
    return true;
}
