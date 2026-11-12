"""
exporter.py — Converts extracted InvoiceData to CSV or Excel bytes.
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm import InvoiceData


def to_csv_bytes(data: "InvoiceData") -> bytes:
    """Return UTF-8 CSV bytes for the invoice."""
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Header block
    writer.writerow(["Field", "Value"])
    writer.writerow(["Vendor", data.vendor or ""])
    writer.writerow(["Date", data.date or ""])
    writer.writerow(["Invoice Number", data.invoice_number or ""])
    writer.writerow([])

    # Line items
    writer.writerow(["Description", "Qty", "Unit Price", "Line Total"])
    for item in data.items or []:
        writer.writerow([
            item.description or "",
            item.qty if item.qty is not None else "",
            f"{item.unit_price:.2f}" if item.unit_price is not None else "",
            f"{item.line_total:.2f}" if item.line_total is not None else "",
        ])
    writer.writerow([])

    # Totals
    writer.writerow(["Subtotal", f"{data.subtotal:.2f}" if data.subtotal else ""])
    writer.writerow(["Tax", f"{data.tax:.2f}" if data.tax else ""])
    writer.writerow(["Grand Total", f"{data.total:.2f}" if data.total else ""])

    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility


def to_excel_bytes(data: "InvoiceData") -> bytes:
    """Return .xlsx bytes for the invoice."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("openpyxl is required for Excel export.")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Invoice"

    # ── Styles ────────────────────────────────────────────────────────────────
    HEADER_FILL = PatternFill("solid", fgColor="2D3748")
    HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
    ACCENT_FILL = PatternFill("solid", fgColor="EBF4FF")
    TOTAL_FONT = Font(bold=True, size=11)
    CENTER = Alignment(horizontal="center", vertical="center")
    LEFT = Alignment(horizontal="left", vertical="center")
    thin = Side(border_style="thin", color="CBD5E0")
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

    def header_cell(row, col, value):
        c = ws.cell(row=row, column=col, value=value)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = CENTER
        c.border = BORDER
        return c

    def data_cell(row, col, value, bold=False, fill=None):
        c = ws.cell(row=row, column=col, value=value)
        c.alignment = LEFT
        c.border = BORDER
        if bold:
            c.font = TOTAL_FONT
        if fill:
            c.fill = fill
        return c

    # ── Invoice metadata ───────────────────────────────────────────────────────
    ws.merge_cells("A1:D1")
    title = ws["A1"]
    title.value = "INVOICE EXTRACT"
    title.font = Font(bold=True, size=16, color="2B6CB0")
    title.alignment = CENTER
    ws.row_dimensions[1].height = 30

    meta = [
        ("Vendor", data.vendor or ""),
        ("Date", data.date or ""),
        ("Invoice Number", data.invoice_number or ""),
    ]
    for i, (label, val) in enumerate(meta, start=2):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws.cell(row=i, column=2, value=val)

    # ── Line items table ───────────────────────────────────────────────────────
    item_start = 6
    headers = ["Description", "Qty", "Unit Price", "Line Total"]
    for col, h in enumerate(headers, start=1):
        header_cell(item_start, col, h)

    for r, item in enumerate(data.items or [], start=item_start + 1):
        fill = ACCENT_FILL if r % 2 == 0 else None
        data_cell(r, 1, item.description or "", fill=fill)
        data_cell(r, 2, item.qty, fill=fill)
        data_cell(r, 3, item.unit_price, fill=fill)
        data_cell(r, 4, item.line_total, fill=fill)
        ws.cell(r, 3).number_format = "#,##0.00"
        ws.cell(r, 4).number_format = "#,##0.00"

    total_row = item_start + 1 + len(data.items or [])

    # ── Totals ─────────────────────────────────────────────────────────────────
    ws.cell(total_row + 1, 3, "Subtotal").font = TOTAL_FONT
    ws.cell(total_row + 1, 4, data.subtotal).number_format = "#,##0.00"
    ws.cell(total_row + 2, 3, "Tax").font = TOTAL_FONT
    ws.cell(total_row + 2, 4, data.tax or 0).number_format = "#,##0.00"
    ws.cell(total_row + 3, 3, "Grand Total").font = Font(bold=True, color="1A365D", size=12)
    ws.cell(total_row + 3, 4, data.total).font = Font(bold=True, color="1A365D", size=12)
    ws.cell(total_row + 3, 4).number_format = "#,##0.00"

    # ── Column widths ──────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 15

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
