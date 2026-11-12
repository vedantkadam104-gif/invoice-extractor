"""
app.py — LedgerAI: Intelligent Invoice & Bill Data Extractor
Custom modern dark theme with high-contrast typography, interactive inspection, and instant exports.
"""

from __future__ import annotations

import datetime
import os
import io

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuickInvoice AI — Invoice Extractor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Clean, High-Contrast Modern Dark Theme CSS ────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global canvas & background */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #080C14 !important;
        color: #E2E8F0 !important;
    }

    /* Container constraints */
    .block-container {
        max-width: 1320px !important;
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* ─── Top App Header Bar ─────────────────────────────────────────────── */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.2rem 1.8rem;
        background: #0E1526;
        border: 1px solid #1E293B;
        border-radius: 16px;
        margin-bottom: 1.8rem;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4);
    }
    .brand-section {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    .brand-icon {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        background: linear-gradient(135deg, #3B82F6, #1D4ED8);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
    }
    .brand-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.1rem;
    }
    .header-badges {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        border: 1px solid;
    }
    .badge-pill.status {
        background: rgba(16, 185, 129, 0.1);
        color: #34D399;
        border-color: rgba(16, 185, 129, 0.3);
    }
    .badge-pill.model {
        background: rgba(59, 130, 246, 0.1);
        color: #60A5FA;
        border-color: rgba(59, 130, 246, 0.3);
    }

    /* ─── Cards & Panels ─────────────────────────────────────────────────── */
    .card-panel {
        background: #0E1526;
        border: 1px solid #1E293B;
        border-radius: 18px;
        padding: 1.6rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .card-desc {
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }

    /* ─── Metric Box Components ─────────────────────────────────────────── */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.2rem;
    }
    .metric-item {
        background: #141D32;
        border: 1px solid #1E2D4A;
        border-radius: 14px;
        padding: 1.1rem;
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.35rem;
    }
    .metric-val {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F1F5F9;
        word-break: break-word;
    }
    .metric-val.green {
        color: #10B981 !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
    }
    .metric-val.blue {
        color: #38BDF8 !important;
    }

    /* ─── Custom Clean HTML Table for Items ──────────────────────────────── */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
        color: #E2E8F0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #1E293B;
        margin-bottom: 1.2rem;
    }
    .custom-table thead {
        background: #162238;
    }
    .custom-table th {
        padding: 0.85rem 1.1rem;
        font-weight: 600;
        color: #94A3B8;
        text-align: left;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #1E293B;
    }
    .custom-table th.num {
        text-align: right;
    }
    .custom-table td {
        padding: 0.85rem 1.1rem;
        border-bottom: 1px solid #162033;
        background: #0E1526;
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table tr:hover td {
        background: #131E33;
    }
    .custom-table td.num {
        text-align: right;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
    }
    .custom-table td.bold {
        font-weight: 600;
        color: #F8FAFC;
    }

    /* ─── Validation Status Banner ──────────────────────────────────────── */
    .validation-badge-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .validation-badge-banner.valid {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #34D399;
    }
    .validation-badge-banner.flagged {
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.35);
        color: #F87171;
    }

    /* ─── Upload Dropzone Customization ──────────────────────────────────── */
    [data-testid="stFileUploadDropzone"] {
        background: #0B111E !important;
        border: 2px dashed #1E293B !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        transition: all 0.2s;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #3B82F6 !important;
        background: #0E1729 !important;
    }
    [data-testid="stFileUploadDropzone"] svg {
        fill: #3B82F6 !important;
    }

    /* ─── Streamlit UI Button Overrides ──────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.75rem 1.8rem !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(59, 130, 246, 0.6) !important;
    }

    .stDownloadButton > button {
        background: #141D32 !important;
        color: #F1F5F9 !important;
        border: 1px solid #243452 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.7rem 1.4rem !important;
        font-size: 0.88rem !important;
        transition: all 0.2s !important;
    }
    .stDownloadButton > button:hover {
        background: #1A2642 !important;
        border-color: #3B82F6 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #0E1526 !important;
        border: 1px solid #1E293B !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
    }

    /* Hide standard headers */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── TOP APP BAR ───────────────────────────────────────────────────────────────
today_str = datetime.date.today().strftime("%B %d, %Y")

st.markdown(
    f"""
    <div class="app-header">
        <div class="brand-section">
            <div class="brand-icon">⚡</div>
            <div>
                <h1 class="brand-title">QuickInvoice AI</h1>
                <div class="brand-subtitle">Commercial Invoice & Receipt OCR Engine</div>
            </div>
        </div>
        <div class="header-badges">
            <span class="badge-pill status">● API Connected</span>
            <span class="badge-pill model">🤖 Gemini 2.5 Flash</span>
            <span style="font-size:0.8rem; color:#64748B; margin-left:0.5rem;">{today_str}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2-COLUMN WORKBENCH LAYOUT ─────────────────────────────────────────────────
left_col, right_col = st.columns([1.1, 1.9], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN: UPLOAD & INPUT BILL PREVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with left_col:
    st.markdown(
        """
        <div class="card-panel">
            <div class="card-title">📤 Upload Invoice Document</div>
            <div class="card-desc">Supported: JPG, PNG, WEBP, multi-page PDF</div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        label="Drop file here",
        type=["jpg", "jpeg", "png", "webp", "bmp", "pdf"],
        help="Upload photo or scan of a bill",
        label_visibility="collapsed",
    )

    if uploaded_file:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        if uploaded_file.type != "application/pdf":
            st.image(uploaded_file, caption=f"{uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)", use_container_width=True)
        else:
            st.markdown(
                f"""
                <div style="text-align:center; padding:1.8rem; background:#080C14; border:1px solid #1E293B; border-radius:14px; margin-bottom:1rem;">
                    <div style="font-size:2.8rem;">📄</div>
                    <div style="font-size:0.9rem; font-weight:700; color:#F8FAFC; margin-top:0.4rem;">{uploaded_file.name}</div>
                    <div style="font-size:0.75rem; color:#64748B;">{uploaded_file.size / 1024:.1f} KB • Portable Document Format</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        extract_btn = st.button("⚡ Extract & Verify Bill", use_container_width=True, type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── How it works card ──────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="card-panel" style="padding:1.3rem;">
            <div class="card-title" style="font-size:0.92rem;">🛡️ Validation Architecture</div>
            <div style="font-size:0.8rem; color:#64748B; line-height:1.6; margin-top:0.5rem;">
                <div style="margin-bottom:0.4rem;"><strong style="color:#94A3B8;">1. Local OCR:</strong> EasyOCR reads text directly without sending raw images to third parties.</div>
                <div style="margin-bottom:0.4rem;"><strong style="color:#94A3B8;">2. Structured LLM:</strong> OpenRouter converts unformatted text into typed JSON schema.</div>
                <div><strong style="color:#94A3B8;">3. Math Audit:</strong> Line totals are independently summed and cross-checked against grand total to eliminate hallucination.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION LOGIC (Triggered on click)
# ═══════════════════════════════════════════════════════════════════════════════
if uploaded_file and 'extract_btn' in locals() and extract_btn:
    with st.spinner("🔍 Running EasyOCR text detection & Gemini 2.5 Flash schema extraction…"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            response = httpx.post(f"{API_BASE}/extract", files=files, timeout=120)
            response.raise_for_status()
            st.session_state["result"] = response.json()
            st.rerun()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            st.error(f"❌ Extraction API Error: {detail}")
        except Exception as e:
            st.error(f"❌ Connection error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: EXTRACTED DATA, METRICS, TABLE, & DOWNLOADS
# ═══════════════════════════════════════════════════════════════════════════════
with right_col:
    if "result" in st.session_state:
        res = st.session_state["result"]
        res_id = res["id"]
        is_valid = res.get("is_valid", False)

        st.markdown(
            """
            <div class="card-panel">
            """,
            unsafe_allow_html=True,
        )

        # ── 1. Validation Banner ───────────────────────────────────────────────
        if is_valid:
            st.markdown(
                """
                <div class="validation-badge-banner valid">
                    <span>✔ ARITHMETIC AUDIT PASSED</span>
                    <span style="font-size:0.75rem; background:rgba(16,185,129,0.2); padding:0.2rem 0.6rem; border-radius:9999px;">Line sums match grand total</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="validation-badge-banner flagged">
                    <span>⚠ CALCULATION MISMATCH DETECTED</span>
                    <span style="font-size:0.75rem; background:rgba(239,68,68,0.2); padding:0.2rem 0.6rem; border-radius:9999px;">Manual check recommended</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if res.get("validation_notes"):
            for note in res["validation_notes"]:
                st.warning(f"⚠️ {note}")

        # ── 2. Four Key Header Metrics ─────────────────────────────────────────
        vendor_name = res.get("vendor") or "Unknown Vendor"
        inv_date = res.get("date") or "—"
        inv_num = res.get("invoice_number") or "—"
        grand_total = res.get("total")
        total_str = f"${grand_total:,.2f}" if grand_total is not None else "—"

        st.markdown(
            f"""
            <div class="metric-grid">
                <div class="metric-item">
                    <div class="metric-label">Vendor</div>
                    <div class="metric-val">{vendor_name}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Date</div>
                    <div class="metric-val blue">{inv_date}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Invoice #</div>
                    <div class="metric-val">{inv_num}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Grand Total</div>
                    <div class="metric-val green">{total_str}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── 3. Line Items Clean HTML Table ─────────────────────────────────────
        st.markdown("<div class='card-title'>📋 Itemized Charges</div>", unsafe_allow_html=True)

        items = res.get("items", [])
        if items:
            table_rows_html = ""
            for item in items:
                desc = item.get("description") or "—"
                qty = item.get("qty")
                qty_str = f"{qty:g}" if qty is not None else "—"
                unit_price = item.get("unit_price")
                unit_str = f"${unit_price:,.2f}" if unit_price is not None else "—"
                line_total = item.get("line_total")
                line_str = f"${line_total:,.2f}" if line_total is not None else "—"

                table_rows_html += f"""
                <tr>
                    <td class="bold">{desc}</td>
                    <td class="num">{qty_str}</td>
                    <td class="num">{unit_str}</td>
                    <td class="num bold" style="color:#38BDF8;">{line_str}</td>
                </tr>
                """

            st.markdown(
                f"""
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th style="width:50%;">Description</th>
                            <th class="num" style="width:14%;">Qty</th>
                            <th class="num" style="width:18%;">Unit Price</th>
                            <th class="num" style="width:18%;">Line Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No individual line items detected in this document.")

        # ── 4. Subtotal, Tax, and Final Balances ────────────────────────────────
        sub = res.get("subtotal")
        tax = res.get("tax")
        sub_str = f"${sub:,.2f}" if sub is not None else "—"
        tax_str = f"${tax:,.2f}" if tax is not None else "—"

        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; gap:2rem; padding:0.8rem 1.1rem; background:#141D32; border-radius:12px; border:1px solid #1E2D4A; margin-bottom:1.5rem; align-items:center;">
                <div style="font-size:0.85rem; color:#94A3B8;">Subtotal: <strong style="color:#F8FAFC; margin-left:0.3rem;">{sub_str}</strong></div>
                <div style="font-size:0.85rem; color:#94A3B8;">Tax: <strong style="color:#F8FAFC; margin-left:0.3rem;">{tax_str}</strong></div>
                <div style="font-size:1.1rem; color:#F8FAFC; font-weight:700;">Grand Total: <span style="color:#10B981; margin-left:0.4rem;">{total_str}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── 5. Action Bar: Downloads ───────────────────────────────────────────
        st.markdown("<div class='card-title' style='font-size:0.95rem;'>📥 Export Clean Data</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)

        dl1, dl2 = st.columns(2)
        with dl1:
            try:
                csv_bytes = httpx.get(f"{API_BASE}/download/{res_id}/csv", timeout=30).content
                st.download_button(
                    label="📄 Export to CSV",
                    data=csv_bytes,
                    file_name=f"invoice_{res_id[:8]}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"CSV error: {e}")

        with dl2:
            try:
                xlsx_bytes = httpx.get(f"{API_BASE}/download/{res_id}/excel", timeout=30).content
                st.download_button(
                    label="📊 Export to Excel (.xlsx)",
                    data=xlsx_bytes,
                    file_name=f"invoice_{res_id[:8]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Excel error: {e}")

        # ── 6. Raw OCR Text Inspection Drawer ──────────────────────────────────
        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
        with st.expander("🔍 Inspect Raw OCR Extracted Text (Debug)"):
            st.code(res.get("raw_text_preview", "(empty)"), language=None)

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Placeholder Empty State when no bill has been uploaded yet
        st.markdown(
            """
            <div class="card-panel" style="text-align:center; padding:4rem 2rem;">
                <div style="font-size:3.5rem; margin-bottom:1rem;">⚡</div>
                <h3 style="color:#F8FAFC; font-size:1.3rem; font-weight:700; margin-bottom:0.4rem;">No Invoice Loaded Yet</h3>
                <p style="color:#64748B; font-size:0.88rem; max-width:440px; margin:0 auto 1.5rem auto;">
                    Upload a receipt or invoice document on the left panel to trigger automatic OCR reading, LLM structured parsing, and math validation.
                </p>
                <div style="display:inline-flex; gap:1.5rem; color:#94A3B8; font-size:0.8rem; background:#141D32; padding:0.6rem 1.4rem; border-radius:9999px; border:1px solid #1E2D4A;">
                    <span>✔ Instant Table Parsing</span>
                    <span>✔ Arithmetic Hallucination Check</span>
                    <span>✔ CSV & Excel Export</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; color:#475569; font-size:0.78rem; margin-top:2rem;">
        QuickInvoice AI • Built with FastAPI, EasyOCR, OpenRouter & Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
