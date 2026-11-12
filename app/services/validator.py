import logging
from typing import List
from app.schemas import InvoiceData, ValidationResult, ItemMathCheck
from app.config import settings

logger = logging.getLogger(__name__)

class InvoiceValidator:
    def __init__(self, tolerance: float = None):
        self.tolerance = tolerance if tolerance is not None else settings.CALCULATION_TOLERANCE

    def validate(self, invoice: InvoiceData) -> ValidationResult:
        """
        Validates the mathematical consistency of an extracted invoice:
        1. Checks per-item (quantity * unit_price == total_price).
        2. Sums all item totals.
        3. Adds taxes/shipping and subtracts discounts.
        4. Compares with stated grand_total.
        5. Flags discrepancies to alert users of OCR errors or LLM hallucinations.
        """
        item_checks: List[ItemMathCheck] = []
        flags: List[str] = []
        
        # 1. Per-Item checks
        for idx, item in enumerate(invoice.items, start=1):
            expected_item_total = round(item.quantity * item.unit_price, 2)
            diff = round(abs(expected_item_total - item.total_price), 2)
            is_match = diff <= self.tolerance
            
            if not is_match and item.unit_price > 0 and item.quantity > 0:
                flags.append(
                    f"Item #{idx} ('{item.description}'): Qty {item.quantity} × {invoice.currency}{item.unit_price} = "
                    f"{invoice.currency}{expected_item_total}, but total listed is {invoice.currency}{item.total_price} (diff: {invoice.currency}{diff})"
                )
            
            item_checks.append(
                ItemMathCheck(
                    item_index=idx,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    calculated_total=expected_item_total,
                    reported_total=item.total_price,
                    is_match=is_match,
                    difference=diff
                )
            )

        # 2. Sum of all line items
        calculated_items_sum = round(sum(item.total_price for item in invoice.items), 2)

        # 3. Check Subtotal vs Line Items
        if invoice.subtotal is not None and invoice.subtotal > 0:
            subtotal_diff = round(abs(calculated_items_sum - invoice.subtotal), 2)
            if subtotal_diff > self.tolerance:
                flags.append(
                    f"Subtotal Mismatch: Sum of line items ({invoice.currency}{calculated_items_sum}) does not match reported subtotal ({invoice.currency}{invoice.subtotal}). Difference: {invoice.currency}{subtotal_diff}"
                )

        # 4. Calculate Final Expected Grand Total
        base_amount = invoice.subtotal if (invoice.subtotal is not None and invoice.subtotal > 0) else calculated_items_sum
        tax = invoice.tax_amount or 0.0
        shipping = invoice.shipping or 0.0
        discount = invoice.discount or 0.0

        calculated_grand_total = round(base_amount + tax + shipping - discount, 2)
        reported_grand_total = round(invoice.grand_total, 2)
        discrepancy = round(abs(calculated_grand_total - reported_grand_total), 2)

        # 5. Evaluate Validation Status
        if not invoice.items and reported_grand_total > 0:
            status = "WARNING"
            is_valid = False
            flags.append("No line items were detected on the invoice, but a Grand Total is present.")
            explanation = (
                f"Warning: Extracted Grand Total is {invoice.currency}{reported_grand_total}, "
                f"but zero line items could be parsed. Verification cannot confirm individual charges."
            )
        elif discrepancy <= self.tolerance:
            status = "VALID"
            is_valid = True
            explanation = (
                f"Math Verified: All {len(invoice.items)} line item(s) sum to {invoice.currency}{calculated_items_sum}. "
                f"With tax ({invoice.currency}{tax}) and adjustments, calculated total ({invoice.currency}{calculated_grand_total}) "
                f"matches reported Grand Total ({invoice.currency}{reported_grand_total})."
            )
        else:
            status = "MISMATCH_DETECTED"
            is_valid = False
            flags.append(
                f"Grand Total Discrepancy: Expected {invoice.currency}{calculated_grand_total} "
                f"(Items: {invoice.currency}{calculated_items_sum} + Tax: {invoice.currency}{tax} - Disc: {invoice.currency}{discount}), "
                f"but invoice states {invoice.currency}{reported_grand_total}. Discrepancy: {invoice.currency}{discrepancy}"
            )
            explanation = (
                f"Discrepancy Detected ({invoice.currency}{discrepancy}): "
                f"Item sum is {invoice.currency}{calculated_items_sum}. Calculated final amount is {invoice.currency}{calculated_grand_total}, "
                f"which does not match the reported Grand Total of {invoice.currency}{reported_grand_total}. "
                f"Please review the line items or OCR text for possible missed rows or tax misallocations."
            )

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            calculated_items_sum=calculated_items_sum,
            calculated_grand_total=calculated_grand_total,
            reported_grand_total=reported_grand_total,
            discrepancy_amount=discrepancy,
            item_math_checks=item_checks,
            flags=flags,
            explanation=explanation
        )
