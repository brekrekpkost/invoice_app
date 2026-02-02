from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from datetime import datetime
import re
import db
import invoice_generator
import os

console = Console()

def show_menu():
    console.print("\n[bold cyan]Finance Dashboard[/bold cyan]")
    console.print("1. Create Invoice")
    console.print("2. View Invoices")
    console.print("3. Mark Paid/Unpaid")
    console.print("4. Add Customer")
    console.print("5. View Customers")
    console.print("6. Log Transaction")
    console.print("7. View P&L")
    console.print("8. Configure Payment Account")
    console.print("9. Delete Invoice")
    console.print("0. Exit")
    return Prompt.ask("\nChoice")

def add_customer_ui():
    console.print("\n[bold]Add New Customer[/bold]")
    name = Prompt.ask("Customer name")
    abn = Prompt.ask("ABN")
    addr1 = Prompt.ask("Address line 1")
    addr2 = Prompt.ask("Address line 2")
    start_num = Prompt.ask("Starting invoice number", default="1")
    
    customer_id = db.add_customer(name, abn, addr1, addr2, int(start_num))
    console.print(f"[green]Customer added (ID: {customer_id})[/green]")

def view_customers_ui():
    customers = db.get_customers()
    
    if not customers:
        console.print("[yellow]No customers found[/yellow]")
        return
    
    table = Table(title="Customers")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("ABN")
    table.add_column("Next Invoice #", style="green")
    
    for c in customers:
        table.add_row(str(c[0]), c[1], c[2], str(c[5]).zfill(4))
    
    console.print(table)

def create_invoice_ui():
    customers = db.get_customers()
    
    if not customers:
        console.print("[yellow]No customers found. Add a customer first.[/yellow]")
        return
    
    console.print("\n[bold]Select Customer:[/bold]")
    for c in customers:
        console.print(f"{c[0]}. {c[1]}")
    
    cust_input = Prompt.ask("Customer ID")
    m = re.match(r"\s*(\d+)", cust_input or "")
    if not m:
        console.print("[red]Invalid customer ID[/red]")
        return
    customer_id = int(m.group(1))
    customer = db.get_customer(customer_id)
    
    if not customer:
        console.print("[red]Invalid customer ID[/red]")
        return
    
    invoice_num = str(customer[5]).zfill(4)
    date = Prompt.ask("Invoice date", default=datetime.now().strftime("%d/%m/%Y"))
    
    line_items = []
    console.print("\n[bold]Add Line Items (enter blank description to finish)[/bold]")
    
    while True:
        desc = Prompt.ask("Description")
        if not desc:
            break
        qty = int(Prompt.ask("Quantity", default="1"))
        price = float(Prompt.ask("Unit price"))
        line_items.append({"qty": qty, "description": desc, "price": price})
    
    if not line_items:
        console.print("[yellow]No items added. Invoice cancelled.[/yellow]")
        return
    
    # Select sender email
    console.print("\n[bold]Select sender email:[/bold]")
    console.print("1. finance@krepko.com.au")
    console.print("2. agajanbabayev11@outlook.com")
    email_choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
    sender_email = "finance@krepko.com.au" if email_choice == "1" else "agajanbabayev11@outlook.com"
    
    # Select sender ABN
    console.print("\n[bold]Select sender ABN:[/bold]")
    console.print("1. 2069312617 (Krepko)")
    console.print("2. 12 339 140 269 (Agajan Babayev)")
    abn_choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
    sender_abn = "20693126171" if abn_choice == "1" else "12 339 140 269"
    
    # Include logo?
    include_logo = Confirm.ask("Include logo?", default=True)
    
    total = sum(item["qty"] * item["price"] for item in line_items)
    
    console.print(f"\n[bold]Total: ${total:.2f} AUD[/bold]")
    
    if not Confirm.ask("Generate invoice?"):
        return

    # Select payment account to display on invoice
    accounts = db.get_payment_accounts()
    selected_bank = None
    if accounts:
        console.print("\n[bold]Select payment account to use on this invoice:[/bold]")
        for a in accounts:
            default_mark = " (default)" if a.get('is_default') else ""
            console.print(f"{a['id']}. {a['name']} - BSB: {a['bsb']} ACC: {a['acc']}{default_mark}")
        console.print("n. Add new payment account")
        choice = Prompt.ask("Choice", default="")
        if choice and choice.lower().startswith('n'):
            name = Prompt.ask("Account Name")
            bsb = Prompt.ask("BSB")
            acc = Prompt.ask("Account Number")
            make_default = Confirm.ask("Set as default?", default=False)
            new_id = db.add_payment_account(name, bsb, acc, is_default=make_default)
            selected_bank = db.get_payment_account(new_id)
        else:
            m = re.match(r"\s*(\d+)", choice or "")
            if not m:
                console.print("[yellow]No valid selection - using default account[/yellow]")
                selected_bank = db.get_bank_info()
            else:
                selected_bank = db.get_payment_account(int(m.group(1)))
    else:
        console.print("\n[bold yellow]No payment accounts configured. Using default settings.[/bold yellow]")
        selected_bank = db.get_bank_info()

    pdf_path = os.path.join("invoices", f"Invoice_{invoice_num}.pdf")
    invoice_generator.generate_invoice_from_db(
        customer, invoice_num, date, line_items, pdf_path, 
        sender_email, sender_abn, include_logo, bank=selected_bank
    )
    
    invoice_id = db.create_invoice(customer_id, invoice_num, date, total, pdf_path, 
                                   bank_name=selected_bank.get('name') if selected_bank else None,
                                   bank_bsb=selected_bank.get('bsb') if selected_bank else None,
                                   bank_acc=selected_bank.get('acc') if selected_bank else None)
    
    for item in line_items:
        db.add_line_item(invoice_id, item["qty"], item["description"], item["price"])
    
    db.increment_invoice_number(customer_id)
    
    console.print(f"[green]Invoice #{invoice_num} created: {pdf_path}[/green]")

    # Show the payment account used on this invoice
    if selected_bank:
        console.print(f"[bold]Payment account used:[/bold] {selected_bank.get('name','-')} — BSB {selected_bank.get('bsb','-')} ACC {selected_bank.get('acc','-')}")
    else:
        bank_info = db.get_bank_info()
        if bank_info and bank_info.get('name'):
            console.print(f"[bold]Payment account used:[/bold] {bank_info.get('name','-')} — BSB {bank_info.get('bsb','-')} ACC {bank_info.get('acc','-')}")
        else:
            console.print("[bold yellow]No payment account details available[/bold yellow]")

def view_invoices_ui():
    invoices = db.get_invoices()
    
    if not invoices:
        console.print("[yellow]No invoices found[/yellow]")
        return
    
    table = Table(title="Invoices")
    table.add_column("ID", style="cyan")
    table.add_column("Customer", style="magenta")
    table.add_column("Invoice #")
    table.add_column("Date")
    table.add_column("Status")
    table.add_column("Total", style="green")
    table.add_column("Payment Account")
    
    for inv in invoices:
        status_color = "green" if inv[4] == "paid" else "red"
        payment_label = inv[7] if len(inv) > 7 and inv[7] else "-"
        table.add_row(
            str(inv[0]),
            inv[1],
            inv[2],
            inv[3],
            f"[{status_color}]{inv[4]}[/{status_color}]",
            f"${inv[5]:.2f}",
            payment_label
        )
    
    console.print(table)

def mark_paid_ui():
    invoices = db.get_invoices()
    
    if not invoices:
        console.print("[yellow]No invoices found[/yellow]")
        return
    
    console.print("\n[bold]Invoices:[/bold]")
    for inv in invoices:
        status_color = "green" if inv[4] == "paid" else "red"
        console.print(f"{inv[0]}. {inv[1]} - Invoice #{inv[2]} - [{status_color}]{inv[4]}[/{status_color}]")
    
    inv_input = Prompt.ask("Invoice ID to toggle")
    m = re.match(r"\s*(\d+)", inv_input or "")
    if not m:
        console.print("[red]Invalid invoice ID[/red]")
        return
    invoice_id = int(m.group(1))

    current_status = next((inv[4] for inv in invoices if inv[0] == invoice_id), None)
    
    if not current_status:
        console.print("[red]Invalid invoice ID[/red]")
        return
    
    new_status = "paid" if current_status == "unpaid" else "unpaid"
    db.update_invoice_status(invoice_id, new_status)
    console.print(f"[green]Invoice status updated to: {new_status}[/green]")

    if new_status == "paid":
        inv = db.get_invoice(invoice_id)
        if inv:
            # inv: id, customer_id, invoice_number, date, status, total, pdf_path, bank_name, bank_bsb, bank_acc
            customer = db.get_customer(inv[1])
            items_db = db.get_invoice_items(invoice_id)
            line_items = [{"qty": i[0], "description": i[1], "price": i[2]} for i in items_db]
            
            receipt_path = os.path.join("invoices", f"Receipt_{inv[2]}.pdf")
            
            bank_info = {'name': inv[7], 'bsb': inv[8], 'acc': inv[9]}
            
            invoice_generator.generate_receipt(
                customer, inv[2], inv[3], line_items, receipt_path,
                include_logo=True, bank=bank_info, total_paid=inv[5]
            )
            console.print(f"[green]Receipt generated: {receipt_path}[/green]")

def delete_invoice_ui():
    invoices = db.get_invoices()
    if not invoices:
        console.print("[yellow]No invoices found[/yellow]")
        return
    
    console.print("\n[bold]Invoices:[/bold]")
    for inv in invoices:
        console.print(f"{inv[0]}. {inv[1]} - Invoice #{inv[2]} - {inv[4]}")
    
    inv_input = Prompt.ask("Invoice ID to delete")
    m = re.match(r"\s*(\d+)", inv_input or "")
    if not m:
        console.print("[red]Invalid invoice ID[/red]")
        return
    invoice_id = int(m.group(1))
    
    if Confirm.ask(f"Are you sure you want to delete invoice ID {invoice_id}? This cannot be undone."):
        db.delete_invoice(invoice_id)
        console.print("[green]Invoice deleted[/green]")

def configure_bank_ui():
    console.print("\n[bold]Configure Payment Accounts[/bold]")
    while True:
        accounts = db.get_payment_accounts()
        if accounts:
            console.print("\nExisting payment accounts:")
            for a in accounts:
                default_mark = " (default)" if a.get('is_default') else ""
                console.print(f"{a['id']}. {a['name']} - BSB: {a['bsb']} ACC: {a['acc']}{default_mark}")
        else:
            console.print("[yellow]No payment accounts configured[/yellow]")

        console.print("a. Add new account")
        console.print("s. Set default account")
        console.print("b. Back to menu")

        choice = Prompt.ask("Choice", default="b")
        if choice.lower() == 'a':
            name = Prompt.ask("Account Name")
            bsb = Prompt.ask("BSB")
            acc = Prompt.ask("Account Number")
            make_default = Confirm.ask("Set as default?", default=False)
            db.add_payment_account(name, bsb, acc, is_default=make_default)
            console.print("[green]Payment account added[/green]")
        elif choice.lower() == 's':
            id_choice = Prompt.ask("Account ID to set as default")
            m = re.match(r"\s*(\d+)", id_choice or "")
            if not m:
                console.print("[red]Invalid account ID[/red]")
            else:
                db.set_default_payment_account(int(m.group(1)))
                console.print("[green]Default account updated[/green]")
        else:
            break


def add_transaction_ui():
    console.print("\n[bold]Log Transaction[/bold]")
    date = Prompt.ask("Date", default=datetime.now().strftime("%d/%m/%Y"))
    trans_type = Prompt.ask("Type", choices=["income", "cost"])
    amount = float(Prompt.ask("Amount"))
    category = Prompt.ask("Category", default="general")
    notes = Prompt.ask("Notes", default="")
    
    db.add_transaction(date, trans_type, amount, category, notes)
    console.print("[green]Transaction logged[/green]")

def view_pl_ui():
    income, costs = db.get_profit_loss()
    profit = income - costs
    
    table = Table(title="Profit & Loss")
    table.add_column("Item", style="cyan")
    table.add_column("Amount", style="green")
    
    table.add_row("Total Income", f"${income:.2f}")
    table.add_row("Total Costs", f"${costs:.2f}")
    table.add_row("Profit/Loss", f"[{'green' if profit >= 0 else 'red'}]${profit:.2f}[/{'green' if profit >= 0 else 'red'}]")
    
    console.print(table)
