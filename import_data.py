import sqlite3
import pandas as pd
import re
import os

DB_NAME = "customers.db"

# --- PHONE NORMALIZATION ---
def normalize_phone(phone):
    if not phone or pd.isna(phone):
        return None
    clean = re.sub(r'\D', '', str(phone))  # Keep only digits
    if clean.startswith('0'):
        clean = '44' + clean[1:]
    elif len(clean) == 10 and (clean.startswith('7') or clean.startswith('1')):
        clean = '44' + clean
    return f"+{clean}"

# --- IMPORT FUNCTION ---
def run_import(excel_path):
    if not os.path.exists(excel_path):
        print(f"Error: File '{excel_path}' not found in this folder.")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Ensure table exists with phone as PRIMARY KEY
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            phone TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            town TEXT,
            postcode TEXT,
            gas_request TEXT
        )
    ''')

    try:
        df = pd.read_excel(excel_path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        print(f"Found columns: {df.columns.tolist()}")

        # Bulk insert inside one transaction for speed
        records = []
        for _, row in df.iterrows():
            raw_phone = row.get('phone')
            clean_phone = normalize_phone(raw_phone)
            if not clean_phone:
                continue

            name = row.get('name')
            if pd.isna(name) or str(name).strip() == "":
                name = "Unnamed Customer"

            records.append((
                clean_phone,
                name,
                row.get('address line 1'),
                row.get('town'),
                row.get('postcode'),
                str(row.get('gas request', ''))
            ))

        if records:
            cur.executemany('''
                INSERT OR REPLACE INTO customers
                (phone, name, address, town, postcode, gas_request)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', records)
            conn.commit()
            print(f"Success! Imported {len(records)} customers from {excel_path}.")
        else:
            print("No valid phone numbers found to import.")

    except Exception as e:
        print(f"Failed to read Excel: {e}")
    finally:
        conn.close()

# --- RUN IMPORT ---
if __name__ == "__main__":
    run_import("Address Book.xlsx")  # Change to your Excel filename