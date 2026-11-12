import json
import re
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from app.schemas import InvoiceData, InvoiceItem
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert financial document and invoice parsing AI.
Your job is to read raw, potentially messy OCR text extracted from an invoice or bill and convert it into structured JSON.

CRITICAL EXTRACTION RULES:
1. Vendor: Identify the business or entity issuing the invoice (name, address, phone, tax/registration/GSTIN ID).
2. Metadata: Extract invoice number, issue date (format as YYYY-MM-DD if possible), due date, and currency.
3. Line Items: Extract EVERY purchased product or service:
   - "description": Clear description of the item.
   - "quantity": Number of units (float, default 1.0 if not stated).
   - "unit_price": Price per individual unit (float).
   - "total_price": Total line item price before invoice-level taxes (float, quantity * unit_price).
   DO NOT hallucinate or guess line items that are not in the text.
4. Financials:
   - "subtotal": Sum of items before tax/discounts (float, or null if omitted).
   - "tax_rate": Percentage tax rate if stated (e.g. 18.0 for 18%, or null).
   - "tax_amount": Total tax charge (float, or null).
   - "discount": Any deducted discount amount (float, default 0.0).
   - "shipping": Shipping / delivery fee (float, default 0.0).
   - "grand_total": The absolute final amount payable on the bill (float, mandatory).
5. Output format: Return ONLY a valid JSON object matching this schema. Do not enclose in markdown code fences or add explanatory text.

JSON Schema format:
{
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "vendor_phone": "string or null",
  "vendor_tax_id": "string or null",
  "customer_name": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "string or null",
  "due_date": "string or null",
  "currency": "string ($ or ₹ or € or USD, etc.)",
  "items": [
    {
      "description": "string",
      "quantity": 1.0,
      "unit_price": 10.0,
      "total_price": 10.0
    }
  ],
  "subtotal": 10.0,
  "tax_rate": null,
  "tax_amount": 0.0,
  "discount": 0.0,
  "shipping": 0.0,
  "grand_total": 10.0,
  "notes": "string or null"
}
"""

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.default_model = default_model or settings.DEFAULT_MODEL

    def _clean_json_response(self, text: str) -> str:
        """Strip markdown fences (```json ... ```) and leading/trailing junk."""
        text = text.strip()
        # Remove markdown code block if present
        pattern = r"^```(?:json)?\s*(.*?)\s*```$"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If wrapped inside some other text, extract outermost { ... }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1].strip()
        
        return text

    async def extract_invoice_data(
        self,
        ocr_text: str,
        model: Optional[str] = None,
        custom_api_key: Optional[str] = None
    ) -> Tuple[InvoiceData, str]:
        """
        Send raw OCR text to OpenRouter LLM and return validated InvoiceData.
        """
        print(f"DEBUG: extract_invoice_data called with custom_api_key={repr(custom_api_key)}, self.api_key={repr(self.api_key)}", flush=True)
        effective_key = custom_api_key or self.api_key
        effective_model = model or self.default_model

        if not effective_key:
            # Fallback mock extractor if no key provided
            print("DEBUG: entering fallback branch", flush=True)
            logger.warning("No OpenRouter API key configured. Using heuristic/demo extractor.")
            return self._heuristic_fallback_extractor(ocr_text), "Demo Heuristic Engine (No API Key)"
        print("DEBUG: after fallback check, proceeding to HTTP call!", flush=True)

        user_content = f"Here is the raw text extracted from the bill/invoice via OCR:\n\n=== OCR TEXT START ===\n{ocr_text}\n=== OCR TEXT END ===\n\nExtract and return the structured invoice JSON now:"

        headers = {
            "Authorization": f"Bearer {effective_key}",
            "HTTP-Referer": "https://github.com/invoice-extractor",
            "X-Title": "Invoice Data Extractor",
            "Content-Type": "application/json"
        }

        payload = {
            "model": effective_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,  # Low temperature for strict factual extraction
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result_json = response.json()
            except httpx.HTTPStatusError as e:
                err_detail = e.response.text
                logger.error(f"OpenRouter API error {e.response.status_code}: {err_detail}")
                raise RuntimeError(f"OpenRouter API error ({e.response.status_code}): {err_detail}")
            except Exception as e:
                logger.error(f"Connection error to OpenRouter: {e}")
                raise RuntimeError(f"Failed to communicate with OpenRouter API: {str(e)}")

        choices = result_json.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned an empty response.")

        raw_content = choices[0].get("message", {}).get("content", "")
        cleaned_json = self._clean_json_response(raw_content)

        try:
            parsed_dict = json.loads(cleaned_json)
            # Validate with Pydantic
            invoice_data = InvoiceData.model_validate(parsed_dict)
            return invoice_data, effective_model
        except Exception as e:
            logger.error(f"Failed to parse LLM response into InvoiceData: {e}\nRaw Content: {raw_content}")
            raise ValueError(f"Failed to parse model output as valid invoice data: {str(e)}")

    def _heuristic_fallback_extractor(self, text: str) -> InvoiceData:
        """
        Simple regex/rule-based fallback parser for demo / offline use when no API key is provided.
        Parses common patterns for totals, dates, and amounts.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        vendor = lines[0] if lines else "Sample Store"
        
        # Search for date pattern
        date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})", text)
        invoice_date = date_match.group(1) if date_match else "2026-05-10"

        # Search for invoice number pattern
        inv_match = re.search(r"(?:Invoice|Inv|Bill|Receipt)\s*(?:#|No|Number)?[:\s]*([A-Za-z0-9-_]+)", text, re.IGNORECASE)
        invoice_number = inv_match.group(1) if inv_match else "INV-1001"

        # Search for currency
        currency = "$"
        if "₹" in text or "INR" in text:
            currency = "₹"
        elif "€" in text or "EUR" in text:
            currency = "€"
        elif "£" in text or "GBP" in text:
            currency = "£"

        # Extract amounts from lines
        items = []
        item_counter = 1
        subtotal = 0.0

        for line in lines:
            # Match lines with price patterns at the end, e.g. "Widget ABC 2 15.00 30.00"
            amounts = re.findall(r"\d+\.\d{2}", line)
            if amounts and not any(k in line.lower() for k in ["total", "tax", "subtotal", "balance", "due"]):
                try:
                    price = float(amounts[-1])
                    desc = re.sub(r"\d+\.\d{2}", "", line).strip() or f"Item {item_counter}"
                    qty = 1.0
                    unit_p = price
                    if len(amounts) >= 2:
                        unit_p = float(amounts[-2])
                        qty = round(price / unit_p, 2) if unit_p > 0 else 1.0
                    items.append(InvoiceItem(description=desc, quantity=qty, unit_price=unit_p, total_price=price))
                    subtotal += price
                    item_counter += 1
                except Exception:
                    continue

        if not items:
            # Default placeholder items if none parsed
            items = [
                InvoiceItem(description="Standard Goods / Services", quantity=1.0, unit_price=100.0, total_price=100.0)
            ]
            subtotal = 100.0

        # Try to find grand total
        total_match = re.search(r"(?:grand\s+total|total\s+amount|total)[\s:]*([$€₹£]?\s*[\d,]+\.\d{2})", text, re.IGNORECASE)
        if total_match:
            clean_num = re.sub(r"[^\d.]", "", total_match.group(1))
            grand_total = float(clean_num)
        else:
            grand_total = subtotal

        return InvoiceData(
            vendor_name=vendor,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            currency=currency,
            items=items,
            subtotal=round(subtotal, 2),
            tax_amount=0.0,
            grand_total=round(grand_total, 2)
        )
