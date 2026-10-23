import os
import json
import io
import streamlit as st
from PIL import Image
import pytesseract

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="TaxLedger Enterprise Cloud", page_icon="🔒", layout="wide")

CONFIG_FILE = "firms.json"

USER_CREDENTIALS = {
    "admin": "admin123",
    "shivam": "shivam@2026",
    "mohit": "pass1234"
}

STATE_CODES = [
    "Uttar Pradesh (09)", "Delhi (07)", "Haryana (06)", "Punjab (03)",
    "Uttarakhand (05)", "Rajasthan (08)", "Bihar (10)", "Madhya Pradesh (23)",
    "Maharashtra (27)", "Gujarat (24)", "West Bengal (19)", "Tamil Nadu (33)",
    "Karnataka (29)", "Telangana (36)", "Andhra Pradesh (37)", "Other State"
]

UNITS_LIST = ["Kgs", "Pcs", "Dzn", "Nos", "Mtrs", "Bags", "Boxes", "Ltrs"]

def check_authentication():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""

    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center;'>🔐 TaxLedger Enterprise - Login</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8;'>Please authorize access to continue to the workspace.</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username_input = st.text_input("Username / User ID")
                password_input = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Sign In 🔑", use_container_width=True)

                if submit_login:
                    if username_input in USER_CREDENTIALS and USER_CREDENTIALS[username_input] == password_input:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = username_input
                        st.success("Authorization successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password. Please try again.")
        return False
    return True

if not check_authentication():
    st.stop()

DEFAULT_FIRMS_DATA = {
    "Shivam Store": {
        "gstin": "09AIPPG0981P1ZI", "pan": "AIPPG0981P",
        "address": "Ward No. 16, Gali Ghanta Ghar, Balakram, Khatauli, Muzaffarnagar (U.P.) - 251201",
        "phone": "7500055873", "fssai": "12724065000128",
        "bank_name": "Gulshan Mercantile Urban Co-operative Bank Ltd.", "account_no": "507022000134", "ifsc": "IBKL01529GM", "jurisdiction": "Muzaffarnagar"
    },
    "Pal Enterprises": {
        "gstin": "09ABCDE1234F1Z1", "pan": "ABCDE1234F",
        "address": "Plot No. 12, Industrial Area, Khatauli, Muzaffarnagar (U.P.)",
        "phone": "9876543210", "fssai": "",
        "bank_name": "State Bank of India", "account_no": "30987654321", "ifsc": "SBIN0001234", "jurisdiction": "Muzaffarnagar"
    }
}

def load_firms_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_FIRMS_DATA
    return DEFAULT_FIRMS_DATA

def save_firms_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def make_watermark_callback(watermark_text):
    def draw_watermark(canvas, doc):
        if not watermark_text.strip():
            return
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.HexColor('#E2E8F0'))
        canvas.translate(doc.pagesize[0] / 2.0, doc.pagesize[1] / 2.0)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text.upper())
        canvas.restoreState()
    return draw_watermark

def generate_pdf_bytes(firm_name, inv_no, date, vehicle_no, eway_bill_no, place_of_supply, firm_info, billed_text, shipped_text, items_list, tax_type, total_tax_rate, watermark_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    PRIMARY_COLOR = colors.HexColor('#0F172A')
    ACCENT_COLOR = colors.HexColor('#2563EB')
    BORDER_COLOR = colors.HexColor('#CBD5E0')
    BG_LIGHT = colors.HexColor('#F8FAFC')

    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8.5, leading=12, fontName='Helvetica', textColor=colors.HexColor('#334155'))
    table_header = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8.5, leading=10, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)
    cell_style = ParagraphStyle('CellText', parent=styles['Normal'], fontSize=8.5, leading=11, fontName='Helvetica', textColor=colors.HexColor('#1E293B'))
    cell_bold = ParagraphStyle('CellBold', parent=cell_style, fontName='Helvetica-Bold')

    seller_text = f"<b>M/s {firm_name.upper()}</b><br/>{firm_info.get('address','')}<br/><b>GSTIN:</b> {firm_info.get('gstin','')} | <b>PAN:</b> {firm_info.get('pan','')}"
    if firm_info.get("phone") or firm_info.get("fssai"):
        seller_text += f"<br/>Tel: {firm_info.get('phone','')} | FSSAI Lic. No.: {firm_info.get('fssai','')}"

    invoice_meta = f"<b>TAX INVOICE</b><br/><br/><b>Invoice No:</b> {inv_no}<br/>"
    if vehicle_no.strip():
        invoice_meta += f"<b>Vehicle No:</b> {vehicle_no}<br/>"
    if eway_bill_no.strip():
        invoice_meta += f"<b>E-Way Bill No:</b> {eway_bill_no}<br/>"
    invoice_meta += f"<b>Date:</b> {date}<br/><b>Place of Supply:</b> {place_of_supply}"

    story = []

    header_table = Table([[Paragraph(seller_text, header_style), Paragraph(invoice_meta, ParagraphStyle('RightMeta', parent=header_style, alignment=2))]], colWidths=[4.3 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 1.5, ACCENT_COLOR)
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    billed_formatted = billed_text.replace('\n', '<br/>')
    shipped_formatted = shipped_text.replace('\n', '<br/>')
    address_table = Table([[Paragraph(f"<b>BILLED TO:</b><br/>{billed_formatted}", header_style), Paragraph(f"<b>SHIPPED TO:</b><br/>{shipped_formatted}", header_style)]], colWidths=[3.7 * inch, 3.8 * inch])
    address_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8)
    ]))
    story.append(address_table)
    story.append(Spacer(1, 10))

    items_table_data = [
        [Paragraph("<b>S.N.</b>", table_header), Paragraph("<b>Description of Goods</b>", table_header), Paragraph("<b>HSN/SAC</b>", table_header), Paragraph("<b>Qty.</b>", table_header), Paragraph("<b>Unit</b>", table_header), Paragraph("<b>Price (₹)</b>", table_header), Paragraph("<b>Amount (₹)</b>", table_header)]
    ]

    subtotal = 0.0
    for idx, item in enumerate(items_list, 1):
        amt = item["qty"] * item["price"]
        subtotal += amt
        items_table_data.append([
            Paragraph(str(idx), cell_style),
            Paragraph(item["desc"], cell_style),
            Paragraph(item["hsn"], cell_style),
            Paragraph(f"{item['qty']:.2f}", cell_style),
            Paragraph(item["unit"], cell_style),
            Paragraph(f"{item['price']:,.2f}", cell_style),
            Paragraph(f"{amt:,.2f}", cell_style)
        ])

    items_table_data.append(["", Paragraph("<b>Sub Total</b>", cell_bold), "", "", "", "", Paragraph(f"{subtotal:,.2f}", cell_bold)])

    if tax_type == "Intra-State (CGST + SGST)":
        half_tax_rate = total_tax_rate / 2.0
        cgst_amt = subtotal * (half_tax_rate / 100.0)
        sgst_amt = subtotal * (half_tax_rate / 100.0)
        total_tax_amt = cgst_amt + sgst_amt
        grand_total = subtotal + total_tax_amt

        items_table_data.append(["", Paragraph(f"Add : CGST @ {half_tax_rate:.2f}%", cell_style), "", "", "", "", Paragraph(f"{cgst_amt:,.2f}", cell_style)])
        items_table_data.append(["", Paragraph(f"Add : SGST @ {half_tax_rate:.2f}%", cell_style), "", "", "", "", Paragraph(f"{sgst_amt:,.2f}", cell_style)])
    else:
        igst_amt = subtotal * (total_tax_rate / 100.0)
        total_tax_amt = igst_amt
        grand_total = subtotal + total_tax_amt

        items_table_data.append(["", Paragraph(f"Add : IGST @ {total_tax_rate:.2f}%", cell_style), "", "", "", "", Paragraph(f"{igst_amt:,.2f}", cell_style)])

    items_table_data.append(["", Paragraph("<b>Grand Total</b>", cell_bold), "", "", "", "", Paragraph(f"<b>₹ {grand_total:,.2f}</b>", cell_bold)])

    items_table = Table(items_table_data, colWidths=[0.4*inch, 3.1*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.8*inch, 1.0*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 5)
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    if tax_type == "Intra-State (CGST + SGST)":
        half_rate = total_tax_rate / 2.0
        hsn_data = [
            [Paragraph("<b>Tax Rate</b>", table_header), Paragraph("<b>Taxable Amt.</b>", table_header), Paragraph("<b>CGST Amt.</b>", table_header), Paragraph("<b>SGST Amt.</b>", table_header), Paragraph("<b>Total Tax</b>", table_header)],
            [Paragraph(f"{total_tax_rate:.1f}%", cell_style), Paragraph(f"{subtotal:,.2f}", cell_style), Paragraph(f"{cgst_amt:,.2f}", cell_style), Paragraph(f"{sgst_amt:,.2f}", cell_style), Paragraph(f"{total_tax_amt:,.2f}", cell_style)]
        ]
        hsn_table = Table(hsn_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    else:
        hsn_data = [
            [Paragraph("<b>Tax Rate</b>", table_header), Paragraph("<b>Taxable Amt.</b>", table_header), Paragraph("<b>IGST Amt.</b>", table_header), Paragraph("<b>Total Tax</b>", table_header)],
            [Paragraph(f"{total_tax_rate:.1f}%", cell_style), Paragraph(f"{subtotal:,.2f}", cell_style), Paragraph(f"{igst_amt:,.2f}", cell_style), Paragraph(f"{total_tax_amt:,.2f}", cell_style)]
        ]
        hsn_table = Table(hsn_data, colWidths=[1.8*inch, 1.9*inch, 1.9*inch, 1.9*inch])

    hsn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 4)
    ]))
    story.append(hsn_table)
    story.append(Spacer(1, 10))

    bank_details_text = f"<b>Bank Details:</b><br/>Bank Name: {firm_info.get('bank_name','')}<br/>Current A/c. No.: {firm_info.get('account_no','')} | IFSC Code: {firm_info.get('ifsc','')}"
    footer_text = f"{bank_details_text}<br/><br/><b>Terms & Conditions:</b><br/>1. Goods once sold will not be taken back.<br/>2. Subject to '{firm_info.get('jurisdiction','Muzaffarnagar')}' Jurisdiction only."
    footer_table = Table([[
        Paragraph(footer_text, header_style),
        Paragraph("<br/><br/><br/><b>Receiver's Signature</b>", ParagraphStyle('CenterSig', parent=header_style, alignment=1)),
        Paragraph(f"<b>for M/s {firm_name.upper()}</b><br/><br/><br/><b>Authorised Signatory</b>", ParagraphStyle('RightSig', parent=header_style, alignment=1))
    ]], colWidths=[3.8 * inch, 1.8 * inch, 1.9 * inch])

    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    story.append(footer_table)

    watermark_cb = make_watermark_callback(watermark_text)
    doc.build(story, onFirstPage=watermark_cb, onLaterPages=watermark_cb)

    buffer.seek(0)
    return buffer

firms_data = load_firms_config()

st.sidebar.title("TaxLedger Enterprise")
st.sidebar.caption("Cloud Invoice Workspace Suite")

st.sidebar.markdown(f"👤 **User:** `{st.session_state['username']}`")
if st.sidebar.button("🚪 Logout"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.rerun()

st.sidebar.markdown("---")
nav = st.sidebar.radio("Navigation", ["📊 Invoice Workspace", "⚙️ Manage Firms"])

if nav == "📊 Invoice Workspace":
    st.title("GST Invoice Generator")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        selected_firm = st.selectbox("Select Seller Firm", list(firms_data.keys()))
    with c2:
        inv_no = st.text_input("Invoice Number", "017/2026-27")
    with c3:
        vehicle_no = st.text_input("Vehicle No.", "UP 12 AB 1234")
    with c4:
        eway_bill_no = st.text_input("E-Way Bill No.", "351098765432")

    c5, c6, c7 = st.columns([1, 1, 1])
    with c5:
        inv_date = st.text_input("Invoice Date", "20-08-2026")
    with c6:
        place_of_supply = st.selectbox("Place of Supply (State)", STATE_CODES, index=0)
    with c7:
        watermark_text = st.text_input("Watermark Text", "ORIGINAL COPY")

    firm_info = firms_data.get(selected_firm, {})

    with st.expander("🏢 Selected Firm Structured Details", expanded=False):
        st.markdown(f"**Firm Name:** {selected_firm}")
        st.markdown(f"**GSTIN:** `{firm_info.get('gstin', 'N/A')}` | **PAN:** `{firm_info.get('pan', 'N/A')}`")
        st.markdown(f"**Address:** {firm_info.get('address', 'N/A')}")
        st.markdown(f"**Bank:** {firm_info.get('bank_name', 'N/A')} | **A/c No:** {firm_info.get('account_no', 'N/A')} | **IFSC:** {firm_info.get('ifsc', 'N/A')}")

    col_b, col_s = st.columns(2)
    with col_b:
        st.subheader("Billed To Details")
        billed_img = st.file_uploader("Upload Billed Details Image (OCR)", type=["png", "jpg", "jpeg"], key="billed_ocr")
        default_billed = "TEEBADHA TRADERS\n219, SORAV, LEHRA, Tiwaripur, Prayagraj\nGSTIN: 09AZEPT8930H1ZU"
        if billed_img:
            try:
                img = Image.open(billed_img)
                default_billed = pytesseract.image_to_string(img).strip() or default_billed
            except Exception:
                st.warning("OCR process failed.")
        billed_text = st.text_area("Billed Address", default_billed, height=100)

    with col_s:
        st.subheader("Shipped To Details")
        shipped_img = st.file_uploader("Upload Shipped Details Image (OCR)", type=["png", "jpg", "jpeg"], key="shipped_ocr")
        default_shipped = "Sh. MAHAVEER SINGHVI\nBHAGWANPUR, HARIDWAR, ROORKEE\nPIN - 247661"
        if shipped_img:
            try:
                img = Image.open(shipped_img)
                default_shipped = pytesseract.image_to_string(img).strip() or default_shipped
            except Exception:
                st.warning("OCR process failed.")
        shipped_text = st.text_area("Shipped Address", default_shipped, height=100)

    st.markdown("---")
    st.subheader("📦 Line Items & Dynamic Setup")

    # Key renamed to line_items to prevent conflict with st.session_state.items method
    if "line_items" not in st.session_state:
        st.session_state["line_items"] = [
            {"desc": "MIX MASALA (H)", "hsn": "0910", "qty": 150.0, "unit": "Kgs", "price": 60.0}
        ]

    for idx, item in enumerate(st.session_state["line_items"]):
        col_i1, col_i2, col_i3, col_i4, col_i5, col_i6 = st.columns([3, 1, 1, 1, 1, 0.5])
        with col_i1:
            item["desc"] = st.text_input(f"Item #{idx+1} Description", item["desc"], key=f"desc_{idx}")
        with col_i2:
            item["hsn"] = st.text_input(f"HSN #{idx+1}", item["hsn"], key=f"hsn_{idx}")
        with col_i3:
            item["qty"] = st.number_input(f"Qty #{idx+1}", value=float(item["qty"]), key=f"qty_{idx}")
        with col_i4:
            unit_index = UNITS_LIST.index(item["unit"]) if item["unit"] in UNITS_LIST else 0
            item["unit"] = st.selectbox(f"Unit #{idx+1}", UNITS_LIST, index=unit_index, key=f"unit_{idx}")
        with col_i5:
            item["price"] = st.number_input(f"Price #{idx+1}", value=float(item["price"]), key=f"price_{idx}")
        with col_i6:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("❌", key=f"del_{idx}"):
                if len(st.session_state["line_items"]) > 1:
                    st.session_state["line_items"].pop(idx)
                    st.rerun()

    if st.button("➕ Add Another Item"):
        st.session_state["line_items"].append({"desc": "", "hsn": "0910", "qty": 1.0, "unit": "Kgs", "price": 0.0})
        st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Tax Configuration")

    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        tax_type = st.selectbox("GST Mechanism", ["Intra-State (CGST + SGST)", "Inter-State (IGST)"])
    with t_col2:
        tax_category = st.selectbox("Tax Preset", ["5%", "18%", "Exempt (0%)", "Custom Rate"])
    with t_col3:
        if tax_category == "Exempt (0%)":
            total_tax_rate = 0.0
        elif tax_category == "5%":
            total_tax_rate = 5.0
        elif tax_category == "18%":
            total_tax_rate = 18.0
        else:
            total_tax_rate = st.number_input("Custom Tax Rate (%)", value=12.0)

    subtotal = sum(i["qty"] * i["price"] for i in st.session_state["line_items"])
    tax_amount = subtotal * (total_tax_rate / 100.0)
    grand_total = subtotal + tax_amount

    st.sidebar.markdown("---")
    st.sidebar.metric("Subtotal", f"₹{subtotal:,.2f}")
    st.sidebar.metric(f"Total Tax ({total_tax_rate:.1f}%)", f"₹{tax_amount:,.2f}")
    st.sidebar.metric("Grand Total", f"₹{grand_total:,.2f}")

    if st.button("⚡ Generate Cloud PDF Invoice", type="primary"):
        pdf_bytes = generate_pdf_bytes(
            selected_firm, inv_no, inv_date, vehicle_no, eway_bill_no, place_of_supply,
            firm_info, billed_text, shipped_text, st.session_state["line_items"],
            tax_type, total_tax_rate, watermark_text
        )
        st.download_button(
            label="💾 Download Generated Invoice PDF",
            data=pdf_bytes,
            file_name=f"Invoice_{selected_firm.replace(' ', '_')}_{inv_no.replace('/', '_')}.pdf",
            mime="application/pdf"
        )

elif nav == "⚙️ Manage Firms":
    st.title("Firm Management Directory")

    firm_action = st.radio("Action", ["Edit Existing Firm", "Add New Firm"], horizontal=True)

    if firm_action == "Edit Existing Firm":
        selected_mgr = st.selectbox("Select Firm to Modify", list(firms_data.keys()))
        info = firms_data[selected_mgr]

        m_name = st.text_input("Firm Name", selected_mgr)
        m_gstin = st.text_input("GSTIN", info.get("gstin", ""))
        m_pan = st.text_input("PAN", info.get("pan", ""))
        m_phone = st.text_input("Phone", info.get("phone", ""))
        m_addr = st.text_input("Address", info.get("address", ""))
        m_bank = st.text_input("Bank Name", info.get("bank_name", ""))
        m_acc = st.text_input("Account Number", info.get("account_no", ""))
        m_ifsc = st.text_input("IFSC Code", info.get("ifsc", ""))

        if st.button("Save Changes"):
            firms_data[m_name] = {
                "gstin": m_gstin, "pan": m_pan, "phone": m_phone,
                "address": m_addr, "bank_name": m_bank,
                "account_no": m_acc, "ifsc": m_ifsc, "jurisdiction": "Muzaffarnagar"
            }
            save_firms_config(firms_data)
            st.success(f"Updated details for '{m_name}'")

    else:
        new_name = st.text_input("New Firm Name")
        new_gstin = st.text_input("GSTIN")
        new_pan = st.text_input("PAN")
        new_phone = st.text_input("Phone")
        new_addr = st.text_input("Address")
        new_bank = st.text_input("Bank Name")
        new_acc = st.text_input("Account Number")
        new_ifsc = st.text_input("IFSC Code")

        if st.button("Register New Firm"):
            if new_name and new_name not in firms_data:
                firms_data[new_name] = {
                    "gstin": new_gstin, "pan": new_pan, "phone": new_phone,
                    "address": new_addr, "bank_name": new_bank,
                    "account_no": new_acc, "ifsc": new_ifsc, "jurisdiction": "Muzaffarnagar"
                }
                save_firms_config(firms_data)
                st.success(f"Registered firm '{new_name}'")
            else:
                st.error("Firm name is either blank or already exists.")