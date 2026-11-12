import io
import csv
from typing import Tuple
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.schemas import InvoiceData, ValidationResult

class ExporterService:
    @staticmethod
    def export_to_csv(invoice: InvoiceData, validation: ValidationResult) -> str:
        """
        Export invoice data to CSV format suitable for accounting software import.
        Each line item gets its own row with invoice headers attached.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "Invoice Number",
            "Invoice Date",
            "Vendor Name",
            "Vendor Tax ID",
            "Customer Name",
            "Item Description",
            "Quantity",
            "Unit Price",
            "Total Price",
            "Currency",
            "Subtotal",
            "Tax Amount",
            "Discount",
            "Grand Total",
            "Validation Status",
            "Discrepancy"
        ])

        if not invoice.items:
            # Write a single summary row if no items
            writer.writerow([
                invoice.invoice_number or "",
                invoice.invoice_date or "",
                invoice.vendor_name or "",
                invoice.vendor_tax_id or "",
                invoice.customer_name or "",
                "N/A",
                0,
                0.0,
                0.0,
                invoice.currency or "$",
                invoice.subtotal or 0.0,
                invoice.tax_amount or 0.0,
                invoice.discount or 0.0,
                invoice.grand_total,
                validation.status,
                validation.discrepancy_amount
            ])
        else:
            for item in invoice.items:
                writer.writerow([
                    invoice.invoice_number or "",
                    invoice.invoice_date or "",
                    invoice.vendor_name or "",
                    invoice.vendor_tax_id or "",
                    invoice.customer_name or "",
                    item.description,
                    item.quantity,
                    item.unit_price,
                    item.total_price,
                    invoice.currency or "$",
                    invoice.subtotal or validation.calculated_items_sum,
                    invoice.tax_amount or 0.0,
                    invoice.discount or 0.0,
                    invoice.grand_total,
                    validation.status,
                    validation.discrepancy_amount
                ])

        return output.getvalue()

    @staticmethod
    def export_to_excel(invoice: InvoiceData, validation: ValidationResult) -> bytes:
        """
        Generate a polished multi-tab Excel (.xlsx) workbook.
        Tab 1: Invoice Summary & Metadata
        Tab 2: Line Items Detail Table
        """
        wb = Workbook()

        # Styles
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="1F4E78")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)
        
        status_color = "C6EFCE" if validation.is_valid else "FFC7CE"  # soft green vs soft red
        status_font_color = "006100" if validation.is_valid else "9C0006"
        status_fill = PatternFill(start_color=status_color, end_color=status_color, fill_type="solid")
        status_font = Font(name="Calibri", size=11, bold=True, color=status_font_color)

        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # ---------------- SHEET 1: SUMMARY ----------------
        ws_summary = wb.active
        ws_summary.title = "Invoice Summary"
        ws_summary.views.sheetView[0].showGridLines = True

        ws_summary["A1"] = "INVOICE SUMMARY"
        ws_summary["A1"].font = title_font

        summary_rows = [
            ("Vendor Name", invoice.vendor_name or "N/A"),
            ("Vendor Tax ID / GSTIN", invoice.vendor_tax_id or "N/A"),
            ("Vendor Address", invoice.vendor_address or "N/A"),
            ("Vendor Phone", invoice.vendor_phone or "N/A"),
            ("Customer Name", invoice.customer_name or "N/A"),
            ("Invoice Number", invoice.invoice_number or "N/A"),
            ("Invoice Date", invoice.invoice_date or "N/A"),
            ("Due Date", invoice.due_date or "N/A"),
            ("Currency", invoice.currency or "$"),
            ("Items Count", len(invoice.items)),
            ("Subtotal", f"{invoice.currency or '$'} {invoice.subtotal or validation.calculated_items_sum:.2f}"),
            ("Tax Amount", f"{invoice.currency or '$'} {invoice.tax_amount or 0.0:.2f}"),
            ("Discount", f"{invoice.currency or '$'} {invoice.discount or 0.0:.2f}"),
            ("Shipping", f"{invoice.currency or '$'} {invoice.shipping or 0.0:.2f}"),
            ("Grand Total", f"{invoice.currency or '$'} {invoice.grand_total:.2f}"),
            ("Validation Status", validation.status),
            ("Discrepancy", f"{invoice.currency or '$'} {validation.discrepancy_amount:.2f}"),
            ("Validation Notes", validation.explanation)
        ]

        for r_idx, (label, val) in enumerate(summary_rows, start=3):
            cell_label = ws_summary.cell(row=r_idx, column=1, value=label)
            cell_label.font = bold_font
            cell_label.border = thin_border
            cell_label.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

            cell_val = ws_summary.cell(row=r_idx, column=2, value=val)
            cell_val.font = regular_font
            cell_val.border = thin_border

            if label == "Validation Status":
                cell_val.fill = status_fill
                cell_val.font = status_font
            elif label == "Grand Total":
                cell_val.font = Font(name="Calibri", size=12, bold=True, color="1F4E78")

        # ---------------- SHEET 2: LINE ITEMS ----------------
        ws_items = wb.create_sheet(title="Line Items")
        ws_items.views.sheetView[0].showGridLines = True

        headers = ["#", "Item Description", "Quantity", "Unit Price", "Total Price", "Item Math Check"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws_items.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left")

        curr = invoice.currency or "$"
        row_num = 2
        for idx, item in enumerate(invoice.items, start=1):
            # Check item calculation
            expected = round(item.quantity * item.unit_price, 2)
            match = abs(expected - item.total_price) <= 0.05
            math_check_text = "Match" if match else f"Diff: {curr}{abs(expected - item.total_price):.2f}"

            row_cells = [
                ws_items.cell(row=row_num, column=1, value=idx),
                ws_items.cell(row=row_num, column=2, value=item.description),
                ws_items.cell(row=row_num, column=3, value=item.quantity),
                ws_items.cell(row=row_num, column=4, value=item.unit_price),
                ws_items.cell(row=row_num, column=5, value=item.total_price),
                ws_items.cell(row=row_num, column=6, value=math_check_text)
            ]

            for col_i, c in enumerate(row_cells, start=1):
                c.font = regular_font
                c.border = thin_border
                if col_i in [3, 4, 5]:
                    c.alignment = Alignment(horizontal="right")
                    if col_i in [4, 5]:
                        c.number_format = '#,##0.00'
                elif col_i == 6:
                    c.alignment = Alignment(horizontal="center")
                    if not match:
                        c.fill = status_fill
                        c.font = status_font

            row_num += 1

        # Summary total row in Sheet 2
        sum_row = row_num
        ws_items.cell(row=sum_row, column=1, value="").border = thin_border
        ws_items.cell(row=sum_row, column=2, value="TOTALS").font = bold_font
        ws_items.cell(row=sum_row, column=2).border = thin_border
        ws_items.cell(row=sum_row, column=3, value="").border = thin_border
        ws_items.cell(row=sum_row, column=4, value="Items Sum:").font = bold_font
        ws_items.cell(row=sum_row, column=4).border = thin_border
        
        sum_cell = ws_items.cell(row=sum_row, column=5, value=validation.calculated_items_sum)
        sum_cell.font = bold_font
        sum_cell.number_format = '#,##0.00'
        sum_cell.border = thin_border
        ws_items.cell(row=sum_row, column=6, value="").border = thin_border

        # Auto-adjust column widths for both sheets
        for ws in [ws_summary, ws_items]:
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len and len(val_str) < 60:
                        max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output_stream = io.BytesIO()
        wb.save(output_stream)
        return output_stream.getvalue()
