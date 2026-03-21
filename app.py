import sqlite3
import re
import pandas as pd
from flask import Flask, request

app = Flask(__name__)
DB_NAME = "customers.db"

# --- GLOBAL DB CONNECTION (persistent) ---
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")
conn.execute("PRAGMA temp_store = MEMORY;")

# --- CACHE ---
cache = {}

def load_cache():
    global cache
    cur = conn.execute("SELECT * FROM customers")
    cache = {row["phone"]: dict(row) for row in cur.fetchall()}

load_cache()

# --- PHONE NORMALIZATION ---
def normalize_phone(phone):
    if not phone or pd.isna(phone):
        return None
    clean = re.sub(r'\D', '', str(phone))
    if clean.startswith('0'):
        clean = '44' + clean[1:]
    elif len(clean) == 10 and (clean.startswith('7') or clean.startswith('1')):
        clean = '44' + clean
    return f"+{clean}"

# --- LOOKUP ---
@app.route("/lookup")
def lookup():
    raw_phone = request.args.get("phone", "")
    phone = normalize_phone(raw_phone)
    mode = request.args.get("mode", "view")

    user = cache.get(phone)

    if user:
        if mode == "edit":
            return f"""
            <body style="font-family: sans-serif; padding: 20px; background-color: #f0f7ff;">
                <div style="max-width: 400px; margin: auto; background: white; padding: 20px; border-radius: 8px; border-top: 5px solid #3498db; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #2c3e50; margin-top: 0;">Edit Record</h2>
                    <form action="/add_customer" method="POST">
                        <input type="hidden" name="phone" value="{phone}">
                        <label>Name</label>
                        <input type="text" name="name" value="{user['name']}" required style="width:100%; padding:8px; margin:4px 0;">
                        <label>Address</label>
                        <input type="text" name="address" value="{user['address']}" style="width:100%; padding:8px; margin:4px 0;">
                        <label>Town</label>
                        <input type="text" name="town" value="{user['town']}" style="width:100%; padding:8px; margin:4px 0;">
                        <label>Postcode</label>
                        <input type="text" name="postcode" value="{user['postcode']}" style="width:100%; padding:8px; margin:4px 0;">
                        <label>Gas Request</label>
                        <input type="text" name="gas_request" value="{user['gas_request']}" style="width:100%; padding:8px; margin:4px 0;">
                        <button type="submit" style="width:100%; padding:12px; background:#3498db; color:white; border:none; border-radius:4px;">Save Changes</button>
                        <p style="text-align:center;"><a href="/lookup?phone={phone}">Cancel</a></p>
                    </form>
                </div>
            </body>
            """
        else:
            return f"""
            <body style="font-family: sans-serif; padding:20px;">
                <div style="max-width:400px;margin:auto;border:1px solid #ddd;padding:20px;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);border-top:5px solid #3498db;">
                    <div style="display:flex; justify-content:space-between;">
                        <h2>{user['name']}</h2>
                        <a href="/lookup?phone={phone}&mode=edit">Edit</a>
                    </div>
                    <p><strong>Address:</strong><br>{user['address']}<br>{user['town']}, {user['postcode']}</p>
                    <p><strong>Gas Request:</strong> {user['gas_request']}</p>
                    <small>Caller: {phone}</small>
                </div>
            </body>
            """
    else:
        return f"""
        <body style="font-family:sans-serif; padding:20px;">
            <div style="max-width:400px;margin:auto;background:white;padding:20px;border-radius:8px;border-top:5px solid #e74c3c;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color:#e74c3c;">Unknown Caller</h2>
                <p>No record found for <strong>{phone}</strong></p>
                <form action="/add_customer" method="POST">
                    <input type="hidden" name="phone" value="{phone}">
                    <label>Name</label><input type="text" name="name" required style="width:100%; padding:8px; margin:4px 0;">
                    <label>Address</label><input type="text" name="address" style="width:100%; padding:8px; margin:4px 0;">
                    <label>Town</label><input type="text" name="town" style="width:100%; padding:8px; margin:4px 0;">
                    <label>Postcode</label><input type="text" name="postcode" style="width:100%; padding:8px; margin:4px 0;">
                    <label>Gas Request</label><input type="text" name="gas_request" style="width:100%; padding:8px; margin:4px 0;">
                    <button type="submit" style="width:100%; padding:12px; background:#27ae60; color:white; border:none; border-radius:4px;">Save New Customer</button>
                </form>
            </div>
        </body>
        """

# --- ADD / UPDATE CUSTOMER ---
@app.route("/add_customer", methods=["POST"])
def add_customer():
    phone = request.form.get("phone")
    name = request.form.get("name")
    address = request.form.get("address")
    town = request.form.get("town")
    postcode = request.form.get("postcode")
    gas_request = request.form.get("gas_request")

    conn.execute('''
        INSERT OR REPLACE INTO customers
        (phone, name, address, town, postcode, gas_request)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (phone, name, address, town, postcode, gas_request))
    conn.commit()

    # update cache instantly
    cache[phone] = {
        "phone": phone,
        "name": name,
        "address": address,
        "town": town,
        "postcode": postcode,
        "gas_request": gas_request
    }

    return f"""
    <body style="font-family:sans-serif;padding:20px;text-align:center;">
        <h2 style="color:#27ae60;">✓ Record Saved</h2>
        <p><strong>{name}</strong> is now in the database.</p>
        <a href="/lookup?phone={phone}" style="padding:10px 20px;background:#3498db;color:white;text-decoration:none;border-radius:4px;">View Record</a>
    </body>
    """

if __name__ == "__main__":
    app.run(port=5000)