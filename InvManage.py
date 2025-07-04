import threading
import time
import sqlite3
import random
import re
from flask import Flask, request, redirect, render_template_string
from rich.console import Console
from rich.table import Table

DB_FILE = "inventory.db"
app = Flask(__name__)
console = Console()

# Configurable product code format: letters + digits, e.g. "EUK111111" or "JOS111"
PRODUCT_CODE_FORMAT = "EUK111111"  # Change this as you like


TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Inventory Management</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; max-width: 900px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f0f0f0; }
        input[type=number] { width: 60px; }
        input[type=text] { width: 100px; }
        input[type=checkbox] { transform: scale(1.2); }
        .low-stock { background-color: #ffcccc; }
        form { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Inventory Management</h1>

    <table>
        <thead>
            <tr>
                <th>Product Code</th>
                <th>Item</th>
                <th>Quantity</th>
                <th>Low Threshold</th>
                <th>On Order</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for row in stock %}
            <tr class="{{ 'low-stock' if row.quantity <= row.low_threshold else '' }}">
                <form method="post" action="/update/{{ row.item }}">
                <td><input name="product_code" type="text" value="{{ row.product_code or '' }}" required></td>
                <td>{{ row.item }}</td>
                <td><input name="quantity" type="number" min="0" value="{{ row.quantity }}" required></td>
                <td><input name="low_threshold" type="number" min="0" value="{{ row.low_threshold }}" required></td>
                <td style="text-align:center;">
                    <input name="on_order" type="checkbox" value="1" {% if row.on_order %}checked{% endif %}>
                </td>
                <td>
                    <button type="submit">Save</button>
                    <a href="/delete/{{ row.item }}" onclick="return confirm('Delete item?');">Delete</a>
                </td>
                </form>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <h2>Add New Item</h2>
    <form method="post" action="/add" onsubmit="return checkProductCode();">
        <label>Product Code: <input name="product_code" id="product_code" type="text"></label><br><br>
        <label>Item Name: <input name="item" id="item_name" type="text" required></label><br><br>
        <label>Quantity: <input name="quantity" type="number" min="0" value="0" required></label><br><br>
        <label>Low Threshold: <input name="low_threshold" type="number" min="0" value="5" required></label><br><br>
        <label>On Order: <input name="on_order" type="checkbox" value="1"></label><br><br>
        <button type="submit">Add Item</button>
    </form>

    <script>
    function checkProductCode() {
        const code = document.getElementById("product_code").value.trim();
        const item = document.getElementById("item_name").value.trim();
        if (!code) {
            return confirm(`No product code entered for "${item}". Generate one automatically?`);
        }
        return true;
    }
    </script>
</body>
</html>
"""


def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_table_if_not_exists():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        product_code TEXT UNIQUE,
        item TEXT PRIMARY KEY,
        quantity INTEGER DEFAULT 0,
        low_threshold INTEGER DEFAULT 5,
        on_order INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()


def parse_product_code_format(fmt: str):
    """
    Parse the product code format into (prefix_letters, number_count).
    Example: "EUK111111" => ("EUK", 6)
             "111" => ("", 3)
             "JOS111" => ("JOS", 3)
    """
    match = re.match(r"([A-Za-z]*)(1+)", fmt)
    if not match:
        # fallback: no prefix, 6 digits
        return "", 6
    prefix, ones = match.groups()
    return prefix, len(ones)


def generate_unique_code(conn, fmt):
    prefix, num_digits = parse_product_code_format(fmt)
    while True:
        number_part = ''.join(str(random.randint(0, 9)) for _ in range(num_digits))
        code = f"{prefix}{number_part}"
        exists = conn.execute(
            "SELECT 1 FROM stock WHERE product_code = ?", (code,)
        ).fetchone()
        if not exists:
            return code


def fetch_all_stock():
    conn = get_db_connection()
    stock = conn.execute("SELECT * FROM stock ORDER BY item").fetchall()
    conn.close()
    return stock


def draw_table(stock):
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Product Code", style="dim", width=12)
    table.add_column("Item", style="bold")
    table.add_column("Quantity", justify="right")
    table.add_column("Low Threshold", justify="right")
    table.add_column("On Order", justify="center")

    for row in stock:
        low_stock = row["quantity"] <= row["low_threshold"]
        style = "on red" if low_stock else ""
        on_order_str = "X" if row["on_order"] else ""
        table.add_row(
            row["product_code"] or "",
            row["item"],
            str(row["quantity"]),
            str(row["low_threshold"]),
            on_order_str,
            style=style,
        )
    console.clear()
    console.print(table)


last_db_snapshot = None  # to detect changes


def monitor_db_and_draw(interval=1.0):
    global last_db_snapshot
    while True:
        stock = fetch_all_stock()
        # Compare with last snapshot to see if changed
        current_snapshot = [(r["product_code"], r["item"], r["quantity"], r["low_threshold"], r["on_order"]) for r in stock]
        if current_snapshot != last_db_snapshot:
            draw_table(stock)
            last_db_snapshot = current_snapshot
        time.sleep(interval)


@app.route("/")
def index():
    stock = fetch_all_stock()
    return render_template_string(TEMPLATE, stock=stock)


@app.route("/update/<item>", methods=["POST"])
def update(item):
    product_code = request.form["product_code"].strip()
    quantity = int(request.form["quantity"])
    low_threshold = int(request.form["low_threshold"])
    on_order = 1 if request.form.get("on_order") == "1" else 0

    conn = get_db_connection()
    conn.execute("""
        UPDATE stock SET
        product_code = ?,
        quantity = ?,
        low_threshold = ?,
        on_order = ?
        WHERE item = ?
    """, (product_code, quantity, low_threshold, on_order, item))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/add", methods=["POST"])
def add():
    product_code = request.form["product_code"].strip()
    item = request.form["item"].strip()
    quantity = int(request.form["quantity"])
    low_threshold = int(request.form["low_threshold"])
    on_order = 1 if request.form.get("on_order") == "1" else 0

    conn = get_db_connection()
    if not product_code:
        product_code = generate_unique_code(conn, PRODUCT_CODE_FORMAT)

    try:
        conn.execute("""
            INSERT INTO stock (product_code, item, quantity, low_threshold, on_order)
            VALUES (?, ?, ?, ?, ?)
        """, (product_code, item, quantity, low_threshold, on_order))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # could add error message for duplicate
    finally:
        conn.close()

    return redirect("/")


@app.route("/delete/<item>")
def delete(item):
    conn = get_db_connection()
    conn.execute("DELETE FROM stock WHERE item = ?", (item,))
    conn.commit()
    conn.close()
    return redirect("/")


def run_flask():
    # Hide flask output if you want (optional)
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host="0.0.0.0", port=8080)


def main():
    create_table_if_not_exists()

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    monitor_db_and_draw(interval=1.0)


if __name__ == "__main__":
    main()
