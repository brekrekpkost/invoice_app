import db, invoice_generator, os

# initialize DB/settings
try:
    db.init_db()
except Exception:
    pass

customer = (None, 'Test', 'ABN', '', '', 1)
items = [{'qty': 1, 'description': 'Service', 'price': 10.0}]

p = os.path.join('invoices', 'Invoice_0124.pdf')
invoice_generator.generate_invoice_from_db(customer, '0124', '01/02/2026', items, p, include_logo=False)
print('created', os.path.exists(p))
