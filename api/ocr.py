"""
ocr.py — OCR pipeline using EasyOCR + pdf2image
Supports: JPEG, PNG, WEBP, BMP images and PDF files.
"""

from __future__ import annotations

import io
import logging
import ssl
from pathlib import Path
from typing import Union

# Fix Windows SSL certificate verification error when downloading EasyOCR models
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

import easyocr
from PIL import Image

logger = logging.getLogger(__name__)

# Store OCR models locally inside project workspace to prevent permission issues
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Initialise once at module load — EasyOCR downloads models on first use
_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        logger.info("Loading EasyOCR model (English)…")
        _reader = easyocr.Reader(
            ["en"],
            gpu=False,
            verbose=False,
            model_storage_directory=str(MODEL_DIR),
            user_network_directory=str(MODEL_DIR),
            download_enabled=True,
        )
        logger.info("EasyOCR model ready.")
    return _reader


def _ocr_image(image: Image.Image) -> str:
    """Run EasyOCR on a PIL Image and return joined text."""
    reader = _get_reader()
    # EasyOCR accepts a numpy array or file path
    import numpy as np
    img_array = np.array(image.convert("RGB"))
    results = reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(results)


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Main entry point.
    Given raw file bytes and an original filename, returns extracted text.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _extract_from_pdf(file_bytes)
    else:
        # Treat as image
        return _extract_from_image(file_bytes)


def _extract_from_image(file_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(file_bytes))
    text = _ocr_image(image)
    logger.debug("OCR image → %d chars", len(text))
    return text


def _extract_from_pdf(file_bytes: bytes) -> str:
    """Convert PDF pages to images then OCR each page."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise RuntimeError(
            "pdf2image is not installed. Add it to requirements.txt."
        )

    logger.info("Converting PDF to images…")
    pages: list[Image.Image] = convert_from_bytes(file_bytes, dpi=200)
    logger.info("PDF has %d page(s).", len(pages))

    all_text: list[str] = []
    for i, page in enumerate(pages):
        logger.debug("OCR-ing page %d/%d…", i + 1, len(pages))
        all_text.append(_ocr_image(page))

    combined = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
    logger.debug("PDF OCR total → %d chars", len(combined))
    return combined
