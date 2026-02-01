import db, invoice_generator, os

# initialize DB
db.init_db()

# add accounts
id1 = db.add_payment_account('Bank A','111 111','100100100', is_default=True)
id2 = db.add_payment_account('Bank B','222 222','200200200')
print('accounts:', db.get_payment_accounts())

# generate invoice using Bank B explicitly
cust = (None, 'Test Client', 'ABN', 'Addr1', 'Addr2', 1)
items = [{'qty':1,'description':'Service','price':12.0}]
path = os.path.join('invoices','Invoice_TEST.pdf')
acc = db.get_payment_account(id2)
invoice_generator.generate_invoice_from_db(cust,'9999','01/02/2026', items, path, include_logo=False, bank=acc)
print('generated exists:', os.path.exists(path))

# create invoice record with bank
inv_id = db.create_invoice(1,'9999','01/02/2026',12.0,path, bank_name=acc.get('name'), bank_bsb=acc.get('bsb'), bank_acc=acc.get('acc'))
print('invoice record:', [i for i in db.get_invoices() if i[0]==inv_id])
