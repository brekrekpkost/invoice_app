from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import textwrap
import os
from datetime import datetime

BANK_INFO = {
    "name": "Agajan Babayev",
    "bsb": "633 123",
    "acc": "222 245 938"
}

ACCENT_COLOR = "#2b5797"
LOGO_PATH = "logo.png"
PHONE = "+61404746265"

def generate_invoice_from_db(customer, invoice_num, date, line_items, output_path, 
                            sender_email=None, sender_abn=None, include_logo=True, bank=None):
    if sender_email is None:
        sender_email = "finance@krepko.com.au"
    if sender_abn is None:
        sender_abn = "20693126171"
        
    config = {
        "color": ACCENT_COLOR,
        "sender": {
            "abn": sender_abn,
            "phone": PHONE,
            "email": sender_email
        },
        "meta": {
            "number": invoice_num,
            "date": date
        },
        "client": {
            "name": customer[1],
            "abn": customer[2],
            "address_line_1": customer[3],
            "address_line_2": customer[4]
        },
        "items": line_items,
        "bank": BANK_INFO,
        "include_logo": include_logo
    }

    # override bank info with the explicit bank passed in
    if bank and isinstance(bank, dict):
        config['bank'].update({k: bank.get(k) for k in ('name', 'bsb', 'acc') if bank.get(k)})
    
    draw_invoice(output_path, config)
    return output_path

def draw_invoice(filename, config):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    sender = config.get('sender', {})
    client = config.get('client', {})
    invoice_meta = config.get('meta', {})
    items = config.get('items', [])
    bank = config.get('bank', {})
    # override bank info with stored settings if available
    try:
        db_bank = db.get_bank_info()
        if db_bank:
            for k in ['name', 'bsb', 'acc']:
                if db_bank.get(k):
                    bank[k] = db_bank.get(k)
    except Exception:
        pass

    include_logo = config.get('include_logo', True)
    
    accent_color = colors.HexColor(config.get('color', '#2b5797')) 
    text_color = colors.black

    y = height - 2.0 * cm 
    left_margin = 2.0 * cm
    right_margin = width - 2.0 * cm
    
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 10)
    
    c.drawString(left_margin, y, f"ABN: {sender.get('abn', '')}")
    
    # Add logo if requested and exists
    if include_logo and os.path.exists(LOGO_PATH):
        try:
            img = ImageReader(LOGO_PATH)
            img_width, img_height = img.getSize()
            aspect = img_height / float(img_width)
            
            logo_width = 3 * cm
            logo_height = logo_width * aspect
            
            c.drawImage(img, right_margin - logo_width, y - logo_height + 0.3*cm, 
                       width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Logo error: {e}")
    
    y -= 0.5 * cm
    
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, f"Phone {sender.get('phone', '')}")
    y -= 0.5 * cm
    
    c.drawString(left_margin, y, f"Email {sender.get('email', '')}")
    y -= 1.5 * cm 

    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, f"INVOICE NO. #{invoice_meta.get('number', '')}")
    
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_margin, y, f"DATE {invoice_meta.get('date', '')}")
    
    y -= 1.5 * cm

    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin, y, "BILL TO")
    y -= 0.6 * cm
    
    c.setFillColor(text_color)
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, client.get('name', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, client.get('address_line_1', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, client.get('address_line_2', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, f"ABN {client.get('abn', '')}")
    
    y -= 1.5 * cm

    c.setFillColor(accent_color)
    c.rect(left_margin - 0.2*cm, y - 0.2*cm, width - 4.0*cm + 0.4*cm, 0.8*cm, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    
    col_qty = left_margin
    col_desc = left_margin + 2.5 * cm
    col_unit = left_margin + 11.0 * cm
    col_total = left_margin + 14.5 * cm
    
    text_y = y + 0.1 * cm
    c.drawString(col_qty, text_y, "QUANTITY")
    c.drawString(col_desc, text_y, "DESCRIPTION")
    c.drawString(col_unit, text_y, "UNIT PRICE")
    c.drawString(col_total, text_y, "TOTAL")
    
    y -= 0.8 * cm

    c.setFillColor(text_color)
    c.setFont("Helvetica", 10)
    subtotal = 0.0

    for i, item in enumerate(items):
        qty = item['qty']
        price = item['price']
        total = qty * price
        subtotal += total
        
        c.drawString(col_qty, y, str(qty))
        c.drawString(col_unit, y, f"${price:.2f} AUD")
        c.drawString(col_total, y, f"${total:.2f} AUD")
        
        wrapped_lines = textwrap.wrap(item['description'], width=42)
        line_y = y
        for line in wrapped_lines:
            c.drawString(col_desc, line_y, line.strip())
            line_y -= 0.5 * cm
        
        y = line_y - 0.3 * cm

    y -= 0.2 * cm
    c.setStrokeColor(accent_color)
    c.setLineWidth(1)
    c.line(col_unit, y + 0.4*cm, right_margin, y + 0.4*cm)
    
    c.setFont("Helvetica-Bold", 10)
    
    c.drawString(col_unit, y, "SUBTOTAL")
    c.drawRightString(right_margin, y, f"{subtotal:.2f}")
    y -= 0.6 * cm
    
    sales_tax = 0.00
    c.drawString(col_unit, y, "SALES TAX")
    c.drawRightString(right_margin, y, f"{sales_tax:.2f}")
    y -= 0.6 * cm
    
    c.setStrokeColor(accent_color)
    c.line(col_unit, y + 0.4*cm, right_margin, y + 0.4*cm)
    
    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(col_unit, y, "GRAND TOTAL")
    c.drawRightString(right_margin, y, f"$ {subtotal + sales_tax:.2f} AUD")
    
    y -= 3.0 * cm

    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin, y, "Bank transfer (Preferred)")
    y -= 0.6 * cm
    
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, f"Account Name: {bank.get('name', '')}")
    y -= 0.5 * cm
    c.drawString(left_margin, y, f"BSB: {bank.get('bsb', '')}")
    y -= 0.5 * cm
    c.drawString(left_margin, y, f"ACC: {bank.get('acc', '')}")
    
    y -= 2.0 * cm
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(accent_color)
    c.drawString(left_margin, y, "Thank you for your business!")

    c.save()
    print(f"Invoice generated: {filename}")

def generate_receipt(customer, invoice_num, date, line_items, output_path, 
                            sender_email=None, sender_abn=None, include_logo=True, bank=None, total_paid=0.0):
    if sender_email is None:
        sender_email = "finance@krepko.com.au"
    if sender_abn is None:
        sender_abn = "20693126171"
        
    config = {
        "color": ACCENT_COLOR,
        "sender": {
            "abn": sender_abn,
            "phone": PHONE,
            "email": sender_email
        },
        "meta": {
            "number": invoice_num,
            "date": date,
            "total_paid": total_paid
        },
        "client": {
            "name": customer[1],
            "abn": customer[2],
            "address_line_1": customer[3],
            "address_line_2": customer[4]
        },
        "items": line_items,
        "bank": BANK_INFO,
        "include_logo": include_logo
    }

    if bank and isinstance(bank, dict):
        config['bank'].update({k: bank.get(k) for k in ('name', 'bsb', 'acc') if bank.get(k)})
    
    draw_receipt(output_path, config)
    return output_path

def draw_receipt(filename, config):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    sender = config.get('sender', {})
    client = config.get('client', {})
    meta = config.get('meta', {})
    items = config.get('items', [])
    bank = config.get('bank', {}) # Include for consistency or contact
    
    include_logo = config.get('include_logo', True)
    
    accent_color = colors.HexColor(config.get('color', '#2b5797')) 
    text_color = colors.black

    y = height - 2.0 * cm 
    left_margin = 2.0 * cm
    right_margin = width - 2.0 * cm
    
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 10)
    
    c.drawString(left_margin, y, f"ABN: {sender.get('abn', '')}")
    
    # Add logo if requested and exists
    if include_logo and os.path.exists(LOGO_PATH):
        try:
            img = ImageReader(LOGO_PATH)
            img_width, img_height = img.getSize()
            aspect = img_height / float(img_width)
            
            logo_width = 3 * cm
            logo_height = logo_width * aspect
            
            c.drawImage(img, right_margin - logo_width, y - logo_height + 0.3*cm, 
                       width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Logo error: {e}")
    
    y -= 0.5 * cm
    
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, f"Phone {sender.get('phone', '')}")
    y -= 0.5 * cm
    
    c.drawString(left_margin, y, f"Email {sender.get('email', '')}")
    y -= 1.5 * cm 

    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, f"RECEIPT NO. #{meta.get('number', '')}")
    
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_margin, y, f"PAID DATE {datetime.now().strftime('%d/%m/%Y')}")
    
    y -= 1.5 * cm

    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin, y, "BILLED TO")
    y -= 0.6 * cm
    
    c.setFillColor(text_color)
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, client.get('name', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, client.get('address_line_1', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, client.get('address_line_2', ''))
    y -= 0.5 * cm
    c.drawString(left_margin, y, f"ABN {client.get('abn', '')}")
    
    y -= 1.5 * cm

    # Receipt Table
    c.setFillColor(accent_color)
    c.rect(left_margin - 0.2*cm, y - 0.2*cm, width - 4.0*cm + 0.4*cm, 0.8*cm, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    
    col_qty = left_margin
    col_desc = left_margin + 2.5 * cm
    col_unit = left_margin + 11.0 * cm
    col_total = left_margin + 14.5 * cm
    
    text_y = y + 0.1 * cm
    c.drawString(col_qty, text_y, "QUANTITY")
    c.drawString(col_desc, text_y, "DESCRIPTION")
    c.drawString(col_unit, text_y, "UNIT PRICE")
    c.drawString(col_total, text_y, "TOTAL")
    
    y -= 0.8 * cm

    c.setFillColor(text_color)
    c.setFont("Helvetica", 10)
    subtotal = 0.0

    for i, item in enumerate(items):
        qty = item['qty']
        price = item['price']
        total = qty * price
        subtotal += total
        
        c.drawString(col_qty, y, str(qty))
        c.drawString(col_unit, y, f"${price:.2f} AUD")
        c.drawString(col_total, y, f"${total:.2f} AUD")
        
        wrapped_lines = textwrap.wrap(item['description'], width=42)
        line_y = y
        for line in wrapped_lines:
            c.drawString(col_desc, line_y, line.strip())
            line_y -= 0.5 * cm
        
        y = line_y - 0.3 * cm

    y -= 0.2 * cm
    c.setStrokeColor(accent_color)
    c.setLineWidth(1)
    c.line(col_unit, y + 0.4*cm, right_margin, y + 0.4*cm)
    
    c.setFont("Helvetica-Bold", 10)
    
    c.drawString(col_unit, y, "TOTAL PAID")
    c.drawRightString(right_margin, y, f"${subtotal:.2f} AUD")
    y -= 0.6 * cm
    
    c.setFillColor(accent_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(col_unit, y, "BALANCE DUE")
    c.drawRightString(right_margin, y, "$ 0.00 AUD")
    
    y -= 3.0 * cm
    
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(accent_color)
    c.drawCentredString(width / 2.0, y, "PAYMENT RECEIVED - THANK YOU")

    c.save()
    print(f"Receipt generated: {filename}")
