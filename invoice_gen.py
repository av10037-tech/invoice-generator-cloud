import os
import json
import io
import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="TaxLedger Enterprise Cloud", page_icon="🔒", layout="wide")

CONFIG_FILE = "firms.json"
HISTORY_FILE = "invoice_history.json"

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

def load_invoice_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]
                elif isinstance(data, dict):
                    converted = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            v["firm_name"] = k
                            converted.append(v)
                    return converted
        except Exception:
            return []
    return []

def save_invoice_history(record):
    history = load_invoice_history()
    updated = False
    
    for idx, item in enumerate(history):
        if isinstance(item, dict) and item.get("inv_no") == record.get("inv_no") and item.get("firm_name") == record.get("firm_name"):
            history[idx] = record
            updated = True
            break
            
    if not updated:
        history.append(record)
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def make_watermark_callback(watermark_text):
    def draw_watermark(canvas, doc):
        if not watermark_text.strip():
            return
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 45)
        canvas.setFillColor(colors.HexColor('#F1F5F9'))
        canvas.translate(doc.pagesize[0] / 2.0, doc.pagesize[1] / 2.0)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text.upper())
        canvas.restoreState()
    return draw_watermark

# FULL-PAGE PDF GENERATOR ENGINE
def generate_pdf_bytes(firm_name, inv_no, date, vehicle_no, eway_bill_no, place_of_supply, firm_info, billed_text, shipped_text, items_list, tax_type, total_tax_rate, watermark_text):
    buffer = io.BytesIO()
    margin = 28.0
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )
    styles = getSampleStyleSheet()

    PINK_ACCENT = colors.HexColor('#E11D48')
    DARK_TEXT = colors.HexColor('#0F172A')
    MUTED_TEXT = colors.HexColor('#64748B')
    HEADER_BG = colors.HexColor('#475569')
    ROW_BG_ALT = colors.HexColor('#F8FAFC')
    LINE_COLOR = colors.HexColor('#E2E8F0')

    title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=28, leading=32, textColor=PINK_ACCENT)
    meta_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=MUTED_TEXT)
    meta_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=DARK_TEXT)
    
    body_muted = ParagraphStyle('BodyMuted', fontName='Helvetica', fontSize=8.5, leading=12, textColor=MUTED_TEXT)
    body_dark = ParagraphStyle('BodyDark', fontName='Helvetica', fontSize=8.5, leading=12, textColor=DARK_TEXT)
    
    tbl_hdr_style = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=colors.white)
    tbl_cell_style = ParagraphStyle('TblCell', fontName='Helvetica', fontSize=8.5, leading=11, textColor=DARK_TEXT)
    tbl_cell_right = ParagraphStyle('TblCellR', parent=tbl_cell_style, alignment=2)

    story = []

    seller_html = f"<b>M/s {firm_name.upper()}</b><br/>{firm_info.get('address','')}<br/><b>GSTIN:</b> {firm_info.get('gstin','')} | <b>PAN:</b> {firm_info.get('pan','')}"
    if firm_info.get("phone"):
        seller_html += f"<br/>Tel: {firm_info.get('phone','')}"

    left_header = [
        Paragraph("Invoice", title_style),
        Spacer(1, 8),
        Table([
            [Paragraph("NO.", meta_label), Paragraph("DATE", meta_label), Paragraph("DUE / VEHICLE", meta_label), Paragraph("E-WAY BILL", meta_label)],
            [Paragraph(f"#{inv_no}", meta_val), Paragraph(date, meta_val), Paragraph(vehicle_no or "N/A", meta_val), Paragraph(eway_bill_no or "N/A", meta_val)]
        ], colWidths=[1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    ]
    left_header[2].setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,0), 2)
    ]))

    top_table = Table([[left_header, Paragraph(seller_html, ParagraphStyle('SellerTxt', parent=body_dark, alignment=2))]], colWidths=[4.5*inch, 3.2*inch])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(top_table)
    story.append(Spacer(1, 8))

    billed_formatted = billed_text.replace('\n', '<br/>')
    shipped_formatted = shipped_text.replace('\n', '<br/>')

    billed_p = Paragraph(f"<font color='#64748B'><b>BILLED TO:</b></font><br/>{billed_formatted}", body_dark)
    shipped_p = Paragraph(f"<font color='#64748B'><b>SHIPPED TO:</b></font><br/>{shipped_formatted}<br/><b>Place of Supply:</b> {place_of_supply}", body_dark)

    addr_table = Table([[billed_p, shipped_p]], colWidths=[4.2*inch, 3.5*inch])
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 8))

    tbl_data = [
        [
            Paragraph("Item & Description", tbl_hdr_style),
            Paragraph("HSN/SAC", tbl_hdr_style),
            Paragraph("Qty", ParagraphStyle('HdrC', parent=tbl_hdr_style, alignment=1)),
            Paragraph("Unit", ParagraphStyle('HdrC', parent=tbl_hdr_style, alignment=1)),
            Paragraph("Price (Rs.)", ParagraphStyle('HdrR', parent=tbl_hdr_style, alignment=2)),
            Paragraph("Amount (Rs.)", ParagraphStyle('HdrR', parent=tbl_hdr_style, alignment=2))
        ]
    ]

    subtotal = 0.0
    actual_count = len(items_list)
    TOTAL_ROWS = 14 
    
    row_heights = [20]
    for idx in range(TOTAL_ROWS - 1):
        row_heights.append(22)
        if idx < actual_count:
            item = items_list[idx]
            amt = item["qty"] * item["price"]
            subtotal += amt
            tbl_data.append([
                Paragraph(f"<b>{item['desc']}</b>", tbl_cell_style),
                Paragraph(item["hsn"], tbl_cell_style),
                Paragraph(f"{item['qty']:.2f}", ParagraphStyle('C', parent=tbl_cell_style, alignment=1)),
                Paragraph(item["unit"], ParagraphStyle('C', parent=tbl_cell_style, alignment=1)),
                Paragraph(f"{item['price']:,.2f}", tbl_cell_right),
                Paragraph(f"{amt:,.2f}", tbl_cell_right)
            ])
        else:
            tbl_data.append(["", "", "", "", "", ""])

    items_table = Table(tbl_data, colWidths=[3.2*inch, 0.9*inch, 0.7*inch, 0.6*inch, 1.1*inch, 1.2*inch], rowHeights=row_heights)
    
    ts = [
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, LINE_COLOR)
    ]
    for r in range(1, len(tbl_data)):
        if r % 2 == 0:
            ts.append(('BACKGROUND', (0, r), (-1, r), ROW_BG_ALT))

    items_table.setStyle(TableStyle(ts))
    story.append(items_table)
    story.append(Spacer(1, 10))

    if tax_type == "Intra-State (CGST + SGST)":
        half_rate = total_tax_rate / 2.0
        cgst_amt = subtotal * (half_rate / 100.0)
        sgst_amt = subtotal * (half_rate / 100.0)
        tot_tax = cgst_amt + sgst_amt
        grand_tot = subtotal + tot_tax

        totals_data = [
            [Paragraph("SUBTOTAL", ParagraphStyle('R1', parent=body_muted, alignment=2)), Paragraph(f"Rs. {subtotal:,.2f}", tbl_cell_right)],
            [Paragraph(f"CGST ({half_rate:.1f}%)", ParagraphStyle('R2', parent=body_muted, alignment=2)), Paragraph(f"Rs. {cgst_amt:,.2f}", tbl_cell_right)],
            [Paragraph(f"SGST ({half_rate:.1f}%)", ParagraphStyle('R3', parent=body_muted, alignment=2)), Paragraph(f"Rs. {sgst_amt:,.2f}", tbl_cell_right)],
            [Paragraph("<b>TOTAL</b>", ParagraphStyle('R4', parent=body_dark, alignment=2)), Paragraph(f"<b>Rs. {grand_tot:,.2f}</b>", ParagraphStyle('R5', parent=meta_val, alignment=2))]
        ]
    else:
        igst_amt = subtotal * (total_tax_rate / 100.0)
        tot_tax = igst_amt
        grand_tot = subtotal + tot_tax

        totals_data = [
            [Paragraph("SUBTOTAL", ParagraphStyle('R1', parent=body_muted, alignment=2)), Paragraph(f"Rs. {subtotal:,.2f}", tbl_cell_right)],
            [Paragraph(f"IGST ({total_tax_rate:.1f}%)", ParagraphStyle('R2', parent=body_muted, alignment=2)), Paragraph(f"Rs. {igst_amt:,.2f}", tbl_cell_right)],
            [Paragraph("<b>TOTAL</b>", ParagraphStyle('R4', parent=body_dark, alignment=2)), Paragraph(f"<b>Rs. {grand_tot:,.2f}</b>", ParagraphStyle('R5', parent=meta_val, alignment=2))]
        ]

    totals_table = Table(totals_data, colWidths=[2.2*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,-1), (-1,-1), 1, PINK_ACCENT)
    ]))

    right_aligned_totals = Table([["", totals_table]], colWidths=[4.0*inch, 3.7*inch])
    right_aligned_totals.setStyle(TableStyle([('PADDING', (0,0), (-1,-1), 0)]))
    story.append(right_aligned_totals)
    story.append(Spacer(1, 10))

    pink_line = Table([[""]], colWidths=[7.7*inch])
    pink_line.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 2, PINK_ACCENT)]))
    story.append(pink_line)
    story.append(Spacer(1, 8))

    bank_info = f"<b>Payment Details:</b> {firm_info.get('bank_name','')} | A/c: {firm_info.get('account_no','')} | IFSC: {firm_info.get('ifsc','')}"
    
    footer_table = Table([[
        Paragraph(f"{bank_info}<br/><br/><font size=7.5 color='#64748B'>1. Goods once sold will not be taken back.<br/>2. Subject to '{firm_info.get('jurisdiction','Muzaffarnagar')}' Jurisdiction.</font>", body_dark),
        Paragraph(f"<b>for M/s {firm_name.upper()}</b><br/><br/><br/><b>Authorised Signatory</b>", ParagraphStyle('SigR', parent=body_dark, alignment=2))
    ]], colWidths=[5.0*inch, 2.7*inch])
    
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0)
    ]))
    story.append(footer_table)

    watermark_cb = make_watermark_callback(watermark_text)
    doc.build(story, onFirstPage=watermark_cb, onLaterPages=watermark_cb)

    buffer.seek(0)
    return buffer

firms_data = load_firms_config()

# Safe Callback Reset Function for Clear Workspace Button
def clear_workspace_callback():
    st.session_state["line_items"] = [{"desc": "", "hsn": "", "qty": 1.0, "unit": "Kgs", "price": 0.0}]
    st.session_state["billed_text"] = ""
    st.session_state["shipped_text"] = ""
    st.session_state["vehicle_no"] = ""
    st.session_state["eway_bill_no"] = ""

    # Purge all line item specific widget cached keys
    keys_to_delete = [k for k in st.session_state.keys() if any(k.startswith(prefix) for prefix in ["desc_", "hsn_", "qty_", "unit_", "price_"])]
    for key in keys_to_delete:
        del st.session_state[key]

st.sidebar.title("TaxLedger Enterprise")
st.sidebar.caption("Cloud Invoice Workspace Suite")

st.sidebar.markdown(f"👤 **User:** `{st.session_state['username']}`")
if st.sidebar.button("🚪 Logout"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.rerun()

st.sidebar.markdown("---")
nav = st.sidebar.radio("Navigation", ["📊 Invoice Workspace", "📈 Firm Analytics Dashboard", "✏️ Edit / Revise Invoices", "⚙️ Manage Firms"])

# NAV 1: INVOICE WORKSPACE
if nav == "📊 Invoice Workspace":
    st.title("GST Invoice Generator")

    if "billed_text" not in st.session_state:
        st.session_state["billed_text"] = "TEEBADHA TRADERS\n219, SORAV, LEHRA, Tiwaripur, Prayagraj\nGSTIN: 09AZEPT8930H1ZU"
    if "shipped_text" not in st.session_state:
        st.session_state["shipped_text"] = "Sh. MAHAVEER SINGHVI\nBHAGWANPUR, HARIDWAR, ROORKEE\nPIN - 247661"
    if "vehicle_no" not in st.session_state:
        st.session_state["vehicle_no"] = "UP 12 AB 1234"
    if "eway_bill_no" not in st.session_state:
        st.session_state["eway_bill_no"] = "351098765432"

    header_cols = st.columns([2, 1, 1, 1])
    with header_cols[0]:
        selected_firm = st.selectbox("Select Seller Firm", list(firms_data.keys()))
    with header_cols[1]:
        inv_no = st.text_input("Invoice Number", "017/2026-27")
    with header_cols[2]:
        vehicle_no = st.text_input("Vehicle No.", key="vehicle_no")
    with header_cols[3]:
        eway_bill_no = st.text_input("E-Way Bill No.", key="eway_bill_no")

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
        if billed_img:
            try:
                img = Image.open(billed_img)
                st.session_state["billed_text"] = pytesseract.image_to_string(img).strip() or st.session_state["billed_text"]
            except Exception:
                st.warning("OCR process failed.")
        billed_text = st.text_area("Billed Address", key="billed_text", height=100)

    with col_s:
        st.subheader("Shipped To Details")
        shipped_img = st.file_uploader("Upload Shipped Details Image (OCR)", type=["png", "jpg", "jpeg"], key="shipped_ocr")
        if shipped_img:
            try:
                img = Image.open(shipped_img)
                st.session_state["shipped_text"] = pytesseract.image_to_string(img).strip() or st.session_state["shipped_text"]
            except Exception:
                st.warning("OCR process failed.")
        shipped_text = st.text_area("Shipped Address", key="shipped_text", height=100)

    st.markdown("---")
    st.subheader("📦 Line Items & Dynamic Setup")

    if "line_items" not in st.session_state:
        st.session_state["line_items"] = [
            {"desc": "MIX MASALA (H)", "hsn": "0910", "qty": 150.0, "unit": "Kgs", "price": 60.0}
        ]

    for idx, item in enumerate(st.session_state["line_items"]):
        col_i1, col_i2, col_i3, col_i4, col_i5, col_i6 = st.columns([3, 1, 1, 1, 1, 0.5])
        with col_i1:
            item["desc"] = st.text_input(f"Item #{idx+1} Description", value=item["desc"], key=f"desc_{idx}")
        with col_i2:
            item["hsn"] = st.text_input(f"HSN #{idx+1}", value=item["hsn"], key=f"hsn_{idx}")
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

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("➕ Add Another Item"):
            st.session_state["line_items"].append({"desc": "", "hsn": "", "qty": 1.0, "unit": "Kgs", "price": 0.0})
            st.rerun()
    with col_btn2:
        st.button("🧹 Clear All Workspace Data", on_click=clear_workspace_callback)

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

        record = {
            "firm_name": selected_firm,
            "inv_no": inv_no,
            "date": inv_date,
            "vehicle_no": vehicle_no,
            "eway_bill_no": eway_bill_no,
            "place_of_supply": place_of_supply,
            "billed_text": billed_text,
            "shipped_text": shipped_text,
            "line_items": st.session_state["line_items"],
            "tax_type": tax_type,
            "total_tax_rate": total_tax_rate,
            "watermark_text": watermark_text,
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "grand_total": grand_total
        }
        save_invoice_history(record)

        st.download_button(
            label="💾 Download Generated Invoice PDF",
            data=pdf_bytes,
            file_name=f"Invoice_{selected_firm.replace(' ', '_')}_{inv_no.replace('/', '_')}.pdf",
            mime="application/pdf"
        )

# NAV 2: FIRM ANALYTICS DASHBOARD
elif nav == "📈 Firm Analytics Dashboard":
    st.title("Firm Invoice Generation Analytics")

    history = load_invoice_history()
    all_firms = list(firms_data.keys())

    if not history:
        st.info("No invoices generated yet. Create invoices from the workspace to view analytics.")
    else:
        df = pd.DataFrame(history)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invoices Generated", len(df))
        m2.metric("Active Firms Billed", df["firm_name"].nunique() if "firm_name" in df.columns else 0)
        m3.metric("Total Billed Revenue", f"₹{df['grand_total'].sum():,.2f}" if "grand_total" in df.columns else "₹0.00")

        st.markdown("---")
        st.subheader("Invoice Distribution per Firm")

        if "firm_name" in df.columns and "grand_total" in df.columns:
            summary_df = df.groupby("firm_name").agg(
                Invoice_Count=("inv_no", "count"),
                Total_Billed=("grand_total", "sum")
            ).reset_index()

            for f_name in all_firms:
                if f_name not in summary_df["firm_name"].values:
                    summary_df = pd.concat([summary_df, pd.DataFrame([{"firm_name": f_name, "Invoice_Count": 0, "Total_Billed": 0.0}])], ignore_index=True)

            summary_df = summary_df.sort_values(by="Invoice_Count", ascending=False)

            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.dataframe(
                    summary_df.style.format({"Total_Billed": "₹{:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )

            with col_right:
                st.bar_chart(summary_df.set_index("firm_name")["Invoice_Count"])

# NAV 3: EDIT / REVISE INVOICES
elif nav == "✏️ Edit / Revise Invoices":
    st.title("Edit & Revise Generated Invoices")

    history = load_invoice_history()

    if not history:
        st.warning("No generated invoices found in history to edit.")
    else:
        invoice_options = [f"{item.get('firm_name', 'Unknown')} - Invoice #{item.get('inv_no', 'N/A')} ({item.get('date', '')})" for item in history]
        selected_option = st.selectbox("Select Invoice to Modify", invoice_options)

        selected_idx = invoice_options.index(selected_option)
        rec = history[selected_idx]

        st.markdown("---")
        st.subheader(f"Editing Invoice #{rec.get('inv_no')} ({rec.get('firm_name')})")

        e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
        with e1:
            current_firm = rec.get("firm_name", list(firms_data.keys())[0])
            firm_idx = list(firms_data.keys()).index(current_firm) if current_firm in firms_data else 0
            e_firm = st.selectbox("Seller Firm", list(firms_data.keys()), index=firm_idx)
        with e2:
            e_inv_no = st.text_input("Invoice Number", rec.get("inv_no", ""))
        with e3:
            e_vehicle_no = st.text_input("Vehicle No.", rec.get("vehicle_no", ""))
        with e4:
            e_eway_bill_no = st.text_input("E-Way Bill No.", rec.get("eway_bill_no", ""))

        e5, e6, e7 = st.columns([1, 1, 1])
        with e5:
            e_date = st.text_input("Invoice Date", rec.get("date", ""))
        with e6:
            p_idx = STATE_CODES.index(rec.get("place_of_supply")) if rec.get("place_of_supply") in STATE_CODES else 0
            e_place_of_supply = st.selectbox("Place of Supply (State)", STATE_CODES, index=p_idx)
        with e7:
            e_watermark = st.text_input("Watermark Text", rec.get("watermark_text", "ORIGINAL COPY"))

        col_eb, col_es = st.columns(2)
        with col_eb:
            e_billed_text = st.text_area("Billed Address", rec.get("billed_text", ""), height=100)
        with col_es:
            e_shipped_text = st.text_area("Shipped Address", rec.get("shipped_text", ""), height=100)

        st.subheader("Line Items")
        e_items = rec.get("line_items", [])

        updated_items = []
        for idx, item in enumerate(e_items):
            ci1, ci2, ci3, ci4, ci5 = st.columns([3, 1, 1, 1, 1])
            with ci1:
                u_desc = st.text_input(f"Item #{idx+1} Description", item.get("desc", ""), key=f"edit_desc_{idx}")
            with ci2:
                u_hsn = st.text_input(f"HSN #{idx+1}", item.get("hsn", ""), key=f"edit_hsn_{idx}")
            with ci3:
                u_qty = st.number_input(f"Qty #{idx+1}", value=float(item.get("qty", 1.0)), key=f"edit_qty_{idx}")
            with ci4:
                u_unit_idx = UNITS_LIST.index(item.get("unit")) if item.get("unit") in UNITS_LIST else 0
                u_unit = st.selectbox(f"Unit #{idx+1}", UNITS_LIST, index=u_unit_idx, key=f"edit_unit_{idx}")
            with ci5:
                u_price = st.number_input(f"Price #{idx+1}", value=float(item.get("price", 0.0)), key=f"edit_price_{idx}")

            updated_items.append({"desc": u_desc, "hsn": u_hsn, "qty": u_qty, "unit": u_unit, "price": u_price})

        st.subheader("Tax Configuration")
        tc1, tc2 = st.columns(2)
        with tc1:
            e_tax_type = st.selectbox("GST Mechanism", ["Intra-State (CGST + SGST)", "Inter-State (IGST)"], index=0 if rec.get("tax_type") == "Intra-State (CGST + SGST)" else 1)
        with tc2:
            e_tax_rate = st.number_input("Tax Rate (%)", value=float(rec.get("total_tax_rate", 5.0)))

        firm_info = firms_data.get(e_firm, {})

        if st.button("💾 Save Changes & Re-Generate PDF", type="primary"):
            revised_pdf = generate_pdf_bytes(
                e_firm, e_inv_no, e_date, e_vehicle_no, e_eway_bill_no, e_place_of_supply,
                firm_info, e_billed_text, e_shipped_text, updated_items,
                e_tax_type, e_tax_rate, e_watermark
            )

            subtotal = sum(i["qty"] * i["price"] for i in updated_items)
            tax_amount = subtotal * (e_tax_rate / 100.0)
            grand_total = subtotal + tax_amount

            updated_record = {
                "firm_name": e_firm,
                "inv_no": e_inv_no,
                "date": e_date,
                "vehicle_no": e_vehicle_no,
                "eway_bill_no": e_eway_bill_no,
                "place_of_supply": e_place_of_supply,
                "billed_text": e_billed_text,
                "shipped_text": e_shipped_text,
                "line_items": updated_items,
                "tax_type": e_tax_type,
                "total_tax_rate": e_tax_rate,
                "watermark_text": e_watermark,
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "grand_total": grand_total
            }
            save_invoice_history(updated_record)
            st.success("Invoice successfully updated and saved!")

            st.download_button(
                label="💾 Download Revised Invoice PDF",
                data=revised_pdf,
                file_name=f"Invoice_{e_firm.replace(' ', '_')}_{e_inv_no.replace('/', '_')}.pdf",
                mime="application/pdf"
            )

# NAV 4: MANAGE FIRMS
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