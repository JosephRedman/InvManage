#!/usr/bin/env python3

import threading
import time
import sqlite3
import random
import re
import logging
import socket
from flask import Flask, request, redirect, render_template, session, url_for
from rich.console import Console
from rich.table import Table
from shutil import get_terminal_size
from functools import wraps

DB_FILE = "inventory.db"
app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret!"  # CHANGE THIS for production

ver = "2.1.1"

console = Console()

PRODUCT_CODE_FORMAT = "EUK111111"

# Hardcoded credentials
VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    return ip

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
    match = re.match(r"([A-Za-z]*)(1+)", fmt)
    if not match:
        return "", 6
    prefix, ones = match.groups()
    return prefix, len(ones)

def generate_unique_code(conn, fmt):
    prefix, num_digits = parse_product_code_format(fmt)
    while True:
        number_part = ''.join(str(random.randint(0, 9)) for _ in range(num_digits))
        code = f"{prefix}{number_part}"
        exists = conn.execute("SELECT 1 FROM stock WHERE product_code = ?", (code,)).fetchone()
        if not exists:
            return code

def fetch_all_stock():
    conn = get_db_connection()
    stock = conn.execute("SELECT * FROM stock ORDER BY item").fetchall()
    conn.close()
    return stock

def draw_table(stock):
    terminal_width = get_terminal_size().columns
    ip = get_ip_address()
    ip_line = f"InvManage (c) Elec UK. Access the web UI at: http://{ip}:8080".center(terminal_width)

    table = Table(show_header=True, header_style="bold cyan", expand=True)
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
    console.print(ip_line, style="bold green", markup=False)
    console.print(table)
    print("Press Ctrl+H for help".ljust(terminal_width), end="")

last_db_snapshot = None

def monitor_db_and_draw(interval=1.0):
    global last_db_snapshot
    while True:
        stock = fetch_all_stock()
        current_snapshot = [(r["product_code"], r["item"], r["quantity"], r["low_threshold"], r["on_order"]) for r in stock]
        if current_snapshot != last_db_snapshot:
            draw_table(stock)
            last_db_snapshot = current_snapshot
        time.sleep(interval)

# --- Authentication ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# --- Inventory routes ---

@app.route("/")
@login_required
def index():
    stock = fetch_all_stock()
    return render_template("index.html", stock=stock)

@app.route("/update/<item>", methods=["POST"])
@login_required
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
@login_required
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
        pass
    finally:
        conn.close()

    return redirect("/")

@app.route("/delete/<item>")
@login_required
def delete(item):
    conn = get_db_connection()
    conn.execute("DELETE FROM stock WHERE item = ?", (item,))
    conn.commit()
    conn.close()
    return redirect("/")

# --- Run Flask silently ---

def run_flask():
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True
    logging.getLogger().disabled = True
    app.run(host="0.0.0.0", port=8080)

def main():
    create_table_if_not_exists()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    monitor_db_and_draw(interval=1.0)

if __name__ == "__main__":
    main()
