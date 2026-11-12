"""
app.py — Streamlit UI for the Invoice/Bill Data Extractor.
"""

import os
import io

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Invoice Extractor",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
    }

    /* Hero header */
    .hero-header {
        text-align: center;
        padding: 2.5rem 1rem 1rem;
    }
    .hero-header h1 {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
    }
    .hero-header p {
        color: #a0aec0;
        font-size: 1.1rem;
        font-weight: 300;
    }

    /* Glassmorphism card */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 1.8rem;
        backdrop-filter: blur(12px);
        margin-bottom: 1.5rem;
    }

    /* Status badge */
    .badge-valid {
        display: inline-block;
        background: linear-gradient(90deg, #38a169, #48bb78);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .badge-invalid {
        display: inline-block;
        background: linear-gradient(90deg, #c53030, #e53e3e);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }

    /* Section title */
    .section-title {
        color: #e2e8f0;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* Metric value */
    .metric-box {
        background: rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .metric-label {
        color: #a0aec0;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        color: #f7fafc;
        font-size: 1.3rem;
        font-weight: 700;
    }

    /* Upload area styling */
    [data-testid="stFileUploadDropzone"] {
        background: rgba(102, 126, 234, 0.08) !important;
        border: 2px dashed rgba(102, 126, 234, 0.5) !important;
        border-radius: 12px !important;
        color: #a0aec0 !important;
    }

    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Button overrides */
    .stDownloadButton > button {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }

    /* Warning / info colors */
    .stAlert {
        border-radius: 10px !important;
    }

    /* Step indicator */
    .step-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(102,126,234,0.15);
        border: 1px solid rgba(102,126,234,0.3);
        border-radius: 20px;
        padding: 0.3rem 0.9rem;
        font-size: 0.82rem;
        color: #a3b3f7;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-header">
        <h1>🧾 Invoice Extractor</h1>
        <p>Upload a bill image or PDF — get back clean, validated data instantly</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# How-it-works pills
st.markdown(
    """
    <div style="text-align:center; margin-bottom:2rem;">
        <span class="step-pill">📤 Upload Bill</span>
        <span class="step-pill">🔍 OCR Scan</span>
        <span class="step-pill">🤖 AI Extraction</span>
        <span class="step-pill">✅ Validation</span>
        <span class="step-pill">⬇️ Export CSV / Excel</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Upload Section ────────────────────────────────────────────────────────────
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">📁 Upload Invoice</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    label="Drag & drop or click to browse",
    type=["jpg", "jpeg", "png", "webp", "bmp", "pdf"],
    help="Supported formats: JPG, PNG, WEBP, BMP, PDF",
    label_visibility="collapsed",
)

if uploaded_file:
    col_prev, col_info = st.columns([1, 2])
    with col_prev:
        if uploaded_file.type != "application/pdf":
            st.image(uploaded_file, caption="Uploaded Invoice", use_container_width=True)
        else:
            st.markdown(
                f"""
                <div style="text-align:center; padding:2rem;
                     background:rgba(255,255,255,0.05); border-radius:10px;">
                    <div style="font-size:4rem;">📄</div>
                    <div style="color:#a0aec0; margin-top:0.5rem;">{uploaded_file.name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with col_info:
        st.markdown(
            f"""
            <div class="metric-box" style="text-align:left; padding:1rem;">
                <div><span style="color:#a0aec0;">File:</span> <span style="color:#e2e8f0;">{uploaded_file.name}</span></div>
                <div style="margin-top:0.4rem;"><span style="color:#a0aec0;">Size:</span> <span style="color:#e2e8f0;">{uploaded_file.size / 1024:.1f} KB</span></div>
                <div style="margin-top:0.4rem;"><span style="color:#a0aec0;">Type:</span> <span style="color:#e2e8f0;">{uploaded_file.type}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        extract_btn = st.button("🚀 Extract Invoice Data", use_container_width=True, type="primary")

st.markdown("</div>", unsafe_allow_html=True)

# ── Extraction ────────────────────────────────────────────────────────────────
if uploaded_file and extract_btn:
    with st.spinner("🔍 Running OCR and AI extraction… this may take 15–30 seconds"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            response = httpx.post(f"{API_BASE}/extract", files=files, timeout=120)
            response.raise_for_status()
            result = response.json()
            st.session_state["result"] = result
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", str(e))
            st.error(f"❌ API Error {e.response.status_code}: {detail}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Connection error: {e}")
            st.stop()

# ── Results ───────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]
    result_id = result["id"]

    st.markdown("---")

    # Validation badge
    if result["is_valid"]:
        badge = '<span class="badge-valid">✅ Totals Validated</span>'
    else:
        badge = '<span class="badge-invalid">⚠️ Validation Issues Found</span>'

    st.markdown(
        f'<div style="margin-bottom:1rem;">{badge}</div>',
        unsafe_allow_html=True,
    )

    if result["validation_notes"]:
        for note in result["validation_notes"]:
            st.warning(f"⚠️ {note}")

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📊 Invoice Summary</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class="metric-box">
                <div class="metric-label">Vendor</div>
                <div class="metric-value" style="font-size:1rem;">{result.get("vendor") or "—"}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="metric-box">
                <div class="metric-label">Date</div>
                <div class="metric-value" style="font-size:1rem;">{result.get("date") or "—"}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="metric-box">
                <div class="metric-label">Invoice #</div>
                <div class="metric-value" style="font-size:1rem;">{result.get("invoice_number") or "—"}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c4:
        total = result.get("total")
        total_str = f"${total:,.2f}" if total is not None else "—"
        st.markdown(
            f"""<div class="metric-box">
                <div class="metric-label">Grand Total</div>
                <div class="metric-value" style="color:#68d391;">{total_str}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Line items table ──────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📋 Line Items</p>', unsafe_allow_html=True)

    items = result.get("items", [])
    if items:
        df = pd.DataFrame(items)
        df.columns = [c.replace("_", " ").title() for c in df.columns]
        # Format numeric columns
        for col in ["Unit Price", "Line Total"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No line items were extracted.")

    # Totals row
    sub = result.get("subtotal")
    tax = result.get("tax")
    tot = result.get("total")
    totals_cols = st.columns(3)
    with totals_cols[0]:
        st.metric("Subtotal", f"${sub:,.2f}" if sub else "—")
    with totals_cols[1]:
        st.metric("Tax", f"${tax:,.2f}" if tax else "—")
    with totals_cols[2]:
        st.metric("Grand Total", f"${tot:,.2f}" if tot else "—")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">⬇️ Export Data</p>', unsafe_allow_html=True)

    dl1, dl2 = st.columns(2)
    with dl1:
        try:
            csv_resp = httpx.get(f"{API_BASE}/download/{result_id}/csv", timeout=30)
            csv_resp.raise_for_status()
            st.download_button(
                label="📄 Download CSV",
                data=csv_resp.content,
                file_name=f"invoice_{result_id[:8]}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"CSV download failed: {e}")

    with dl2:
        try:
            xlsx_resp = httpx.get(f"{API_BASE}/download/{result_id}/excel", timeout=30)
            xlsx_resp.raise_for_status()
            st.download_button(
                label="📊 Download Excel",
                data=xlsx_resp.content,
                file_name=f"invoice_{result_id[:8]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Excel download failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw OCR text (collapsed) ───────────────────────────────────────────────
    with st.expander("🔍 View Raw OCR Text (for debugging)"):
        st.code(result.get("raw_text_preview", "(none)"), language=None)
        st.caption("Showing first 500 characters of extracted text.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; color:#4a5568; font-size:0.8rem; margin-top:3rem; padding:1rem;">
        Invoice Extractor • Powered by EasyOCR + OpenRouter • Built with FastAPI & Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
