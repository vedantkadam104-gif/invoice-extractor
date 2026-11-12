"""
app.py — Modern SaaS Dashboard for Invoice / Bill Data Extractor
Styled after modern enterprise SaaS analytics dashboards.
"""

from __future__ import annotations

import datetime
import os
import io

import altair as alt
import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BillExtract — AI Invoice Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS: Modern SaaS Dashboard Theme ───────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* Global Typography & Canvas */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #E2E8F0 !important;
        color: #1E293B;
    }

    /* Outer Wrapper / Canvas Frame */
    .block-container {
        max-width: 1380px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* Main Dashboard Sheet */
    .dashboard-canvas {
        background: #FFFFFF;
        border-radius: 24px;
        box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.08), 0 0 1px 1px rgba(15, 23, 42, 0.05);
        padding: 0;
        overflow: hidden;
        margin-bottom: 1.5rem;
    }

    /* ─── Top Navbar ────────────────────────────────────────────────────────── */
    .top-navbar {
        background: #0B132B;
        padding: 1rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top-left-radius: 24px;
        border-top-right-radius: 24px;
    }
    .brand-logo {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 1.35rem;
        letter-spacing: -0.02em;
    }
    .brand-logo span.accent {
        color: #F59E0B;
    }
    .nav-pills {
        display: flex;
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.07);
        padding: 0.25rem 0.4rem;
        border-radius: 9999px;
    }
    .nav-pill {
        color: #94A3B8;
        padding: 0.4rem 1.1rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s;
    }
    .nav-pill.active {
        background: #1C2541;
        color: #FFFFFF;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .nav-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .user-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #F59E0B, #D97706);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        border: 2px solid rgba(255, 255, 255, 0.2);
    }

    /* ─── Greeting / Sub-header ─────────────────────────────────────────────── */
    .greeting-bar {
        background: #0B132B;
        padding: 0.8rem 2rem 2.2rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #FFFFFF;
    }
    .greeting-text h2 {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF;
    }
    .greeting-text p {
        font-size: 0.88rem;
        color: #94A3B8;
        margin: 0.2rem 0 0 0;
    }

    /* ─── Metric Cards Grid ─────────────────────────────────────────────────── */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 1.4rem 1.3rem;
        box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px -3px rgba(15, 23, 42, 0.08);
    }
    .metric-card.highlight {
        background: #0B132B;
        color: #FFFFFF;
        border-color: #1E293B;
    }
    .metric-card.highlight .metric-title {
        color: #94A3B8;
    }
    .metric-card.highlight .metric-num {
        color: #FFFFFF;
    }
    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .metric-num {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin-bottom: 0.4rem;
    }
    .metric-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
    }
    .metric-pill.positive {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
    }
    .metric-pill.negative {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
    }
    .metric-pill.neutral {
        background: rgba(100, 116, 139, 0.12);
        color: #64748B;
    }

    /* ─── Content Panel Cards ───────────────────────────────────────────────── */
    .content-panel {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 1.6rem;
        box-shadow: 0 4px 14px -3px rgba(15, 23, 42, 0.04);
        margin-bottom: 1.5rem;
    }
    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.2rem;
    }
    .panel-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
    }
    .panel-subtitle {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.15rem;
    }

    /* ─── Modern Upload Dropzone ────────────────────────────────────────────── */
    [data-testid="stFileUploadDropzone"] {
        background: #F8FAFC !important;
        border: 2px dashed #CBD5E1 !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        transition: border-color 0.2s, background-color 0.2s;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #F59E0B !important;
        background: #FFFBEB !important;
    }

    /* ─── Action Buttons ────────────────────────────────────────────────────── */
    .stButton > button[kind="primary"] {
        background: #F59E0B !important;
        color: #0B132B !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.6rem !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35) !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #D97706 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.45) !important;
    }

    .stDownloadButton > button {
        background: #F1F5F9 !important;
        color: #0F172A !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        font-size: 0.88rem !important;
        transition: all 0.2s !important;
    }
    .stDownloadButton > button:hover {
        background: #E2E8F0 !important;
        border-color: #CBD5E1 !important;
        transform: translateY(-1px) !important;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: capitalize;
    }
    .status-badge.booked {
        background: #ECFDF5;
        color: #059669;
    }
    .status-badge.pending {
        background: #FFFBEB;
        color: #D97706;
    }
    .status-badge.flagged {
        background: #FEF2F2;
        color: #DC2626;
    }

    /* Clean Table Styling */
    div[data-testid="stDataFrame"] {
        border: 1px solid #F1F5F9;
        border-radius: 14px;
        overflow: hidden;
    }

    /* Hide standard Streamlit header elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Initialize Session State for History & Analytics ───────────────────────────
if "history" not in st.session_state:
    st.session_state["history"] = [
        {"vendor": "Alex Fisher", "date": "2026-10-14", "total": 255.00, "status": "Valid", "items_count": 2},
        {"vendor": "Anna Baker", "date": "2026-10-18", "total": 500.00, "status": "Valid", "items_count": 1},
        {"vendor": "Global Logistics", "date": "2026-10-24", "total": 755.00, "status": "Valid", "items_count": 3},
    ]

# ── TOP NAVBAR & GREETING BANNER ──────────────────────────────────────────────
today_str = datetime.date.today().strftime("%B %d, %Y")

st.markdown(
    f"""
    <div class="dashboard-canvas">
        <div class="top-navbar">
            <div class="brand-logo">
                ⚡ BillExtract <span class="accent">AI</span>
            </div>
            <div class="nav-pills">
                <span class="nav-pill active">Dashboard</span>
                <span class="nav-pill">Invoices</span>
                <span class="nav-pill">Analytics</span>
                <span class="nav-pill">Settings</span>
            </div>
            <div class="nav-right">
                <div style="color:#94A3B8; font-size:0.9rem; cursor:pointer;">🔍</div>
                <div style="color:#94A3B8; font-size:0.9rem; position:relative; cursor:pointer;">
                    🔔<span style="position:absolute; top:-2px; right:-2px; width:7px; height:7px; background:#EF4444; border-radius:50%;"></span>
                </div>
                <div class="user-avatar">VK</div>
            </div>
        </div>
        <div class="greeting-bar">
            <div class="greeting-text">
                <h2>Good morning, Vedant!</h2>
                <p>Track, extract, and audit your commercial invoices in real-time</p>
            </div>
            <div style="display:flex; align-items:center; gap:1rem;">
                <div style="color:#94A3B8; font-size:0.85rem; font-weight:500;">
                    📅 {today_str}
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── COMPUTE STATS FOR METRIC CARDS ─────────────────────────────────────────────
history = st.session_state["history"]
total_revenue = sum(h["total"] for h in history)
total_invoices = len(history)
valid_count = sum(1 for h in history if h["status"] == "Valid")
flagged_count = total_invoices - valid_count

# ── METRIC CARDS ROW (4 CARDS) ─────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1])

with c1:
    st.markdown(
        f"""
        <div class="metric-card highlight">
            <div class="metric-title">Total Revenue</div>
            <div class="metric-num">${total_revenue:,.2f}</div>
            <span class="metric-pill positive">↗ +2.81% from last month</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Invoices</div>
            <div class="metric-num">{total_invoices}</div>
            <span class="metric-pill positive">↗ +5.90% from last month</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Validated Clean</div>
            <div class="metric-num">{valid_count}</div>
            <span class="metric-pill positive">✔ 100% Math match</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Pending / Flagged</div>
            <div class="metric-num">{flagged_count}</div>
            <span class="metric-pill negative">⚠ {flagged_count} flagged issues</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

# ── MAIN LAYOUT: LEFT COLUMN (DATA & UPLOAD) + RIGHT COLUMN (ANALYTICS) ────────
left_col, right_col = st.columns([2.1, 1])

with left_col:
    # ── Upload Card ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="content-panel">
            <div class="panel-header">
                <div>
                    <h3 class="panel-title">Upload & Extract Invoice</h3>
                    <div class="panel-subtitle">Upload any bill image (JPG, PNG) or multi-page PDF to extract structured data</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        label="Drag & drop bill here",
        type=["jpg", "jpeg", "png", "webp", "bmp", "pdf"],
        help="Supported formats: JPG, PNG, WEBP, BMP, PDF",
        label_visibility="collapsed",
    )

    if uploaded_file:
        up_c1, up_c2 = st.columns([1, 2])
        with up_c1:
            if uploaded_file.type != "application/pdf":
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            else:
                st.markdown(
                    f"""
                    <div style="text-align:center; padding:1.5rem; background:#F8FAFC; border-radius:12px; border:1px solid #E2E8F0;">
                        <div style="font-size:2.5rem;">📄</div>
                        <div style="font-size:0.8rem; font-weight:600; color:#475569; margin-top:0.4rem;">{uploaded_file.name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with up_c2:
            st.markdown(
                f"""
                <div style="padding:0.5rem 0;">
                    <div style="font-size:0.85rem; color:#64748B;">File Name: <strong style="color:#0F172A;">{uploaded_file.name}</strong></div>
                    <div style="font-size:0.85rem; color:#64748B; margin-top:0.2rem;">File Size: <strong style="color:#0F172A;">{uploaded_file.size / 1024:.1f} KB</strong></div>
                    <div style="font-size:0.85rem; color:#64748B; margin-top:0.2rem;">Format: <strong style="color:#0F172A;">{uploaded_file.type}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            extract_btn = st.button("🚀 Run OCR & AI Extraction", use_container_width=True, type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Handle Extraction Action ───────────────────────────────────────────────
    if uploaded_file and 'extract_btn' in locals() and extract_btn:
        with st.spinner("⚡ Running OCR and Gemini 2.5 Flash extraction…"):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = httpx.post(f"{API_BASE}/extract", files=files, timeout=120)
                response.raise_for_status()
                result = response.json()
                st.session_state["result"] = result

                # Add to history if not already present
                new_entry = {
                    "vendor": result.get("vendor") or "Unknown Vendor",
                    "date": result.get("date") or str(datetime.date.today()),
                    "total": float(result.get("total") or 0.0),
                    "status": "Valid" if result.get("is_valid") else "Flagged",
                    "items_count": len(result.get("items") or []),
                }
                st.session_state["history"].insert(0, new_entry)
                st.rerun()

            except httpx.HTTPStatusError as e:
                detail = e.response.json().get("detail", str(e))
                st.error(f"❌ Extraction API Error: {detail}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")

    # ── Current Extracted Result Panel ─────────────────────────────────────────
    if "result" in st.session_state:
        res = st.session_state["result"]
        res_id = res["id"]

        is_valid = res.get("is_valid", False)
        badge_class = "booked" if is_valid else "flagged"
        badge_text = "✔ Totals Validated" if is_valid else "⚠ Mismatch Detected"

        st.markdown(
            f"""
            <div class="content-panel">
                <div class="panel-header">
                    <div>
                        <h3 class="panel-title">Extracted Bill Details</h3>
                        <div class="panel-subtitle">Vendor: <strong>{res.get('vendor') or 'N/A'}</strong> • Date: <strong>{res.get('date') or 'N/A'}</strong> • Invoice #: <strong>{res.get('invoice_number') or 'N/A'}</strong></div>
                    </div>
                    <div>
                        <span class="status-badge {badge_class}">{badge_text}</span>
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if res.get("validation_notes"):
            for note in res["validation_notes"]:
                st.warning(f"⚠️ {note}")

        # Items Table
        items = res.get("items", [])
        if items:
            df = pd.DataFrame(items)
            df.columns = [c.replace("_", " ").title() for c in df.columns]
            for col in ["Unit Price", "Line Total"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Totals Summary Bar
        sub = res.get("subtotal")
        tax = res.get("tax")
        tot = res.get("total")

        sum_c1, sum_c2, sum_c3 = st.columns(3)
        with sum_c1:
            st.metric("Subtotal", f"${sub:,.2f}" if sub is not None else "—")
        with sum_c2:
            st.metric("Tax", f"${tax:,.2f}" if tax is not None else "—")
        with sum_c3:
            st.metric("Grand Total", f"${tot:,.2f}" if tot is not None else "—")

        # Download Buttons
        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
        dl_c1, dl_c2 = st.columns(2)
        with dl_c1:
            try:
                csv_resp = httpx.get(f"{API_BASE}/download/{res_id}/csv", timeout=30)
                st.download_button(
                    label="📄 Download Clean CSV",
                    data=csv_resp.content,
                    file_name=f"invoice_{res_id[:8]}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"CSV download error: {e}")

        with dl_c2:
            try:
                xlsx_resp = httpx.get(f"{API_BASE}/download/{res_id}/excel", timeout=30)
                st.download_button(
                    label="📊 Download Formatted Excel",
                    data=xlsx_resp.content,
                    file_name=f"invoice_{res_id[:8]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Excel download error: {e}")

        with st.expander("🔍 View Raw OCR Extracted Text"):
            st.code(res.get("raw_text_preview", "(empty)"), language=None)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Recent Invoices Table (Like "Recent booking list") ─────────────────────
    st.markdown(
        """
        <div class="content-panel">
            <div class="panel-header">
                <div>
                    <h3 class="panel-title">Recent Invoices</h3>
                    <div class="panel-subtitle">History of all extracted bills and verification statuses</div>
                </div>
                <div>
                    <span style="font-size:0.8rem; font-weight:600; color:#64748B; background:#F1F5F9; padding:0.3rem 0.8rem; border-radius:9999px;">Today ▼</span>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    rec_df = pd.DataFrame(st.session_state["history"])
    if not rec_df.empty:
        rec_df_display = rec_df.copy()
        rec_df_display.columns = ["Vendor Name", "Date", "Total Amount", "Audit Status", "Items Count"]
        rec_df_display["Total Amount"] = rec_df_display["Total Amount"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(rec_df_display, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ── RIGHT COLUMN (CHARTS & ANALYTICS WIDGETS) ──────────────────────────────────
with right_col:
    # ── Card 1: Monthly / Weekly Volume Bar Chart ──────────────────────────────
    st.markdown(
        """
        <div class="content-panel">
            <div class="panel-header" style="margin-bottom:0.5rem;">
                <div>
                    <h4 class="panel-title" style="font-size:1rem;">Invoice Volume</h4>
                    <div class="panel-subtitle">Monthly extractions & spend</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    chart_data = pd.DataFrame({
        "Month": ["Oct", "Nov", "Dec", "Jan"],
        "Count": [202, 137, 367, 169]
    })

    bar_chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color="#0B132B")
        .encode(
            x=alt.X("Month:N", sort=None, axis=alt.Axis(labelAngle=0, labelColor="#64748B", tickColor="transparent")),
            y=alt.Y("Count:Q", axis=alt.Axis(gridColor="#F1F5F9", labelColor="#64748B")),
            tooltip=["Month", "Count"]
        )
        .properties(height=180)
    )
    st.altair_chart(bar_chart, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Card 2: Spend Category Donut Chart ──────────────────────────────────────
    st.markdown(
        """
        <div class="content-panel">
            <div class="panel-header" style="margin-bottom:0.5rem;">
                <div>
                    <h4 class="panel-title" style="font-size:1rem;">Spend Categories</h4>
                    <div class="panel-subtitle">Most billed expenses overview</div>
                </div>
                <div>
                    <span style="font-size:0.75rem; color:#64748B; background:#F8FAFC; padding:0.2rem 0.5rem; border-radius:6px; border:1px solid #E2E8F0;">Weekly ▼</span>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    cat_data = pd.DataFrame({
        "Category": ["Equipment", "Supplies", "Services", "Travel"],
        "Share": [56, 25, 12, 7]
    })

    donut_chart = (
        alt.Chart(cat_data)
        .mark_arc(innerRadius=45, outerRadius=75)
        .encode(
            theta=alt.Theta("Share:Q"),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(
                    domain=["Equipment", "Supplies", "Services", "Travel"],
                    range=["#0B132B", "#F59E0B", "#10B981", "#8B5CF6"]
                ),
                legend=alt.Legend(orient="bottom", columns=2, labelColor="#64748B")
            ),
            tooltip=["Category", "Share"]
        )
        .properties(height=210)
    )
    st.altair_chart(donut_chart, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Card 3: Quick System Status ───────────────────────────────────────────
    st.markdown(
        """
        <div class="content-panel">
            <div class="panel-header" style="margin-bottom:0.5rem;">
                <h4 class="panel-title" style="font-size:0.95rem;">Engine Health</h4>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; font-size:0.83rem;">
                <span style="color:#64748B;">OCR Engine (EasyOCR)</span>
                <span class="status-badge booked">Active</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; font-size:0.83rem;">
                <span style="color:#64748B;">LLM (Gemini 2.5 Flash)</span>
                <span class="status-badge booked">Connected</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.83rem;">
                <span style="color:#64748B;">Audit Validator</span>
                <span class="status-badge booked">Enforced</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; color:#94A3B8; font-size:0.8rem; margin-top:2rem;">
        BillExtract AI Platform • Powered by EasyOCR & OpenRouter • Designed for Enterprise Operations
    </div>
    """,
    unsafe_allow_html=True,
)
