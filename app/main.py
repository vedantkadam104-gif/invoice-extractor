import io
import os
import time
import json
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path

from app.config import settings
from app.schemas import InvoiceData, ValidationResult, ExtractionResponse
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validator import InvoiceValidator
from app.services.exporter import ExporterService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("invoice_extractor")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Extracts structured financial data from invoices/bills using OCR + OpenRouter LLM, with arithmetic validation to catch hallucinations."
)

# Enable CORS for local dev & frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
ocr_service = OCRService(tesseract_cmd=settings.TESSERACT_CMD)
llm_service = LLMService(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
    default_model=settings.DEFAULT_MODEL
)
validator = InvoiceValidator(tolerance=settings.CALCULATION_TOLERANCE)

# Static files path for built-in web page
STATIC_DIR = Path(__file__).resolve().parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/api/health")
def health_check():
    """Check API status and available OCR backends."""
    has_tesseract = os.path.exists(settings.TESSERACT_CMD)
    has_api_key = bool(settings.OPENROUTER_API_KEY)
    
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION,
        "default_model": settings.DEFAULT_MODEL,
        "tesseract_detected": has_tesseract,
        "openrouter_key_configured": has_api_key,
        "tolerance": settings.CALCULATION_TOLERANCE
    }

@app.post("/api/extract", response_model=ExtractionResponse)
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice file (PDF or Image: JPG, PNG, WebP, etc.)"),
    model: Optional[str] = Form(None, description="OpenRouter model identifier (e.g. google/gemini-2.0-flash-001)"),
    openrouter_api_key: Optional[str] = Form(None, description="Optional OpenRouter API key override for this request")
):
    """
    Main extraction pipeline:
    1. Reads uploaded PDF or Image bytes.
    2. Runs OCR (PyMuPDF / Tesseract / EasyOCR).
    3. LLM structures messy OCR text into validated JSON.
    4. Mathematical validation verifies line items vs grand total to eliminate hallucination.
    """
    start_time = time.time()
    filename = file.filename or "uploaded_bill"

    try:
        # Read bytes reliably from file
        if hasattr(file, "file"):
            file_bytes = file.file.read()
        elif asyncio.iscoroutinefunction(file.read):
            file_bytes = await file.read()
        else:
            file_bytes = file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        # Check file size limit
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB."
            )

        # Step 1: Run OCR / Document Text Extraction
        logger.info(f"Processing document: '{filename}' ({file_size_mb:.2f} MB)")
        try:
            raw_text, ocr_engine = ocr_service.process_file(file_bytes, filename)
        except Exception as ocr_err:
            logger.error(f"OCR processing failed: {ocr_err}")
            raise HTTPException(status_code=422, detail=f"Failed to read text from file: {str(ocr_err)}")

        if not raw_text or len(raw_text.strip()) < 10:
            raise HTTPException(
                status_code=422,
                detail="Could not extract readable text from document. Please ensure the document is clear and readable."
            )

        # Step 2: LLM Extraction via OpenRouter
        logger.info(f"Sending OCR text ({len(raw_text)} chars) to OpenRouter LLM...")
        try:
            invoice_data, model_used = await llm_service.extract_invoice_data(
                ocr_text=raw_text,
                model=model,
                custom_api_key=openrouter_api_key
            )
        except Exception as llm_err:
            logger.error(f"LLM extraction failed: {llm_err}")
            raise HTTPException(status_code=502, detail=f"LLM extraction error: {str(llm_err)}")

        # Step 3: Math and Consistency Validation (Anti-Hallucination)
        validation_result = validator.validate(invoice_data)
        logger.info(f"Validation complete: status={validation_result.status}, discrepancy={validation_result.discrepancy_amount}")

        processing_duration = round((time.time() - start_time) * 1000, 2)

        return ExtractionResponse(
            success=True,
            filename=filename,
            ocr_engine_used=ocr_engine,
            raw_ocr_text=raw_text,
            data=invoice_data,
            validation=validation_result,
            model_used=model_used,
            processing_time_ms=processing_duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in extract_invoice")
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")

@app.post("/api/export/csv")
def export_csv(payload: dict):
    """
    Generate and stream CSV file for the extracted invoice.
    Accepts the invoice data + validation result in request body.
    """
    try:
        invoice = InvoiceData.model_validate(payload.get("data", payload))
        val_dict = payload.get("validation", {})
        validation = ValidationResult.model_validate(val_dict) if val_dict else validator.validate(invoice)
        
        csv_content = ExporterService.export_to_csv(invoice, validation)
        filename = f"invoice_{invoice.invoice_number or 'extracted'}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to generate CSV: {str(e)}")

@app.post("/api/export/excel")
def export_excel(payload: dict):
    """
    Generate and stream Excel (.xlsx) file with multi-tab layout.
    Accepts the invoice data + validation result in request body.
    """
    try:
        invoice = InvoiceData.model_validate(payload.get("data", payload))
        val_dict = payload.get("validation", {})
        validation = ValidationResult.model_validate(val_dict) if val_dict else validator.validate(invoice)

        excel_bytes = ExporterService.export_to_excel(invoice, validation)
        filename = f"invoice_{invoice.invoice_number or 'extracted'}.xlsx"

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to generate Excel: {str(e)}")

# Mount static files and root web interface
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_ui():
    """Serve the single-page frontend application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Invoice Extractor API is running. UI not found in static folder."}
