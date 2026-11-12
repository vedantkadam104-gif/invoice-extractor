"""
validator.py — Arithmetic validation for extracted invoice data.
Checks that line-item totals match subtotal, and subtotal + tax ≈ grand total.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import InvoiceData

TOLERANCE = 0.02  # 2% relative tolerance for floating-point comparisons


@dataclass
class ValidationResult:
    is_valid: bool
    notes: list[str] = field(default_factory=list)


def _approx_equal(a: float | None, b: float | None, tol: float = TOLERANCE) -> bool:
    """Return True if |a - b| / max(|b|, 1) <= tol."""
    if a is None or b is None:
        return True  # can't check, don't flag
    denom = max(abs(b), 1.0)
    return abs(a - b) / denom <= tol


def validate_invoice(data: "InvoiceData") -> ValidationResult:
    notes: list[str] = []

    # 1. Check that item line totals sum to subtotal
    if data.items:
        computed_subtotal = sum(
            (item.line_total or 0.0) for item in data.items
        )
        if data.subtotal is not None and not _approx_equal(computed_subtotal, data.subtotal):
            notes.append(
                f"Line-item sum ({computed_subtotal:.2f}) does not match "
                f"subtotal ({data.subtotal:.2f})."
            )

    # 2. Check subtotal + tax ≈ total
    if data.subtotal is not None and data.total is not None:
        tax = data.tax or 0.0
        expected_total = data.subtotal + tax
        if not _approx_equal(expected_total, data.total):
            notes.append(
                f"Subtotal ({data.subtotal:.2f}) + Tax ({tax:.2f}) = "
                f"{expected_total:.2f} but grand total is {data.total:.2f}."
            )

    # 3. Check individual line_total = qty * unit_price (if both present)
    for i, item in enumerate(data.items or [], start=1):
        if item.qty is not None and item.unit_price is not None and item.line_total is not None:
            expected = item.qty * item.unit_price
            if not _approx_equal(expected, item.line_total, tol=0.05):
                notes.append(
                    f"Item {i} ({item.description!r}): "
                    f"qty({item.qty}) × unit_price({item.unit_price:.2f}) = "
                    f"{expected:.2f}, but line_total is {item.line_total:.2f}."
                )

    return ValidationResult(is_valid=len(notes) == 0, notes=notes)
