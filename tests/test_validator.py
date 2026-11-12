import pytest
from app.schemas import InvoiceData, InvoiceItem
from app.services.validator import InvoiceValidator

def test_valid_invoice_math():
    """Verify that a mathematically consistent invoice passes validation."""
    invoice = InvoiceData(
        vendor_name="Test Store",
        invoice_number="INV-001",
        currency="$",
        items=[
            InvoiceItem(description="Item A", quantity=2.0, unit_price=25.0, total_price=50.0),
            InvoiceItem(description="Item B", quantity=1.0, unit_price=30.0, total_price=30.0)
        ],
        subtotal=80.0,
        tax_amount=8.0,
        discount=5.0,
        grand_total=83.0  # 80 + 8 - 5 = 83.0
    )
    validator = InvoiceValidator(tolerance=0.05)
    result = validator.validate(invoice)

    assert result.is_valid is True
    assert result.status == "VALID"
    assert result.discrepancy_amount == 0.0
    assert result.calculated_items_sum == 80.0
    assert result.calculated_grand_total == 83.0
    assert len(result.flags) == 0

def test_mismatched_invoice_detects_discrepancy():
    """Verify that an invoice with inflated or missing grand total is flagged as mismatch."""
    invoice = InvoiceData(
        vendor_name="Shady Supplies",
        invoice_number="INV-BAD",
        currency="$",
        items=[
            InvoiceItem(description="Item X", quantity=1.0, unit_price=100.0, total_price=100.0),
            InvoiceItem(description="Item Y", quantity=1.0, unit_price=50.0, total_price=50.0)
        ],
        subtotal=150.0,
        tax_amount=10.0,
        discount=0.0,
        grand_total=220.0  # Should be 160.0. Tampered or hallucinated by 60.0!
    )
    validator = InvoiceValidator(tolerance=0.05)
    result = validator.validate(invoice)

    assert result.is_valid is False
    assert result.status == "MISMATCH_DETECTED"
    assert result.discrepancy_amount == 60.0
    assert any("Discrepancy: $60.0" in f for f in result.flags)

def test_item_line_multiplication_error():
    """Verify that per-item qty * unit_price mismatches are caught."""
    invoice = InvoiceData(
        vendor_name="Typo Mart",
        invoice_number="INV-TYPO",
        currency="$",
        items=[
            # 3 * 10 is 30, but total listed as 40!
            InvoiceItem(description="Faulty Line", quantity=3.0, unit_price=10.0, total_price=40.0)
        ],
        subtotal=40.0,
        tax_amount=0.0,
        grand_total=40.0
    )
    validator = InvoiceValidator(tolerance=0.05)
    result = validator.validate(invoice)

    # Item math check failed
    assert len(result.item_math_checks) == 1
    assert result.item_math_checks[0].is_match is False
    assert result.item_math_checks[0].calculated_total == 30.0
    assert any("Item #1" in f for f in result.flags)

def test_empty_items_warning():
    """Verify that an invoice with grand total but 0 line items flags a warning."""
    invoice = InvoiceData(
        vendor_name="Blank Vendor",
        invoice_number="INV-EMPTY",
        currency="$",
        items=[],
        grand_total=150.0
    )
    validator = InvoiceValidator()
    result = validator.validate(invoice)

    assert result.is_valid is False
    assert result.status == "WARNING"
    assert any("No line items were detected" in f for f in result.flags)
