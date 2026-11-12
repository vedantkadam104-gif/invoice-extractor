from typing import List, Optional
from pydantic import BaseModel, Field

class InvoiceItem(BaseModel):
    description: str = Field(..., description="Description or name of the product or service")
    quantity: float = Field(default=1.0, description="Quantity of items purchased")
    unit_price: float = Field(default=0.0, description="Price per single unit")
    total_price: float = Field(default=0.0, description="Total price for this line item (quantity * unit_price)")

class InvoiceData(BaseModel):
    vendor_name: Optional[str] = Field(default=None, description="Name of the vendor, store, or business issuing the bill")
    vendor_address: Optional[str] = Field(default=None, description="Physical address of the vendor")
    vendor_phone: Optional[str] = Field(default=None, description="Contact phone number of the vendor")
    vendor_tax_id: Optional[str] = Field(default=None, description="Tax ID, GSTIN, VAT, or registration number")
    customer_name: Optional[str] = Field(default=None, description="Name of the customer or bill-to party")
    invoice_number: Optional[str] = Field(default=None, description="Invoice or receipt number/reference ID")
    invoice_date: Optional[str] = Field(default=None, description="Date the invoice was issued (YYYY-MM-DD preferred)")
    due_date: Optional[str] = Field(default=None, description="Payment due date if mentioned")
    currency: Optional[str] = Field(default="$", description="Currency symbol or code (e.g., $, USD, ₹, INR, €, EUR)")
    items: List[InvoiceItem] = Field(default_factory=list, description="List of line items on the invoice")
    subtotal: Optional[float] = Field(default=None, description="Subtotal before taxes and discounts")
    tax_rate: Optional[float] = Field(default=None, description="Tax percentage rate (e.g. 5, 10, 18)")
    tax_amount: Optional[float] = Field(default=None, description="Total tax amount charged")
    discount: Optional[float] = Field(default=0.0, description="Any discounts applied")
    shipping: Optional[float] = Field(default=0.0, description="Shipping or handling charges")
    grand_total: float = Field(default=0.0, description="Final total amount payable on the invoice")
    notes: Optional[str] = Field(default=None, description="Any payment instructions, remarks, or terms")

class ItemMathCheck(BaseModel):
    item_index: int
    description: str
    quantity: float
    unit_price: float
    calculated_total: float
    reported_total: float
    is_match: bool
    difference: float

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="True if line items and adjustments match the grand total")
    status: str = Field(..., description="'VALID', 'MISMATCH_DETECTED', or 'WARNING'")
    calculated_items_sum: float = Field(..., description="Sum of all individual line item totals")
    calculated_grand_total: float = Field(..., description="Subtotal or Item sum + tax + shipping - discount")
    reported_grand_total: float = Field(..., description="Grand total stated on the invoice")
    discrepancy_amount: float = Field(..., description="Difference between calculated and reported total")
    item_math_checks: List[ItemMathCheck] = Field(default_factory=list, description="Per-item Qty * Unit Price validation")
    flags: List[str] = Field(default_factory=list, description="List of detected anomalies or warnings")
    explanation: str = Field(..., description="Human-readable breakdown of the validation assessment")

class ExtractionResponse(BaseModel):
    success: bool
    filename: str
    ocr_engine_used: str
    raw_ocr_text: str
    data: InvoiceData
    validation: ValidationResult
    model_used: str
    processing_time_ms: float
