import streamlit as st
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
import json

# --- CONFIG ---
st.set_page_config(page_title="Crystal Trading", layout="centered")
st.title("💎 Crystal Trading")

# --- LOAD CONFIG FILE ---
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
if not os.path.exists(CONFIG_FILE):
    st.error(f"Config file not found: {CONFIG_FILE}")
    st.stop()
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

BASE_DIR = config["base_dir"]
customers = ["Select customer"] + config["customers"]

# --- TRACKER FILE ---
TRACKER_FILE = os.path.join(BASE_DIR, "invoice_tracker.json")
os.makedirs(BASE_DIR, exist_ok=True)
if not os.path.exists(TRACKER_FILE):
    with open(TRACKER_FILE, "w") as f:
        json.dump({"global_invoice_number": 0}, f)

# --- LOAD TRACKER ---
with open(TRACKER_FILE, "r") as f:
    tracker = json.load(f)

# --- SESSION STATE INITIALIZATION ---
if "invoice_items" not in st.session_state or not isinstance(st.session_state.invoice_items, list):
    st.session_state.invoice_items = [{"description": "Item 1", "quantity": 1, "price": 100.0}]
if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
if "last_invoice_number" not in st.session_state:
    st.session_state.last_invoice_number = None

# --- helper callbacks for add/remove ---
def add_item():
    st.session_state.invoice_items.append({
        "description": f"Item {len(st.session_state.invoice_items) + 1}",
        "quantity": 1,
        "price": 100.0
    })

def remove_item(idx: int):
    if 0 <= idx < len(st.session_state.invoice_items):
        st.session_state.invoice_items.pop(idx)

# --- CUSTOMER + VAT ---
st.subheader("Invoice Details")
customer = st.selectbox("Customer", customers)
vat_type = st.radio("VAT Type", ["VAT Inclusive", "VAT Exclusive"], horizontal=True)

# --- DYNAMIC ITEM LIST ---
st.subheader("Invoice Items")
for idx, item in enumerate(list(st.session_state.invoice_items)):
    col1, col2, col3, col4 = st.columns([5, 2, 2, 1])
    item["description"] = col1.text_input("Description", value=item["description"], key=f"desc_{idx}")
    item["quantity"] = col2.number_input("Quantity", min_value=1, step=1, value=item["quantity"], key=f"qty_{idx}")
    item["price"] = col3.number_input("Price (ZAR)", min_value=0.0, step=100.0, value=item["price"], key=f"price_{idx}")
    col4.button("❌", key=f"remove_{idx}", on_click=remove_item, kwargs={"idx": idx})

st.button("➕ Add Item", on_click=add_item)

# --- CALCULATE TOTALS ---
if customer != "Select customer":
    subtotal = sum(item["quantity"] * item["price"] for item in st.session_state.invoice_items)
    vat = subtotal * 0.15 if vat_type == "VAT Exclusive" else (subtotal - (subtotal / 1.15))
    total = subtotal + vat if vat_type == "VAT Exclusive" else subtotal

    st.markdown(f"### 💰 Subtotal: R{subtotal:,.2f}")
    st.markdown(f"### 🧾 VAT (15%): R{vat:,.2f}")
    st.markdown(f"### ✅ Total: R{total:,.2f}")

    # --- ONE-CLICK DOWNLOAD BUTTON ---
    if st.button("Generate Invoice"):
        tracker["global_invoice_number"] += 1
        invoice_number = tracker["global_invoice_number"]

        def generate_invoice_pdf(customer, items, subtotal, vat, total, vat_type, invoice_number):
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            # Border
            c.setStrokeColor(colors.black)
            c.setLineWidth(1.5)
            c.rect(25, 25, width - 50, height - 50)
            # Header
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 60, "Crystal Trading")
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 100, f"Date: {date.today().strftime('%Y-%m-%d')}")
            c.drawString(50, height - 80, "Invoice No: (i)-" + str(invoice_number))
            c.drawString(50, height - 120, f"Customer: {customer}")
            # Banking details (top-right)
            c.setFont("Helvetica", 12)
            label_x = width - 250
            value_x = width - 50
            start_y = height - 80
            line_height = 15
            bank_details = [
                ("Bank:", "Capitec Business"),
                ("Acc Name:", "Crystal Trading"),
                ("Acc No:", "1478523690"),
                ("Branch Code:", "470010")
            ]
            for i, (label, value) in enumerate(bank_details):
                y = start_y - i * line_height
                c.drawString(label_x, y, label)
                c.drawRightString(value_x, y, value)
            # Table header
            y = height - 180
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Description")
            c.drawString(300, y, "Qty")
            c.drawString(370, y, "Price")
            c.drawString(450, y, "Total")
            c.line(50, y - 5, width - 50, y - 5)
            # Table content
            c.setFont("Helvetica", 10)
            y -= 20
            for item in items:
                c.drawString(50, y, item["description"])
                c.drawString(300, y, str(item["quantity"]))
                c.drawString(370, y, f"R{item['price']:,.2f}")
                c.drawString(450, y, f"R{item['quantity'] * item['price']:,.2f}")
                y -= 20
            # Summary
           # Summary – same alignment & positions as before, but using a list
            summary_details = [
                ("Subtotal:", f"R{subtotal:,.2f}"),
                ("VAT (15%):", f"R{vat:,.2f}"),
                ("Total:", f"R{total:,.2f}")
            ]

            c.line(50, y - 5, width - 50, y - 5)      # horizontal line
            y -= 25                                   # first line starts 25 pt below the line

            for i, (label, value) in enumerate(summary_details):
                curr_y = y - i * 15                   # 15 pt spacing (same as bank details)
                if i == 2:                            # make Total bold
                    c.setFont("Helvetica-Bold", 10)
                else:
                    c.setFont("Helvetica", 10)

                # LEFT‑ALIGNED label at x=400 (same as before)
                c.drawString(400, curr_y, label)

                # RIGHT‑ALIGNED value at x=width‑50 (same as before)
                c.drawRightString(width - 50, curr_y, value)
                # Footer
                c.setFont("Helvetica-Oblique", 10)
                c.drawCentredString(width / 2, 40, "Thank you for your business. We look forward to working with you again!")
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        # Generate PDF in memory
        pdf_buffer = generate_invoice_pdf(
            customer, st.session_state.invoice_items,
            subtotal, vat, total, vat_type, invoice_number
        )

        # Update tracker
        with open(TRACKER_FILE, "w") as f:
            json.dump(tracker, f)

        # ONE-CLICK DOWNLOAD
        st.download_button(
            label="Download Invoice",
            data=pdf_buffer.getvalue(),
            file_name=f"Crystal_Trading_(i)-{invoice_number}.pdf",
            mime="application/pdf",
            key=f"dl_{invoice_number}",
            on_click=lambda: None  # forces immediate download
        )

        # Reset form
        st.session_state.invoice_items = [{"description": "Item 1", "quantity": 1, "price": 100.0}]

else:
    st.info("Please select a customer to generate a invoice.")