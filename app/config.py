import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Invoice / Bill Data Extractor"
    PROJECT_VERSION: str = "1.0.0"
    
    # OpenRouter API configurations
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "google/gemini-2.0-flash-001")
    
    # Tesseract configuration
    # Check default Windows installation paths if not set
    DEFAULT_TESSERACT_WINDOWS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", DEFAULT_TESSERACT_WINDOWS if os.path.exists(DEFAULT_TESSERACT_WINDOWS) else "tesseract")
    
    # Validation Tolerance (e.g. 0.05 to allow for standard currency rounding differences)
    CALCULATION_TOLERANCE: float = float(os.getenv("CALCULATION_TOLERANCE", "0.05"))
    
    # Upload limits
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))

settings = Settings()
