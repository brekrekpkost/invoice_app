import db
import ui

def main():
    db.init_db()
    
    while True:
        choice = ui.show_menu()
        
        if choice == "1":
            ui.create_invoice_ui()
        elif choice == "2":
            ui.view_invoices_ui()
        elif choice == "3":
            ui.mark_paid_ui()
        elif choice == "4":
            ui.add_customer_ui()
        elif choice == "5":
            ui.view_customers_ui()
        elif choice == "6":
            ui.add_transaction_ui()
        elif choice == "7":
            ui.view_pl_ui()
        elif choice == "8":
            ui.configure_bank_ui()
        elif choice == "9":
            ui.delete_invoice_ui()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
