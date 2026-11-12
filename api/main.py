"""
main.py — FastAPI application for the Invoice/Bill Data Extractor.

Endpoints:
  POST /extract              — Upload image or PDF, returns extracted JSON
  GET  /results/{id}         — Fetch a previously extracted result by ID
  GET  /download/{id}/csv    — Download result as CSV
  GET  /download/{id}/excel  — Download result as Excel (.xlsx)
  GET  /health               — Health check
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

load_dotenv()

from exporter import to_csv_bytes, to_excel_bytes
from llm import InvoiceData, extract_invoice_data
from ocr import extract_text_from_bytes
from validator import ValidationResult, validate_invoice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QuickInvoice AI API",
    description="Upload a bill image or PDF and get back clean, validated JSON data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory result store: { id -> { "data": InvoiceData, "validation": ValidationResult, "raw_text": str } }
_results: dict[str, dict[str, Any]] = {}

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/bmp",
    "application/pdf",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".pdf"}


def _assert_allowed(file: UploadFile) -> None:
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """
    Upload an invoice image or PDF.
    Returns structured invoice data + validation result.
    """
    _assert_allowed(file)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info("Received file: %s (%d bytes)", file.filename, len(file_bytes))

    # 1. OCR
    try:
        raw_text = extract_text_from_bytes(file_bytes, file.filename or "upload")
    except Exception as e:
        logger.exception("OCR failed")
        raise HTTPException(status_code=422, detail=f"OCR failed: {e}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the file. Try a clearer image.",
        )

    # 2. LLM extraction
    try:
        invoice_data: InvoiceData = await extract_invoice_data(raw_text)
    except Exception as e:
        logger.exception("LLM extraction failed")
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")

    # 3. Validation
    validation: ValidationResult = validate_invoice(invoice_data)

    # 4. Store result
    result_id = str(uuid.uuid4())
    _results[result_id] = {
        "data": invoice_data,
        "validation": validation,
        "raw_text": raw_text,
    }

    logger.info("Extraction complete. ID=%s valid=%s", result_id, validation.is_valid)

    return _build_response(result_id, invoice_data, validation, raw_text)


@app.get("/results/{result_id}")
async def get_result(result_id: str):
    """Fetch a previously extracted result by its ID."""
    entry = _results.get(result_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Result not found.")
    return _build_response(
        result_id, entry["data"], entry["validation"], entry["raw_text"]
    )


@app.get("/download/{result_id}/csv")
async def download_csv(result_id: str):
    """Download extracted invoice data as CSV."""
    entry = _results.get(result_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Result not found.")
    csv_bytes = to_csv_bytes(entry["data"])
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="invoice_{result_id[:8]}.csv"'},
    )


@app.get("/download/{result_id}/excel")
async def download_excel(result_id: str):
    """Download extracted invoice data as Excel (.xlsx)."""
    entry = _results.get(result_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Result not found.")
    excel_bytes = to_excel_bytes(entry["data"])
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="invoice_{result_id[:8]}.xlsx"'},
    )


def _build_response(
    result_id: str,
    data: InvoiceData,
    validation: ValidationResult,
    raw_text: str,
) -> dict:
    return {
        "id": result_id,
        "vendor": data.vendor,
        "date": data.date,
        "invoice_number": data.invoice_number,
        "items": [item.model_dump() for item in data.items],
        "subtotal": data.subtotal,
        "tax": data.tax,
        "total": data.total,
        "is_valid": validation.is_valid,
        "validation_notes": validation.notes,
        "raw_text_preview": raw_text[:500],
    }
