import io
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import UploadFile
from app.main import health_check, export_csv, export_excel, extract_invoice

SAMPLES_DIR = PROJECT_ROOT / "samples"

def test_health_endpoint():
    """Verify health endpoint returns status and configuration."""
    print("Testing health endpoint...")
    data = health_check()
    assert data["status"] == "healthy"
    assert "default_model" in data
    assert "tolerance" in data

def test_export_csv_endpoint():
    """Verify CSV export endpoint returns proper CSV attachment."""
    print("Testing export CSV endpoint...")
    payload = {
        "data": {
            "vendor_name": "Fast Food Mart",
            "invoice_number": "FF-100",
            "grand_total": 50.0,
            "items": [
                {"description": "Burger Combo", "quantity": 2.0, "unit_price": 25.0, "total_price": 50.0}
            ]
        }
    }
    response = export_csv(payload)
    assert response.status_code == 200
    assert response.media_type == "text/csv"
    assert "Burger Combo" in response.body.decode("utf-8")

def test_export_excel_endpoint():
    """Verify Excel export endpoint returns .xlsx attachment."""
    print("Testing export Excel endpoint...")
    payload = {
        "data": {
            "vendor_name": "Fast Food Mart",
            "invoice_number": "FF-100",
            "grand_total": 50.0,
            "items": [
                {"description": "Burger Combo", "quantity": 2.0, "unit_price": 25.0, "total_price": 50.0}
            ]
        }
    }
    response = export_excel(payload)
    assert response.status_code == 200
    assert "spreadsheetml" in response.media_type
    assert len(response.body) > 1000

def test_extract_invoice_endpoint_with_sample_pdf(monkeypatch):
    """Verify extract_invoice processes an uploaded PDF end-to-end."""
    print("Testing extract invoice with PDF...")
    import app.main
    monkeypatch.setattr(app.main.llm_service, "api_key", "")

    pdf_path = SAMPLES_DIR / "sample_invoice_valid.pdf"
    assert pdf_path.exists()

    with open(pdf_path, "rb") as f:
        content = f.read()

    upload_file = UploadFile(
        file=io.BytesIO(content),
        filename="sample_invoice_valid.pdf",
        headers={"content-type": "application/pdf"}
    )

    response = asyncio.run(extract_invoice(file=upload_file, model="google/gemini-2.0-flash-001"))
    assert response.success is True
    assert "Global Cloud Hardware" in response.raw_ocr_text
    assert response.data is not None
    assert response.validation is not None
    assert response.validation.calculated_items_sum > 0
