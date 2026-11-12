import os
from pathlib import Path
import pytest
from app.schemas import InvoiceData, InvoiceItem
from app.services.validator import InvoiceValidator
from app.services.exporter import ExporterService
from app.services.ocr_service import OCRService

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

def test_csv_and_excel_export():
    """Verify that CSV and Excel workbooks export cleanly with all columns."""
    invoice = InvoiceData(
        vendor_name="Acme Corp",
        invoice_number="INV-2026-001",
        currency="$",
        items=[
            InvoiceItem(description="Widget A", quantity=2.0, unit_price=10.0, total_price=20.0),
            InvoiceItem(description="Widget B", quantity=1.0, unit_price=15.0, total_price=15.0)
        ],
        subtotal=35.0,
        tax_amount=3.5,
        grand_total=38.5
    )
    validator = InvoiceValidator()
    val = validator.validate(invoice)

    # Test CSV
    csv_str = ExporterService.export_to_csv(invoice, val)
    assert "Invoice Number,Invoice Date,Vendor Name" in csv_str
    assert "INV-2026-001" in csv_str
    assert "Widget A" in csv_str
    assert "VALID" in csv_str

    # Test Excel
    excel_bytes = ExporterService.export_to_excel(invoice, val)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000  # valid binary XLSX package

def test_pdf_ocr_extraction():
    """Verify that PyMuPDF extracts text accurately from the generated sample PDF."""
    pdf_path = SAMPLES_DIR / "sample_invoice_valid.pdf"
    assert pdf_path.exists(), "Sample PDF must exist"

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    ocr = OCRService()
    text, engine = ocr.process_file(file_bytes, "sample_invoice_valid.pdf")

    assert "Global Cloud Hardware" in text
    assert "Server Rack Rails" in text
    assert "INV-2026-904" in text
    assert "PyMuPDF" in engine
