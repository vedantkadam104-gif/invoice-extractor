"""Generate realistic sample invoices in PDF and PNG formats for testing."""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image, ImageDraw, ImageFont

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

def create_sample_pdf(filename: str, vendor: str, inv_no: str, date: str, items: list, subtotal: float, tax: float, grand_total: float):
    pdf_path = SAMPLES_DIR / filename
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Title & Vendor
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1F4E78'), spaceAfter=4)
    story.append(Paragraph(vendor, title_style))
    story.append(Paragraph("108 Tech Park Avenue, Suite 400, Austin TX 78701 | Phone: (512) 555-0199", styles['Normal']))
    story.append(Paragraph("Tax ID / GSTIN: TX-99281740-B", styles['Normal']))
    story.append(Spacer(1, 15))

    # Invoice Metadata Table
    meta_data = [
        [Paragraph(f"<b>Invoice #:</b> {inv_no}", styles['Normal']), Paragraph(f"<b>Date:</b> {date}", styles['Normal'])],
        [Paragraph("<b>Billed To:</b> Acme Corp / Accounts Dept", styles['Normal']), Paragraph("<b>Due Date:</b> 2026-06-01", styles['Normal'])]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F2F4F7')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))

    # Items Table
    table_data = [["#", "Item Description", "Qty", "Unit Price", "Total Price"]]
    for idx, (desc, qty, unit_p, total_p) in enumerate(items, 1):
        table_data.append([str(idx), desc, str(qty), f"${unit_p:.2f}", f"${total_p:.2f}"])

    table_data.append(["", "", "", "Subtotal:", f"${subtotal:.2f}"])
    table_data.append(["", "", "", "Tax (10%):", f"${tax:.2f}"])
    table_data.append(["", "", "", "Grand Total:", f"${grand_total:.2f}"])

    items_table = Table(table_data, colWidths=[30, 270, 60, 90, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, len(items)), 0.5, colors.HexColor('#D0D5DD')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, len(items) + 1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (3, len(items) + 1), (-1, len(items) + 1), 1, colors.HexColor('#1F4E78')),
        ('LINEBELOW', (3, -1), (-1, -1), 1.5, colors.HexColor('#1F4E78')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>Terms:</b> Payment due within 30 days. Thank you for your business!", styles['Italic']))

    doc.build(story)
    print(f"Generated PDF: {pdf_path}")

def create_sample_receipt_image(filename: str, vendor: str, inv_no: str, items: list, subtotal: float, tax: float, grand_total: float):
    img_path = SAMPLES_DIR / filename
    width, height = 500, 650
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Simple line-drawing receipt
    draw.rectangle([10, 10, width - 10, height - 10], outline="#475569", width=2)
    
    y = 30
    draw.text((width // 2, y), vendor.upper(), fill="black", anchor="mm")
    y += 25
    draw.text((width // 2, y), "33 MARKET SQUARE, BLDG B", fill="#333333", anchor="mm")
    y += 20
    draw.text((width // 2, y), f"RECEIPT: {inv_no}   DATE: 2026-05-11", fill="#333333", anchor="mm")
    y += 20
    draw.line([(30, y), (width - 30, y)], fill="#94A3B8", width=1)
    y += 25

    # Columns header
    draw.text((30, y), "ITEM", fill="black")
    draw.text((280, y), "QTY", fill="black")
    draw.text((350, y), "PRICE", fill="black")
    draw.text((430, y), "TOTAL", fill="black")
    y += 18
    draw.line([(30, y), (width - 30, y)], fill="#CBD5E1", width=1)
    y += 20

    for desc, qty, unit_p, total_p in items:
        draw.text((30, y), desc[:24], fill="#1E293B")
        draw.text((290, y), str(qty), fill="#1E293B")
        draw.text((350, y), f"{unit_p:.2f}", fill="#1E293B")
        draw.text((430, y), f"{total_p:.2f}", fill="#1E293B")
        y += 26

    y += 10
    draw.line([(30, y), (width - 30, y)], fill="#94A3B8", width=1)
    y += 20

    draw.text((280, y), "SUBTOTAL:", fill="black")
    draw.text((430, y), f"${subtotal:.2f}", fill="black")
    y += 22
    draw.text((280, y), "TAX (8%):", fill="black")
    draw.text((430, y), f"${tax:.2f}", fill="black")
    y += 24
    draw.line([(280, y), (width - 30, y)], fill="black", width=2)
    y += 15
    draw.text((280, y), "GRAND TOTAL:", fill="black")
    draw.text((420, y), f"${grand_total:.2f}", fill="black")

    y += 45
    draw.text((width // 2, y), "*** THANK YOU FOR YOUR VISIT ***", fill="#475569", anchor="mm")

    img.save(str(img_path))
    print(f"Generated Image: {img_path}")

if __name__ == "__main__":
    # Sample 1: Valid PDF
    create_sample_pdf(
        filename="sample_invoice_valid.pdf",
        vendor="Global Cloud Hardware Inc.",
        inv_no="INV-2026-904",
        date="2026-05-10",
        items=[
            ("Server Rack Rails 1U", 2, 45.00, 90.00),
            ("Cat6e Ethernet Cable 50ft", 5, 12.00, 60.00),
            ("Gigabit 8-Port Switch", 1, 150.00, 150.00),
        ],
        subtotal=300.00,
        tax=30.00,
        grand_total=330.00  # 300 + 30 = 330 (Math matches!)
    )

    # Sample 2: Mismatch PDF (Tampered/Discrepancy)
    create_sample_pdf(
        filename="sample_invoice_mismatch.pdf",
        vendor="Apex Industrial Supplies",
        inv_no="INV-2026-999-TAMPERED",
        date="2026-05-11",
        items=[
            ("Hydraulic Pressure Gauge", 1, 120.00, 120.00),
            ("Replacement Gasket Set", 2, 35.00, 70.00),
        ],
        subtotal=190.00,
        tax=19.00,
        grand_total=275.00  # Stated total 275 vs Expected 209 (Discrepancy: $66)
    )

    # Sample 3: Valid Receipt Image
    create_sample_receipt_image(
        filename="sample_receipt_valid.png",
        vendor="QuickBite Cafe & Bakery",
        inv_no="QB-4821",
        items=[
            ("Artisan Sourdough Loaf", 2, 7.50, 15.00),
            ("Cold Brew Coffee 16oz", 2, 4.50, 9.00),
            ("Almond Croissant", 1, 5.00, 5.00),
        ],
        subtotal=29.00,
        tax=2.32,
        grand_total=31.32  # 29 + 2.32 = 31.32 (Math matches!)
    )
