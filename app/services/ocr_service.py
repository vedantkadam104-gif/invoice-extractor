import io
import os
import shutil
import logging
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd
        self._easyocr_reader = None
        self._pytesseract_configured = False

    def _setup_tesseract(self):
        """Configure pytesseract binary path lazily when needed."""
        if self._pytesseract_configured:
            return
        try:
            import pytesseract
            if self.tesseract_cmd and os.path.exists(self.tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            elif shutil.which("tesseract"):
                pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")
            self._pytesseract_configured = True
        except ImportError:
            pass

    def _get_easyocr_reader(self):
        """Lazy load EasyOCR reader if installed."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                # default to English
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False)
            except Exception as e:
                logger.warning(f"EasyOCR could not be initialized: {e}")
                self._easyocr_reader = False
        return self._easyocr_reader if self._easyocr_reader is not False else None

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast and sharpness for optimal OCR reading."""
        try:
            # Convert to grayscale
            gray = image.convert("L")
            # Increase contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.8)
            # Apply slight sharpening
            sharpened = enhanced.filter(ImageFilter.SHARPEN)
            return sharpened
        except Exception as e:
            logger.warning(f"Image preprocessing skipped due to error: {e}")
            return image

    def extract_text_from_pdf(self, file_bytes: bytes) -> Tuple[str, str]:
        """
        Extract text from a PDF file.
        First tries digital text extraction (fast and 100% accurate).
        If digital text is missing or sparse (< 50 chars), renders pages to images and runs OCR.
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_pages = []
            total_chars = 0

            # Step 1: Try reading native embedded text
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    extracted_pages.append(f"--- Page {page_num + 1} ---\n{text.strip()}")
                    total_chars += len(text.strip())

            # If substantial text was found, return it as native PDF text
            if total_chars > 60:
                return "\n\n".join(extracted_pages), "PyMuPDF (Native Digital PDF)"

            # Step 2: PDF is likely scanned / image-based -> render pages to images and OCR
            ocr_pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render at 2x resolution (144 dpi) for clear OCR
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text, engine = self.extract_text_from_image(img)
                if page_text.strip():
                    ocr_pages.append(f"--- Page {page_num + 1} (OCR) ---\n{page_text.strip()}")

            if ocr_pages:
                return "\n\n".join(ocr_pages), f"PyMuPDF + Image OCR"
            
            return "No readable text could be extracted from this PDF.", "None"
        except ImportError:
            # Fallback to pypdf if PyMuPDF is not installed
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                text_list = []
                for i, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        text_list.append(f"--- Page {i + 1} ---\n{t.strip()}")
                if text_list:
                    return "\n\n".join(text_list), "pypdf (Native Digital PDF)"
            except Exception as pe:
                logger.error(f"pypdf extraction failed: {pe}")
            
            raise RuntimeError("PDF processing libraries (PyMuPDF or pypdf) are not available.")

    def extract_text_from_image(self, image: Image.Image) -> Tuple[str, str]:
        """
        Run OCR on an image using Tesseract or EasyOCR.
        """
        preprocessed = self.preprocess_image(image)
        self._setup_tesseract()
        
        # 1. Try pytesseract first
        try:
            import pytesseract
            # Test if tesseract is callable
            text = pytesseract.image_to_string(preprocessed)
            if text.strip():
                return text.strip(), "Tesseract OCR"
        except Exception as e:
            logger.info(f"Tesseract OCR not active or failed: {e}")

        # 2. Try EasyOCR
        easy_reader = self._get_easyocr_reader()
        if easy_reader:
            try:
                import numpy as np
                np_img = np.array(image.convert("RGB"))
                results = easy_reader.readtext(np_img, detail=0)
                text = "\n".join(results)
                if text.strip():
                    return text.strip(), "EasyOCR"
            except Exception as e:
                logger.warning(f"EasyOCR extraction failed: {e}")

        # 3. If neither OCR engine worked, return explanatory message
        return (
            "OCR Notice: No OCR engine (Tesseract or EasyOCR) found installed or runnable on this host.\n"
            "If this is a digital PDF, text was not embedded. Please ensure Tesseract is installed or use Docker.",
            "Fallback (No OCR Engine)"
        )

    def process_file(self, file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """
        Auto-detect file format and route to PDF or Image processor.
        Returns: (extracted_text, engine_name)
        """
        ext = os.path.splitext(filename.lower())[1]
        if ext == ".pdf":
            return self.extract_text_from_pdf(file_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
            img = Image.open(io.BytesIO(file_bytes))
            return self.extract_text_from_image(img)
        else:
            # Attempt to open as image, fallback to utf-8 text
            try:
                img = Image.open(io.BytesIO(file_bytes))
                return self.extract_text_from_image(img)
            except Exception:
                try:
                    return file_bytes.decode("utf-8", errors="ignore"), "Plain Text"
                except Exception:
                    raise ValueError(f"Unsupported file type: {filename}")
