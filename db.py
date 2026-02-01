import sqlite3
from datetime import datetime

DB_NAME = "finance.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        abn TEXT,
        address_line_1 TEXT,
        address_line_2 TEXT,
        next_invoice_number INTEGER DEFAULT 1
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        invoice_number TEXT,
        date TEXT,
        status TEXT DEFAULT 'unpaid',
        total REAL,
        pdf_path TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS line_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        qty INTEGER,
        description TEXT,
        price REAL,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type TEXT,
        amount REAL,
        category TEXT,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payment_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        bsb TEXT,
        acc TEXT,
        is_default INTEGER DEFAULT 0
    )''')

    # Ensure invoices table has bank columns (migrate if needed)
    c.execute("PRAGMA table_info(invoices)")
    cols = [row[1] for row in c.fetchall()]
    if 'bank_name' not in cols:
        c.execute('ALTER TABLE invoices ADD COLUMN bank_name TEXT')
    if 'bank_bsb' not in cols:
        c.execute('ALTER TABLE invoices ADD COLUMN bank_bsb TEXT')
    if 'bank_acc' not in cols:
        c.execute('ALTER TABLE invoices ADD COLUMN bank_acc TEXT')
    
    conn.commit()
    conn.close()

def add_customer(name, abn, addr1, addr2, start_num=1):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO customers (name, abn, address_line_1, address_line_2, next_invoice_number)
                 VALUES (?, ?, ?, ?, ?)''', (name, abn, addr1, addr2, start_num))
    conn.commit()
    customer_id = c.lastrowid
    conn.close()
    return customer_id

def get_customers():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM customers ORDER BY name')
    customers = c.fetchall()
    conn.close()
    return customers

def get_customer(customer_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    customer = c.fetchone()
    conn.close()
    return customer

def increment_invoice_number(customer_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE customers SET next_invoice_number = next_invoice_number + 1 WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()

def create_invoice(customer_id, invoice_num, date, total, pdf_path, bank_name=None, bank_bsb=None, bank_acc=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO invoices (customer_id, invoice_number, date, total, pdf_path, bank_name, bank_bsb, bank_acc)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (customer_id, invoice_num, date, total, pdf_path, bank_name, bank_bsb, bank_acc))
    conn.commit()
    invoice_id = c.lastrowid
    conn.close()
    return invoice_id

def add_line_item(invoice_id, qty, desc, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO line_items (invoice_id, qty, description, price)
                 VALUES (?, ?, ?, ?)''', (invoice_id, qty, desc, price))
    conn.commit()
    conn.close()

def get_invoices():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT i.id, c.name, i.invoice_number, i.date, i.status, i.total, i.pdf_path, i.bank_name, i.bank_bsb, i.bank_acc
                 FROM invoices i
                 JOIN customers c ON i.customer_id = c.id
                 ORDER BY i.date DESC''')
    invoices = c.fetchall()
    conn.close()
    return invoices

def get_invoice_items(invoice_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT qty, description, price FROM line_items WHERE invoice_id = ?', (invoice_id,))
    items = c.fetchall()
    conn.close()
    return items

def update_invoice_status(invoice_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE invoices SET status = ? WHERE id = ?', (status, invoice_id))
    conn.commit()
    conn.close()

def add_transaction(date, trans_type, amount, category, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO transactions (date, type, amount, category, notes)
                 VALUES (?, ?, ?, ?, ?)''', (date, trans_type, amount, category, notes))
    conn.commit()
    conn.close()

def get_transactions():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM transactions ORDER BY date DESC')
    transactions = c.fetchall()
    conn.close()
    return transactions

def get_profit_loss():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'income'")
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE type = 'cost'")
    costs = c.fetchone()[0] or 0
    conn.close()
    return income, costs


def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def set_bank_info(name, bsb, acc):
    # Legacy single-setting for compatibility
    set_setting('bank_name', name)
    set_setting('bank_bsb', bsb)
    set_setting('bank_acc', acc)


def get_bank_info():
    # Prefer default payment_account if present, otherwise fallback to legacy settings
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, bsb, acc, is_default FROM payment_accounts WHERE is_default = 1 LIMIT 1')
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'bsb': row[2], 'acc': row[3], 'is_default': bool(row[4])}
    return {
        'name': get_setting('bank_name'),
        'bsb': get_setting('bank_bsb'),
        'acc': get_setting('bank_acc')
    }


def add_payment_account(name, bsb, acc, is_default=False):
    conn = get_connection()
    c = conn.cursor()
    if is_default:
        c.execute('UPDATE payment_accounts SET is_default = 0')
    c.execute('INSERT INTO payment_accounts (name, bsb, acc, is_default) VALUES (?, ?, ?, ?)', (name, bsb, acc, 1 if is_default else 0))
    conn.commit()
    account_id = c.lastrowid
    conn.close()
    return account_id


def get_payment_accounts():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, bsb, acc, is_default FROM payment_accounts ORDER BY id')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'bsb': r[2], 'acc': r[3], 'is_default': bool(r[4])} for r in rows]


def get_payment_account(account_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, bsb, acc, is_default FROM payment_accounts WHERE id = ?', (account_id,))
    r = c.fetchone()
    conn.close()
    return {'id': r[0], 'name': r[1], 'bsb': r[2], 'acc': r[3], 'is_default': bool(r[4])} if r else None


def set_default_payment_account(account_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE payment_accounts SET is_default = 0')
    c.execute('UPDATE payment_accounts SET is_default = 1 WHERE id = ?', (account_id,))
    conn.commit()
    conn.close()
