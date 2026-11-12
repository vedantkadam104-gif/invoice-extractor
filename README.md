# ⚡ QuickInvoice AI — Smart Invoice & Bill Data Extractor

Upload a photo or PDF of any bill and get back clean, validated JSON — plus a CSV or Excel file — in seconds.

## ✨ Features

- **OCR** — EasyOCR reads text from JPEG, PNG, WEBP, BMP, and multi-page PDF files
- **AI Extraction** — OpenRouter LLM turns messy OCR text into structured fields (vendor, date, items, totals)
- **Validation** — Arithmetic checks confirm that line-item totals match the subtotal and grand total; mismatches are flagged
- **Export** — Download results as CSV or styled Excel (.xlsx)
- **UI** — Beautiful Streamlit interface with glassmorphism dark design
- **Docker** — Single `docker-compose up` to run everything

---

## 🚀 Quick Start

### 1. Clone / copy the project

```bash
cd invoice-extractor
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-your-key-here
```

> Get a free key at https://openrouter.ai/keys

### 3. Build & run

```bash
docker-compose up --build
```

> **First run takes 3–5 minutes** — EasyOCR downloads its English model (~100 MB). Subsequent starts are instant thanks to the Docker volume.

### 4. Open the app

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI docs | http://localhost:8000/docs |

---

## 🔧 Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `google/gemini-flash-1.5` | LLM model to use for extraction |
| `LLM_TIMEOUT` | `60` | Seconds to wait for LLM response |
| `API_BASE_URL` | `http://api:8000` | Internal URL the UI uses to reach the API |

### Changing the LLM model

You can use any model on OpenRouter. Recommended options:

```bash
# Fast & cheap (default)
OPENROUTER_MODEL=google/gemini-flash-1.5

# Higher accuracy
OPENROUTER_MODEL=anthropic/claude-3-haiku

# Free tier
OPENROUTER_MODEL=mistralai/mistral-7b-instruct
```

---

## 📡 API Reference

### `POST /extract`

Upload a bill file and extract invoice data.

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@invoice.jpg"
```

**Response:**
```json
{
  "id": "uuid",
  "vendor": "Acme Corp",
  "date": "2024-01-15",
  "invoice_number": "INV-001",
  "items": [
    { "description": "Widget A", "qty": 2, "unit_price": 10.00, "line_total": 20.00 }
  ],
  "subtotal": 20.00,
  "tax": 2.00,
  "total": 22.00,
  "is_valid": true,
  "validation_notes": []
}
```

### `GET /download/{id}/csv`

Download result as CSV.

### `GET /download/{id}/excel`

Download result as Excel (.xlsx).

### `GET /results/{id}`

Fetch a previously extracted result by ID.

### `GET /health`

Health check — returns `{"status": "ok"}`.

---

## 🗂 Project Structure

```
invoice-extractor/
├── docker-compose.yml
├── .env.example
├── README.md
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py        ← FastAPI routes
│   ├── ocr.py         ← EasyOCR + pdf2image pipeline
│   ├── llm.py         ← OpenRouter LLM call + JSON parsing
│   ├── validator.py   ← Arithmetic validation
│   └── exporter.py    ← CSV / Excel export
└── ui/
    ├── Dockerfile
    ├── requirements.txt
    └── app.py         ← Streamlit interface
```

---

## 🛠 Local Development (without Docker)

**API:**
```bash
cd api
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in your key
uvicorn main:app --reload --port 8000
```

**UI** (in a separate terminal):
```bash
cd ui
pip install -r requirements.txt
API_BASE_URL=http://localhost:8000 streamlit run app.py
```

> On Windows you may need to install **poppler** manually for PDF support:
> Download from https://github.com/oschwartz10612/poppler-windows/releases and add the `bin/` folder to your PATH.

---

## ⚠️ Validation Logic

The extractor checks three things and flags mismatches:

1. `sum(item.line_total)` ≈ `subtotal` (within 2%)
2. `subtotal + tax` ≈ `grand total` (within 2%)
3. `qty × unit_price` ≈ `line_total` per item (within 5%)

This catches hallucinations where the LLM invents numbers that don't add up.

---

## 📄 License

MIT
