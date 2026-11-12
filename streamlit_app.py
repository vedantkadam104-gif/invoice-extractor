import io
import os
import asyncio
import streamlit as st
import pandas as pd
from PIL import Image

from app.config import settings
from app.schemas import InvoiceData, ValidationResult
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validator import InvoiceValidator
from app.services.exporter import ExporterService

# Page Setup
st.set_page_config(
    page_title="Invoice & Bill Data Extractor",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("⚙️ AI & Pipeline Settings")

openrouter_key = st.sidebar.text_input(
    "OpenRouter API Key",
    value=os.getenv("OPENROUTER_API_KEY", ""),
    type="password",
    help="Enter your OpenRouter key to enable LLM extraction."
)

model_options = [
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct"
]
selected_model = st.sidebar.selectbox("Extraction Model", model_options, index=0)

calc_tolerance = st.sidebar.slider(
    "Math Validation Tolerance",
    min_value=0.01,
    max_value=1.00,
    value=settings.CALCULATION_TOLERANCE,
    step=0.01,
    help="Permissible rounding difference between line item sums and final total."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Why Validation Matters")
st.sidebar.info(
    "Small shops type bills by hand. OCR reads messy text, but LLMs can occasionally misread digits or hallucinate missing items. "
    "Our **Anti-Hallucination Math Auditor** computes `∑(Qty × Unit Price) + Tax - Disc` and compares it to the stated Grand Total, flagging any discrepancy instantly."
)

# Main Title
st.title("🧾 Invoice & Bill Data Extractor")
st.caption("Upload a bill photo or PDF — extract structured vendor & item data, audit arithmetic, and export clean CSV/Excel.")

# Upload Area
uploaded_file = st.file_uploader(
    "Choose an Invoice file (PDF or Image)",
    type=["pdf", "png", "jpg", "jpeg", "webp", "tiff"]
)

# Helper function to render PDF page 1 for preview
def get_file_preview(file_bytes: bytes, filename: str):
    if filename.lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) > 0:
                pix = doc[0].get_pixmap(dpi=120)
                return Image.open(io.BytesIO(pix.tobytes("png")))
        except Exception:
            return None
    else:
        try:
            return Image.open(io.BytesIO(file_bytes))
        except Exception:
            return None

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    col_preview, col_data = st.columns([1, 1.3], gap="medium")

    with col_preview:
        st.subheader("📄 Document Preview")
        preview_img = get_file_preview(file_bytes, filename)
        if preview_img:
            st.image(preview_img, use_container_width=True, caption=f"{filename} (Preview)")
        else:
            st.info(f"File uploaded: {filename} ({len(file_bytes) / 1024:.1f} KB)")

    with col_data:
        st.subheader("📊 Extracted Data & Math Audit")

        if st.button("🚀 Run Extraction & Validation", type="primary", use_container_width=True):
            with st.spinner("1/3 Running OCR on document..."):
                ocr_service = OCRService(tesseract_cmd=settings.TESSERACT_CMD)
                try:
                    ocr_text, ocr_engine = ocr_service.process_file(file_bytes, filename)
                except Exception as e:
                    st.error(f"OCR Error: {e}")
                    st.stop()

            with st.spinner("2/3 Prompting OpenRouter LLM for structured JSON..."):
                llm_service = LLMService(
                    api_key=openrouter_key or settings.OPENROUTER_API_KEY,
                    default_model=selected_model
                )
                try:
                    # Run async call safely in sync Streamlit context
                    invoice_data, model_used = asyncio.run(
                        llm_service.extract_invoice_data(
                            ocr_text=ocr_text,
                            model=selected_model,
                            custom_api_key=openrouter_key
                        )
                    )
                except Exception as e:
                    st.error(f"LLM Extraction Failed: {e}")
                    st.stop()

            with st.spinner("3/3 Auditing arithmetic and verifying totals..."):
                validator = InvoiceValidator(tolerance=calc_tolerance)
                validation = validator.validate(invoice_data)

            # Save in session state
            st.session_state["extraction"] = {
                "invoice": invoice_data,
                "validation": validation,
                "ocr_text": ocr_text,
                "ocr_engine": ocr_engine,
                "model_used": model_used
            }

        # Render extracted results from session state if available
        if "extraction" in st.session_state:
            ext = st.session_state["extraction"]
            inv: InvoiceData = ext["invoice"]
            val: ValidationResult = ext["validation"]
            curr = inv.currency or "$"

            # 1. Validation Banner
            if val.is_valid:
                st.success(f"✅ **Math Audit Passed**: {val.explanation}")
            elif val.status == "MISMATCH_DETECTED":
                st.error(f"⚠️ **Arithmetic Mismatch Detected** ({curr}{val.discrepancy_amount:.2f})\n\n{val.explanation}")
                if val.flags:
                    for f in val.flags:
                        st.warning(f)
            else:
                st.info(f"ℹ️ **Notice**: {val.explanation}")

            # 2. Key Metadata Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vendor", inv.vendor_name or "N/A")
            m2.metric("Invoice #", inv.invoice_number or "N/A")
            m3.metric("Date", inv.invoice_date or "N/A")
            m4.metric("Tax ID", inv.vendor_tax_id or "N/A")

            # 3. Line Items Table (Interactive)
            st.markdown("#### Line Items")
            if inv.items:
                items_data = []
                for idx, it in enumerate(inv.items, 1):
                    expected = round(it.quantity * it.unit_price, 2)
                    match = abs(expected - it.total_price) <= 0.05
                    items_data.append({
                        "#": idx,
                        "Description": it.description,
                        "Qty": it.quantity,
                        "Unit Price": it.unit_price,
                        "Total Price": it.total_price,
                        "Math Check": "✓ Match" if match else f"Diff: {curr}{abs(expected - it.total_price):.2f}"
                    })
                df_items = pd.DataFrame(items_data)
                st.dataframe(df_items, use_container_width=True, hide_index=True)
            else:
                st.write("No line items extracted.")

            # 4. Financial Breakdown
            f1, f2, f3 = st.columns([1, 1, 1])
            with f3:
                st.markdown(f"""
                **Items Subtotal:** {curr}{inv.subtotal or val.calculated_items_sum:.2f}  
                **Tax:** {curr}{inv.tax_amount or 0.0:.2f}  
                **Discount:** -{curr}{inv.discount or 0.0:.2f}  
                **Shipping:** {curr}{inv.shipping or 0.0:.2f}  
                ### **Grand Total: {curr}{inv.grand_total:.2f}**
                """)

            # 5. Export Actions
            st.markdown("---")
            exp_col1, exp_col2, exp_col3 = st.columns(3)

            csv_data = ExporterService.export_to_csv(inv, val)
            exp_col1.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"invoice_{inv.invoice_number or 'extracted'}.csv",
                mime="text/csv",
                use_container_width=True
            )

            excel_bytes = ExporterService.export_to_excel(inv, val)
            exp_col2.download_button(
                label="📊 Download Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"invoice_{inv.invoice_number or 'extracted'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            with st.expander("🔍 View Raw OCR Text & Pipeline Diagnostics"):
                st.caption(f"OCR Engine: **{ext['ocr_engine']}** | LLM: **{ext['model_used']}**")
                st.code(ext["ocr_text"], language="text")

else:
    st.info("👆 Please upload an invoice image or PDF to start extracting!")
