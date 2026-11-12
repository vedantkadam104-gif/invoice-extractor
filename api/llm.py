"""
llm.py — Calls OpenRouter to parse raw OCR text into structured invoice JSON.
Uses Pydantic for schema validation and retries once on parse failure.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import httpx
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are an expert invoice data extraction assistant.
Given raw OCR text from a bill or invoice, extract the following fields and
return ONLY valid JSON — no markdown, no code fences, no explanation.

Schema:
{
  "vendor": "string or null",
  "date": "YYYY-MM-DD or null",
  "invoice_number": "string or null",
  "items": [
    {
      "description": "string",
      "qty": number or null,
      "unit_price": number or null,
      "line_total": number or null
    }
  ],
  "subtotal": number or null,
  "tax": number or null,
  "total": number or null
}

Rules:
- All monetary values must be plain numbers (no currency symbols).
- If a field is not found, use null.
- Items array must always be present (empty array if no line items found).
- Dates must be in YYYY-MM-DD format; if only month/year, use first day of month.
- Do NOT invent data. Extract only what is present in the text.
"""


class LineItem(BaseModel):
    description: Optional[str] = None
    qty: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None


class InvoiceData(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = None
    invoice_number: Optional[str] = None
    items: list[LineItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None

    @field_validator("date", mode="before")
    @classmethod
    def _clean_date(cls, v):
        if not v:
            return None
        # Accept common date formats
        v = str(v).strip()
        return v


def _strip_to_json(text: str) -> str:
    """Strip markdown code fences and find the first JSON object."""
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM response.")
    return text[start : end + 1]


FALLBACK_MODELS = [
    "google/gemini-2.5-flash",
    "google/gemini-flash-latest",
    "meta-llama/llama-3.3-70b-instruct",
]


async def extract_invoice_data(raw_text: str) -> InvoiceData:
    """
    Send OCR text to OpenRouter and parse the response into InvoiceData.
    Tries fallback models if the requested model returns 404 / is unavailable.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set.")

    primary_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    timeout = int(os.getenv("LLM_TIMEOUT", "60"))

    # Build model list without duplicates
    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://invoice-extractor.local",
        "X-Title": "Invoice Extractor",
    }

    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Extract invoice data from this OCR text:\n\n{raw_text[:8000]}",
                    },
                ],
                "temperature": 0.1,
                "max_tokens": 2000,
            }

            logger.info("Attempting extraction with model: %s", model)
            try:
                response = await client.post(
                    OPENROUTER_API_URL, json=payload, headers=headers
                )
                if response.status_code == 404:
                    logger.warning("Model %s returned 404 (not found / deprecated). Trying fallback...", model)
                    last_error = ValueError(f"Model {model} not found on OpenRouter.")
                    continue

                if response.status_code >= 400:
                    logger.error("OpenRouter error %d: %s", response.status_code, response.text)
                    raise ValueError(f"OpenRouter error {response.status_code}: {response.text}")

                content = response.json()["choices"][0]["message"]["content"]
                logger.debug("LLM raw response:\n%s", content)

                json_str = _strip_to_json(content)
                data = InvoiceData.model_validate(json.loads(json_str))
                logger.info("Invoice parsed successfully with model %s.", model)
                return data

            except Exception as e:
                logger.warning("Extraction attempt with %s failed: %s", model, e)
                last_error = e
                continue

    raise ValueError(f"All LLM models failed. Last error: {last_error}")
