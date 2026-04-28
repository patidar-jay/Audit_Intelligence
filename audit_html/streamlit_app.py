"""
streamlit_app.py — Audit Intelligence (Streamlit Version)
Pure Python Streamlit app — replaces FastAPI + HTML/CSS/JS frontend.
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import os
import io
import sys
from pathlib import Path
from datetime import datetime, timedelta

# ── Setup path ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from modules.audit_engine import AuditEngine
from modules.database import (
    login_user, create_user, save_audit_session,
    get_audit_history, get_dashboard_stats,
    init_database, MYSQL_AVAILABLE,
)
from modules.gstin_validator import validate_gstin_format, validate_gstin_list

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Audit Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS — Enterprise Light Theme ────────────────────────────────────────
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown("""
<style>
/* ── Font applied ────────────────────────────────────────── */

/* ── HIDE DEFAULT STREAMLIT UI ───────────────────────────── */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}
div[data-testid="stToolbar"] {display: none;}

/* ── Root vars ───────────────────────────────────────────── */
:root {
    --primary:   #2563eb;
    --success:   #10b981;
    --warning:   #f59e0b;
    --danger:    #ef4444;
    --purple:    #8b5cf6;
    --dark:      #1e293b;
    --light-bg:  #f0f4f8;
    --card-bg:   #ffffff;
    --text:      #1a202c;
    --muted:     #64748b;
    --border:    #e2e8f0;
}

/* ── Global ──────────────────────────────────────────────── */
.stApp {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    background-color: #f0f4f8 !important;
    color: #1a202c;
}
.block-container { padding-top: 1.2rem !important; }

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #1e293b !important;
    border-right: none;
    box-shadow: 2px 0 20px rgba(0,0,0,0.08);
}
section[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #ffffff !important;
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    text-align: left;
    background: transparent;
    border: none !important;
    color: #94a3b8 !important;
    padding: 11px 14px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.18s;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(37, 99, 235, 0.15) !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] .stButton > button:focus {
    box-shadow: none !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.08) !important;
}

/* ── Upload zone (sidebar) ───────────────────────────────── */
section[data-testid="stFileUploader"] {
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
    padding: 8px;
    background: #f8fafc;
    transition: border-color 0.2s;
}
section[data-testid="stFileUploader"]:hover {
    border-color: #2563eb;
}
/* Override inside sidebar */
section[data-testid="stSidebar"] section[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.06);
    border-color: rgba(255,255,255,0.12);
}
section[data-testid="stSidebar"] section[data-testid="stFileUploader"]:hover {
    border-color: rgba(37,99,235,0.6);
}

/* ── CARD component ──────────────────────────────────────── */
.card {
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 24px;
    margin-bottom: 16px;
    border: 1px solid #e2e8f0;
}

/* ── KPI metric cards ────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    position: relative;
    border-left: 4px solid #2563eb;
}
div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 700 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #1a202c !important;
    font-weight: 900 !important;
    font-size: 28px !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: #64748b !important;
}

/* ── Tabs styling ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid #e2e8f0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-bottom: 3px solid transparent;
    color: #64748b;
    font-weight: 600;
    padding: 12px 22px;
    margin-bottom: -2px;
    transition: all 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #2563eb;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom-color: #2563eb !important;
    background: transparent !important;
}

/* ── Data tables ─────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 1px 8px rgba(0,0,0,0.04);
}

/* ── Primary buttons ─────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: #2563eb !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.2) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.3) !important;
    transform: translateY(-1px);
}
/* Secondary buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid #e2e8f0 !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: #2563eb !important;
    color: #2563eb !important;
}

/* ── Form submit buttons ─────────────────────────────────── */
.stFormSubmitButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* ── Insight cards ───────────────────────────────────────── */
.insight-card {
    border-left: 4px solid #2563eb;
    background: #ffffff;
    border-radius: 0 12px 12px 0;
    padding: 14px 18px;
    margin-bottom: 12px;
    font-size: 14px;
    line-height: 1.6;
    color: #1a202c;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}

/* ── Badge styles ────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    margin: 2px 3px;
}
.badge-danger  { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.badge-warning { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
.badge-success { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
.badge-cyan    { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.badge-purple  { background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe; }

/* ── Page header ─────────────────────────────────────────── */
.page-header {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.page-header h1 { font-size: 24px; font-weight: 900; color: #1a202c; margin: 0; }
.page-header .accent { color: #2563eb; }
.page-header p { color: #64748b; font-size: 13px; margin: 4px 0 0 0; }

/* ── Login box ───────────────────────────────────────────── */
.login-box {
    max-width: 460px;
    margin: 40px auto;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 36px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}
.login-logo {
    text-align: center;
    margin-bottom: 28px;
}
.login-logo .icon { font-size: 48px; }
.login-logo h1 { font-size: 28px; font-weight: 900; color: #1a202c; }
.login-logo .accent { color: #2563eb; }
.login-logo p { color: #64748b; font-size: 13px; }

/* ── Feature cards grid ──────────────────────────────────── */
.feature-grid {
    display: flex;
    justify-content: center;
    gap: 14px;
    flex-wrap: wrap;
    margin-top: 20px;
}
.feature-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    min-width: 160px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    transition: transform 0.2s, box-shadow 0.2s;
}
.feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
}
.feature-card .feat-icon { font-size: 32px; }
.feature-card .feat-title { font-weight: 700; margin-top: 8px; color: #1a202c; }
.feature-card .feat-sub { color: #64748b; font-size: 12px; margin-top: 2px; }

/* ── Score bar ───────────────────────────────────────────── */
.score-bar-wrap { display: flex; align-items: center; gap: 8px; }
.score-bar-bg {
    flex: 1; height: 8px; background: #e2e8f0;
    border-radius: 4px; overflow: hidden;
}
.score-bar-fill { height: 100%; border-radius: 4px; }

/* ── Footer ──────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #94a3b8;
    font-size: 12px;
    margin-top: 48px;
    padding: 16px;
    border-top: 1px solid #e2e8f0;
}

/* ══════════════════════════════════════════════════════════ */
/*  HOME PAGE STYLES                                         */
/* ══════════════════════════════════════════════════════════ */

/* ── Hero section ────────────────────────────────────────── */
.hero-section {
    text-align: center;
    padding: 60px 20px 40px;
    position: relative;
}
.hero-section::before {
    content: '';
    position: absolute;
    top: -40px; left: 50%; transform: translateX(-50%);
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(37,99,235,0.06) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
}
.hero-badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 24px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #2563eb;
    margin-bottom: 24px;
    animation: fadeInDown 0.6s ease;
}
.hero-title {
    font-size: 50px;
    font-weight: 900;
    line-height: 1.1;
    color: #1a202c;
    margin: 0 0 18px 0;
    animation: fadeInUp 0.7s ease;
}
.hero-title .accent {
    background: linear-gradient(135deg, #2563eb, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-subtitle {
    font-size: 18px;
    color: #64748b;
    max-width: 620px;
    margin: 0 auto 36px;
    line-height: 1.7;
    animation: fadeInUp 0.8s ease;
}

/* ── Stats bar ───────────────────────────────────────────── */
.stats-bar {
    display: flex;
    justify-content: center;
    gap: 48px;
    flex-wrap: wrap;
    padding: 32px 0;
    margin: 32px 0;
    border-top: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    animation: fadeIn 1s ease;
}
.stat-item { text-align: center; min-width: 120px; }
.stat-value {
    font-size: 38px;
    font-weight: 900;
    background: linear-gradient(135deg, #2563eb, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-label {
    font-size: 12px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-top: 6px;
}

/* ── Section titles ──────────────────────────────────────── */
.home-section-title {
    text-align: center;
    font-size: 34px;
    font-weight: 900;
    color: #1a202c;
    margin: 56px 0 8px;
}
.home-section-sub {
    text-align: center;
    font-size: 15px;
    color: #64748b;
    margin-bottom: 40px;
    max-width: 520px;
    margin-left: auto;
    margin-right: auto;
}

/* ── Glass feature cards (home) ──────────────────────────── */
.glass-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 30px 24px;
    text-align: center;
    transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
    position: relative;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.glass-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(37,99,235,0.1);
    border-color: #bfdbfe;
}
.glass-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    border-radius: 16px 16px 0 0;
}
.glass-card.glow-cyan::after    { background: linear-gradient(90deg, #2563eb, #3b82f6); }
.glass-card.glow-purple::after  { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.glass-card.glow-green::after   { background: linear-gradient(90deg, #10b981, #34d399); }
.glass-card.glow-warning::after { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.glass-card.glow-danger::after  { background: linear-gradient(90deg, #ef4444, #f87171); }
.glass-card.glow-teal::after    { background: linear-gradient(90deg, #14b8a6, #2dd4bf); }

.glass-icon { font-size: 42px; margin-bottom: 16px; display: block; }
.glass-title { font-size: 17px; font-weight: 800; color: #1a202c; margin-bottom: 8px; }
.glass-desc { font-size: 13px; color: #64748b; line-height: 1.6; }

/* ── How it works ────────────────────────────────────────── */
.step-card {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 22px 20px;
    margin-bottom: 14px;
    transition: border-color 0.2s, box-shadow 0.2s;
    box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.step-card:hover {
    border-color: #bfdbfe;
    box-shadow: 0 4px 16px rgba(37,99,235,0.06);
}
.step-num {
    min-width: 42px; height: 42px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 900;
    background: linear-gradient(135deg, #2563eb, #8b5cf6);
    color: #ffffff;
    flex-shrink: 0;
}
.step-body h4 { font-size: 15px; font-weight: 800; color: #1a202c; margin: 0 0 4px; }
.step-body p { font-size: 13px; color: #64748b; margin: 0; line-height: 1.55; }

/* ── Tech stack pills ────────────────────────────────────── */
.tech-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 30px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    font-size: 13px;
    font-weight: 600;
    color: #1a202c;
    margin: 5px;
    transition: all 0.2s;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.tech-pill:hover {
    border-color: #2563eb;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.08);
}
.tech-pill .pill-icon { font-size: 18px; }

/* ── CTA banner ──────────────────────────────────────────── */
.cta-banner {
    background: linear-gradient(135deg, #eff6ff, #f5f3ff);
    border: 1px solid #bfdbfe;
    border-radius: 20px;
    padding: 44px 32px;
    text-align: center;
    margin: 48px 0;
}
.cta-banner h2 { font-size: 30px; font-weight: 900; color: #1a202c; margin: 0 0 10px; }
.cta-banner p { color: #64748b; font-size: 15px; margin: 0 0 24px; }

/* ── Animations ──────────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {
    .hero-title { font-size: 32px; }
    .hero-subtitle { font-size: 15px; }
    .stats-bar { gap: 24px; }
    .stat-value { font-size: 28px; }
    .home-section-title { font-size: 24px; }
}

/* ── Alert boxes ─────────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
}

/* ── Text inputs ─────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
    transition: border-color 0.15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}

/* ── Select boxes ────────────────────────────────────────── */
.stSelectbox > div > div {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def fmt_inr(n):
    """Format number as Indian Rupees."""
    n = float(n or 0)
    if n >= 1e7:
        return f"₹{n/1e7:.2f} Cr"
    if n >= 1e5:
        return f"₹{n/1e5:.2f} L"
    if n >= 1000:
        return f"₹{n/1000:.1f}K"
    return f"₹{n:.2f}"


def risk_color(score):
    """Return color based on risk score."""
    if score >= 60:
        return "#ef4444"
    if score >= 30:
        return "#f59e0b"
    return "#10b981"


def detect_and_validate_gstin(file_path):
    """Detect GSTIN columns in the data and validate each GSTIN."""
    import re
    gstin_pattern = re.compile(r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')

    # Load the file
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception:
        return []

    # Find columns that might contain GSTINs
    gstin_results = []
    seen = set()

    for col in df.columns:
        col_lower = col.strip().lower().replace(" ", "_")
        # Check column name hints OR sample values
        is_gstin_col = any(kw in col_lower for kw in ["gstin", "gst_no", "gst_number", "gst", "gstn"])

        if not is_gstin_col:
            # Sample first 10 non-null values to detect GSTIN pattern
            sample_vals = df[col].dropna().astype(str).head(10)
            match_count = sum(1 for v in sample_vals if gstin_pattern.match(v.strip().upper()))
            if match_count >= 3:  # At least 3 out of 10 match → likely GSTIN column
                is_gstin_col = True

        if is_gstin_col:
            for idx, val in df[col].dropna().items():
                raw = str(val).strip().upper()
                if raw and raw != "NAN" and raw not in seen:
                    seen.add(raw)
                    result = validate_gstin_format(raw)
                    gstin_results.append({
                        "row": int(idx) + 1,
                        "column": col,
                        "gstin": raw,
                        "valid": result["valid"],
                        "state": result.get("state", "—") or "—",
                        "state_code": result.get("state_code", "—") or "—",
                        "pan": result.get("pan", "—") or "—",
                        "message": result.get("message", ""),
                    })

    return gstin_results


@st.cache_data(show_spinner=False)
def generate_sample_data():
    """Generate sample transaction data for demo."""
    np.random.seed(42)
    n = 200
    vendors = [
        "Tech Supplies", "Office Depot", "Apex Solutions", "Global Traders",
        "Swift Logistics", "Alpha Corp", "Beta Services", "Gamma Ltd",
    ]
    categories = [
        "IT Equipment", "Office Supplies", "Travel", "Consulting",
        "Marketing", "Utilities", "Maintenance", "Software",
    ]
    # GSTIN numbers per vendor (mix of valid/invalid for demo)
    vendor_gstins = {
        "Tech Supplies":   "27AAPFU0939F1ZV",
        "Office Depot":    "29ABCDE1234F1Z5",
        "Apex Solutions":  "07CQZCD1234M1ZX",
        "Global Traders":  "33XYZAB5678G2ZK",
        "Swift Logistics": "24AAAAA0000A1Z5",
        "Alpha Corp":      "09BBBBB1111B1Z3",
        "Beta Services":   "INVALIDGSTIN123",  # intentionally invalid
        "Gamma Ltd":       "23CCCCC2222C1Z7",
    }
    dates = [
        datetime(2024, 1, 1) + timedelta(days=int(x))
        for x in np.random.randint(0, 365, n)
    ]
    vendor_choices = np.random.choice(vendors, n)
    df = pd.DataFrame({
        "Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Invoice_Number": [f"INV-{1000+i}" for i in range(n)],
        "Vendor_Name": vendor_choices,
        "GSTIN": [vendor_gstins[v] for v in vendor_choices],
        "Amount": np.random.lognormal(9, 1.5, n).round(2),
        "Payment_Mode": np.random.choice(["Bank", "UPI", "Cash"], n, p=[0.6, 0.25, 0.15]),
        "Category": np.random.choice(categories, n),
        "Txn_Type": np.random.choice(["Debit", "Debit", "Debit", "Credit"], n),
    })
    # Inject anomalies for demo
    df.loc[10, "Invoice_Number"] = df.loc[5, "Invoice_Number"]
    df.loc[11, "Invoice_Number"] = df.loc[5, "Invoice_Number"]
    df.loc[20, ["Amount", "Payment_Mode", "Date", "Vendor_Name"]] = [6000, "Cash", "2024-03-15", "Alpha Corp"]
    df.loc[21, ["Amount", "Payment_Mode", "Date", "Vendor_Name"]] = [5500, "Cash", "2024-03-15", "Alpha Corp"]
    df.loc[30, "Amount"] = 850000
    df.loc[40, ["Amount", "Payment_Mode"]] = [9500, "Cash"]
    df.loc[41, ["Amount", "Payment_Mode"]] = [9600, "Cash"]
    return df


def run_audit_on_file(uploaded_file):
    """Save uploaded file to temp, run audit engine, return results."""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        engine = AuditEngine(tmp_path)
        results = engine.run_full_audit()
        # Auto-detect and validate GSTINs
        results["gstin_validation"] = detect_and_validate_gstin(tmp_path)
        return results
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def run_audit_on_df(df):
    """Save DataFrame to temp CSV, run audit engine, return results."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            df.to_csv(tmp, index=False)
            tmp_path = tmp.name
        engine = AuditEngine(tmp_path)
        results = engine.run_full_audit()
        # Auto-detect and validate GSTINs
        results["gstin_validation"] = detect_and_validate_gstin(tmp_path)
        return results
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── Plotly chart helpers ───────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#1a202c", family="Inter, Segoe UI, Arial, sans-serif"),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0"),
    yaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0"),
)


@st.cache_data(show_spinner=False)
def make_bar_chart(labels, values, color="#2563eb", title=""):
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=color,
        marker_line_width=0,
    ))
    fig.update_layout(title=title, **CHART_LAYOUT, height=300)
    return fig


@st.cache_data(show_spinner=False)
def make_line_chart(labels, values, color="#2563eb", title=""):
    # Convert hex color to rgba for fill transparency
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    fill_rgba = f"rgba({r},{g},{b},0.13)"
    fig = go.Figure(go.Scatter(
        x=labels, y=values,
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        fill="tozeroy",
        fillcolor=fill_rgba,
    ))
    fig.update_layout(title=title, **CHART_LAYOUT, height=300)
    return fig


@st.cache_data(show_spinner=False)
def make_pie_chart(labels, values, title=""):
    colors = ["#2563eb", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#6366f1", "#ec4899", "#14b8a6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors[:len(labels)]),
        hole=0.4,
        textinfo="label+percent",
    ))
    fig.update_layout(title=title, **CHART_LAYOUT, height=300, showlegend=True)
    return fig


@st.cache_data(show_spinner=False, ttl=300)
def get_cached_history(user_id, limit=30):
    """Cache audit history for 5 minutes to avoid DB hits on every rerun."""
    return get_audit_history(user_id, limit)

@st.cache_data(show_spinner=False, ttl=300)
def get_cached_stats(user_id):
    """Cache dashboard stats for 5 minutes."""
    return get_dashboard_stats(user_id)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"
if "audit_results" not in st.session_state:
    st.session_state.audit_results = None
if "show_home" not in st.session_state:
    st.session_state.show_home = True

# Initialize DB on startup
if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = False
    if MYSQL_AVAILABLE:
        st.session_state.db_initialized = init_database()


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN / REGISTER PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_login():
    st.markdown("""
    <div class="login-logo">
        <div class="icon">🔍</div>
        <h1>Audit <span class="accent">Intelligence</span></h1>
        <p>AI-Based Financial Fraud Detection System</p>
    </div>
    """, unsafe_allow_html=True)

    if not MYSQL_AVAILABLE:
        st.warning("⚠️ MySQL not connected — running in Demo Mode")

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("Login →", type="primary")
            with col2:
                demo_btn = st.form_submit_button("🎯 Try Demo")

            if login_btn:
                if not username or not password:
                    st.error("Please enter username and password.")
                elif not MYSQL_AVAILABLE:
                    # Demo mode login
                    st.session_state.logged_in = True
                    st.session_state.user = {
                        "id": 1, "username": username,
                        "full_name": username.title(),
                        "email": "demo@example.com", "role": "auditor",
                    }
                    st.toast("✅ Logged in (Demo Mode)!", icon="🎯")
                    st.rerun()
                else:
                    user, msg = login_user(username, password)
                    if user:
                        safe = {k: str(v) if hasattr(v, "isoformat") else v
                                for k, v in user.items() if k != "password_hash"}
                        st.session_state.logged_in = True
                        st.session_state.user = safe
                        st.toast("✅ Login successful!", icon="✅")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

            if demo_btn:
                st.session_state.logged_in = True
                st.session_state.user = {
                    "id": 1, "username": "demo_user",
                    "full_name": "Demo Auditor",
                    "email": "demo@medicaps.ac.in", "role": "auditor",
                }
                st.toast("🎯 Demo login successful!", icon="🎯")
                st.rerun()

        st.info("Default admin: **admin** / **admin123**")

    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            reg_name = st.text_input("Full Name", placeholder="Your full name")
            reg_user = st.text_input("Username", placeholder="Choose a username", key="reg_username")
            reg_email = st.text_input("Email", placeholder="your@email.com")
            reg_pass = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_password")
            reg_conf = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
            reg_btn = st.form_submit_button("Create Account →", type="primary")

            if reg_btn:
                if not all([reg_name, reg_user, reg_email, reg_pass, reg_conf]):
                    st.error("Please fill in all fields.")
                elif len(reg_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif reg_pass != reg_conf:
                    st.error("Passwords do not match.")
                elif not MYSQL_AVAILABLE:
                    st.error("Database not connected. Use Demo Login.")
                else:
                    ok, msg = create_user(reg_user, reg_email, reg_pass, reg_name)
                    if ok:
                        st.success(f"✅ {msg} You can now login.")
                    else:
                        st.error(f"❌ {msg}")

    st.markdown("""
    <div class="footer">
        Medi-Caps University · Jay Solanki & Jaydeep Patidar · B.Tech CSE 2023-27
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR (shown when logged in)
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🔍 Audit **Intelligence**")

        user = st.session_state.user or {}
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.08); border-radius:10px; padding:10px 12px; margin-bottom:12px;">
            <div style="font-weight:700; font-size:14px; color:#ffffff;">{user.get('full_name', 'User')}</div>
            <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Role: {str(user.get('role', 'auditor')).title()}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:1px; padding:4px;'>Navigation</div>", unsafe_allow_html=True)

        if st.button("📊 Dashboard", key="nav_dashboard"):
            st.session_state.current_page = "Dashboard"
            st.rerun()
        if st.button("📜 Audit History", key="nav_history"):
            st.session_state.current_page = "History"
            st.rerun()
        if st.button("🔍 GSTIN Validator", key="nav_gstin"):
            st.session_state.current_page = "GSTIN"
            st.rerun()

        st.divider()

        # Upload section
        st.markdown("<div style='font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:1px; padding:4px;'>Upload</div>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "📁 Upload CSV / Excel",
            type=["csv", "xlsx", "xls"],
            key="file_uploader",
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            sample_btn = st.button("⬇ Sample", key="sample_btn")
        with col2:
            demo_btn = st.button("🚀 Demo", key="demo_btn")

        if sample_btn:
            sample_df = generate_sample_data()
            csv_data = sample_df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv_data,
                file_name="sample_transactions.csv",
                mime="text/csv",
                key="download_sample",
            )

        if demo_btn:
            with st.spinner("🚀 Running AI Audit Pipeline..."):
                sample_df = generate_sample_data()
                results = run_audit_on_df(sample_df)
                st.session_state.audit_results = results
                if MYSQL_AVAILABLE:
                    user_id = st.session_state.user.get("id", 1)
                    save_audit_session(user_id, "sample_transactions.csv", results)
            st.session_state.current_page = "Dashboard"
            st.toast("✅ Demo audit complete!", icon="✅")
            st.rerun()

        if uploaded_file is not None:
            if st.button("▶ Run Audit", type="primary", key="run_audit_btn"):
                with st.spinner("🔍 Running AI Audit Pipeline..."):
                    results = run_audit_on_file(uploaded_file)
                    st.session_state.audit_results = results
                    if MYSQL_AVAILABLE:
                        user_id = st.session_state.user.get("id", 1)
                        save_audit_session(user_id, uploaded_file.name, results)
                st.session_state.current_page = "Dashboard"
                st.toast("✅ Audit complete!", icon="✅")
                st.rerun()

        st.divider()

        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.audit_results = None
            st.session_state.current_page = "Dashboard"
            st.session_state.show_home = True
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    st.markdown("""
    <div class="page-header">
        <h1>🔍 Audit <span class="accent">Intelligence</span></h1>
        <p>AI-Based Financial Fraud Detection · Isolation Forest + Rule Engine</p>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.audit_results

    if results is None:
        # Landing state
        st.markdown("""
        <div style="text-align:center; padding:40px 20px;">
            <div style="font-size:56px; margin-bottom:16px;">📊</div>
            <div style="font-size:20px; font-weight:800; margin-bottom:8px; color:#1a202c;">Upload a File to Start Audit</div>
            <p style="color:#64748b; font-size:14px; margin-bottom:28px;">Use the sidebar to upload CSV or Excel, or click Run Demo</p>
        </div>
        """, unsafe_allow_html=True)

        # Feature cards
        cols = st.columns(4)
        features = [
            ("🤖", "Isolation Forest AI", "Anomaly Detection"),
            ("📋", "4 Compliance Rules", "Rule-Based Engine"),
            ("🏢", "Vendor Risk Score", "0–100 Rating"),
            ("📄", "PDF Reports", "Download Anytime"),
        ]
        for col, (icon, title, sub) in zip(cols, features):
            with col:
                st.markdown(f"""
                <div class="feature-card">
                    <div class="feat-icon">{icon}</div>
                    <div class="feat-title">{title}</div>
                    <div class="feat-sub">{sub}</div>
                </div>
                """, unsafe_allow_html=True)
        return

    # ── We have audit results — render them ────────────────────────────────────
    s = results["summary"]

    st.success(f"✅ Audit complete! **{s['total_transactions']:,}** transactions analyzed — "
               f"**{s['total_flagged']}** flagged (**{s['flag_rate']}%**)")

    # Tabs — include GSTIN tab if validation data exists
    gstin_data = results.get("gstin_validation", [])
    if gstin_data:
        tab_overview, tab_flagged, tab_vendors, tab_analytics, tab_gstin = st.tabs([
            "📋 Overview", "🚨 Flagged Transactions", "🏢 Vendor Risk", "📈 Analytics", "🔍 GSTIN Check"
        ])
    else:
        tab_overview, tab_flagged, tab_vendors, tab_analytics = st.tabs([
            "📋 Overview", "🚨 Flagged Transactions", "🏢 Vendor Risk", "📈 Analytics"
        ])

    # ── TAB 1: Overview ────────────────────────────────────────────────────────
    with tab_overview:
        # KPI metrics
        row1 = st.columns(4)
        kpis_row1 = [
            ("Transactions", f"{s['total_transactions']:,}", "Total analyzed"),
            ("Total Amount", fmt_inr(s["total_amount"]), "Sum of all amounts"),
            ("Flagged", str(s["total_flagged"]), f"{s['flag_rate']}% rate"),
            ("High Risk Vendors", str(s["high_risk_vendors"]), "Need investigation"),
        ]
        for col, (label, value, delta) in zip(row1, kpis_row1):
            with col:
                st.metric(label=label, value=value, delta=delta, delta_color="off")

        row2 = st.columns(4)
        kpis_row2 = [
            ("Duplicate Invoices", str(s["duplicate_invoices"]), "Same type duplicates"),
            ("Cash Violations", str(s["cash_violations"]), "Daily total >₹10K"),
            ("Structured Pmts", str(s["structured_payments"]), "₹8K-9.9K pattern"),
            ("AI Anomalies", str(s["ai_anomalies"]), "Isolation Forest"),
        ]
        for col, (label, value, delta) in zip(row2, kpis_row2):
            with col:
                st.metric(label=label, value=value, delta=delta, delta_color="off")

        st.markdown("")

        # Insights
        st.markdown("### 💡 AI Insights")
        insights = results.get("insights", [])
        if insights:
            for insight in insights:
                st.markdown(f'<div class="insight-card">{insight}</div>', unsafe_allow_html=True)
        else:
            st.info("No insights generated.")

        st.markdown("")

        # Charts — Flag breakdown + Payment mode
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            fd = results.get("charts", {}).get("flag_distribution", {})
            if fd:
                fig = make_bar_chart(
                    list(fd.keys()), list(fd.values()),
                    color="#ef4444", title="Flag Breakdown"
                )
                st.plotly_chart(fig, key="chart_flag_dist")

        with chart_col2:
            pm = results.get("charts", {}).get("payment_mode", {})
            if pm:
                fig = make_pie_chart(
                    pm.get("labels", []), pm.get("values", []),
                    title="Payment Mode Distribution"
                )
                st.plotly_chart(fig, key="chart_payment_mode")

        # PDF download button
        if s["total_flagged"] > 0:
            try:
                from fpdf import FPDF

                def _safe(text):
                    """Sanitize text for fpdf2 (ASCII-safe, no Unicode symbols)."""
                    return str(text).encode("ascii", "replace").decode("ascii")

                def generate_pdf():
                    try:
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Helvetica", "B", 18)
                        pdf.cell(0, 12, "Audit Intelligence Report", ln=True, align="C")
                        pdf.set_font("Helvetica", "", 10)
                        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                        pdf.ln(10)

                        # Summary
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.cell(0, 10, "Summary", ln=True)
                        pdf.set_font("Helvetica", "", 11)
                        for key, val in s.items():
                            label = key.replace("_", " ").title()
                            pdf.cell(0, 7, _safe(f"{label}: {val}"), ln=True)
                        pdf.ln(5)

                        # Insights
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.cell(0, 10, "AI Insights", ln=True)
                        pdf.set_font("Helvetica", "", 10)
                        for ins in insights:
                            pdf.multi_cell(0, 6, _safe(f"  - {ins}"))
                        pdf.ln(5)

                        # Flagged transactions
                        sus = results.get("suspicious_transactions", [])
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.cell(0, 10, f"Flagged Transactions ({len(sus)})", ln=True)
                        pdf.set_font("Helvetica", "", 8)
                        for t in sus[:50]:
                            flags = ", ".join(t.get("reasons", []))
                            line = f"Row {t['row']}: {t['vendor']} | Rs {t['amount']:,.2f} | {t['mode']} | {flags}"
                            pdf.cell(0, 5, _safe(line), ln=True)

                        return pdf.output()
                    except Exception:
                        return None

                if st.button("📄 Generate PDF Report", key="gen_pdf_btn"):
                    with st.spinner("Generating PDF..."):
                        pdf_data = generate_pdf()
                    if pdf_data:
                        st.download_button(
                            "⬇ Download PDF",
                            data=pdf_data,
                            file_name="audit_report.pdf",
                            mime="application/pdf",
                            key="download_pdf_btn",
                        )
                    else:
                        st.warning("PDF generation failed. Try exporting as CSV instead.")
            except ImportError:
                st.info("Install fpdf2 for PDF: `pip install fpdf2`")

    # ── TAB 2: Flagged Transactions ────────────────────────────────────────────
    with tab_flagged:
        txns = results.get("suspicious_transactions", [])

        if txns:
            # Filters
            filter_col1, filter_col2 = st.columns([3, 1])
            with filter_col1:
                search = st.text_input("🔍 Search vendor or invoice...", key="txn_search")
            with filter_col2:
                flag_options = ["All Flags", "Duplicate Invoice", "Cash Limit Breach",
                                "Structured Payment", "AI Anomaly"]
                flag_filter = st.selectbox("Filter by flag", flag_options, key="flag_filter")

            # Apply filters
            filtered_txns = txns
            if search:
                search_low = search.lower()
                filtered_txns = [
                    t for t in filtered_txns
                    if search_low in t["vendor"].lower() or search_low in t["invoice"].lower()
                ]
            if flag_filter != "All Flags":
                filtered_txns = [t for t in filtered_txns if flag_filter in t.get("reasons", [])]

            st.markdown(f"**{len(filtered_txns)}** transactions shown")
            st.info("💡 **Suggested Amount** column shows the category average — "
                    "use this to correct AI anomaly values.")

            # Build DataFrame for display
            if filtered_txns:
                txn_df = pd.DataFrame(filtered_txns)
                display_df = txn_df[[
                    "row", "date", "invoice", "vendor", "txn_type",
                    "amount", "suggested_amount", "mode", "category",
                    "anomaly_score", "reasons"
                ]].copy()
                display_df.columns = [
                    "#", "Date", "Invoice", "Vendor", "Type",
                    "Amount (₹)", "Suggested (₹)", "Mode", "Category",
                    "AI Score", "Flags"
                ]
                display_df["Flags"] = display_df["Flags"].apply(
                    lambda x: " | ".join(x) if isinstance(x, list) else str(x)
                )
                display_df["Amount (₹)"] = display_df["Amount (₹)"].apply(
                    lambda x: f"₹{float(x):,.2f}" if pd.notna(x) else "₹0.00"
                )
                display_df["Suggested (₹)"] = display_df["Suggested (₹)"].apply(
                    lambda x: f"₹{float(x):,.2f}" if x and x != "" and str(x) != "nan" else "—"
                )
                display_df["AI Score"] = display_df["AI Score"].apply(
                    lambda x: f"{float(x):.1f}" if pd.notna(x) and str(x) != "nan" else "0.0"
                )

                st.dataframe(display_df, hide_index=True, height=500)

                # Export CSV
                csv_data = txn_df.to_csv(index=False)
                st.download_button(
                    "⬇ Export Flagged Transactions CSV",
                    data=csv_data,
                    file_name="flagged_transactions.csv",
                    mime="text/csv",
                    key="dl_flagged_csv",
                )
        else:
            st.info("No flagged transactions found.")

    # ── TAB 3: Vendor Risk ─────────────────────────────────────────────────────
    with tab_vendors:
        vendors = results.get("vendor_risk", [])

        if vendors:
            # Risk summary
            high = len([v for v in vendors if v["Risk_Level"] == "High"])
            med = len([v for v in vendors if v["Risk_Level"] == "Medium"])
            low = len([v for v in vendors if v["Risk_Level"] == "Low"])

            risk_col1, risk_col2, risk_col3 = st.columns(3)
            with risk_col1:
                st.markdown(f'<span class="badge badge-danger">🔴 High: {high}</span>', unsafe_allow_html=True)
            with risk_col2:
                st.markdown(f'<span class="badge badge-warning">🟡 Medium: {med}</span>', unsafe_allow_html=True)
            with risk_col3:
                st.markdown(f'<span class="badge badge-success">🟢 Low: {low}</span>', unsafe_allow_html=True)

            # Filters
            v_col1, v_col2, v_col3, v_col4 = st.columns([3, 1, 1, 1])
            with v_col1:
                v_search = st.text_input("🔍 Search vendor...", key="vendor_search")
            with v_col2:
                show_high = st.checkbox("High", value=True, key="chk_high")
            with v_col3:
                show_med = st.checkbox("Medium", value=True, key="chk_med")
            with v_col4:
                show_low = st.checkbox("Low", value=True, key="chk_low")

            # Filter
            filtered_vendors = vendors
            if v_search:
                v_search_low = v_search.lower()
                filtered_vendors = [v for v in filtered_vendors
                                    if v_search_low in v["Vendor_Name"].lower()]
            level_filter = set()
            if show_high: level_filter.add("High")
            if show_med:  level_filter.add("Medium")
            if show_low:  level_filter.add("Low")
            filtered_vendors = [v for v in filtered_vendors if v["Risk_Level"] in level_filter]

            # Build display table
            if filtered_vendors:
                v_df = pd.DataFrame(filtered_vendors)
                display_vdf = v_df[[
                    "Vendor_Name", "Total_Transactions", "Total_Amount",
                    "Flagged_Transactions", "Risk_Score", "Risk_Level"
                ]].copy()
                display_vdf.columns = [
                    "Vendor", "Transactions", "Total Amount",
                    "Flagged", "Risk Score", "Risk Level"
                ]
                display_vdf["Total Amount"] = display_vdf["Total Amount"].apply(lambda x: f"₹{x:,.2f}")
                display_vdf["Risk Score"] = display_vdf["Risk Score"].apply(lambda x: f"{x}/100")

                st.dataframe(display_vdf, hide_index=True, height=500)

                csv_data = v_df.to_csv(index=False)
                st.download_button(
                    "⬇ Export Vendor Risk CSV",
                    data=csv_data,
                    file_name="vendor_risk.csv",
                    mime="text/csv",
                    key="dl_vendor_csv",
                )
            else:
                st.info("No vendors match the current filters.")
        else:
            st.info("No vendor data available.")

    # ── TAB 4: Analytics ───────────────────────────────────────────────────────
    with tab_analytics:
        charts = results.get("charts", {})

        # Monthly trend
        mt = charts.get("monthly_trend", {})
        if mt.get("labels") and mt.get("values"):
            fig = make_line_chart(mt["labels"], mt["values"], "#2563eb", "Monthly Expense Trend")
            st.plotly_chart(fig, key="chart_monthly_trend")

        # Category + Top vendors
        an_col1, an_col2 = st.columns(2)
        with an_col1:
            cs = charts.get("category_spend", {})
            if cs.get("labels") and cs.get("values"):
                fig = make_bar_chart(cs["labels"], cs["values"], "#7c3aed", "Spend by Category")
                st.plotly_chart(fig, key="chart_cat_spend")

        with an_col2:
            tv = charts.get("top_vendors", {})
            if tv.get("labels") and tv.get("values"):
                fig = make_bar_chart(tv["labels"], tv["values"], "#10b981", "Top Vendors by Amount")
                st.plotly_chart(fig, key="chart_top_vendors")

        # Full export
        txns = results.get("suspicious_transactions", [])
        if txns:
            full_df = pd.DataFrame(txns)
            full_df["reasons"] = full_df["reasons"].apply(
                lambda x: "|".join(x) if isinstance(x, list) else str(x)
            )
            csv_data = full_df.to_csv(index=False)
            st.download_button(
                "⬇ Export Full Audit CSV",
                data=csv_data,
                file_name="full_audit_report.csv",
                mime="text/csv",
                key="dl_full_csv",
            )

    # ── TAB 5: GSTIN Validation (if data exists) ───────────────────────────────
    if gstin_data:
        with tab_gstin:
            valid_count = sum(1 for g in gstin_data if g["valid"])
            invalid_count = len(gstin_data) - valid_count

            st.markdown(f"""**{len(gstin_data)}** unique GSTINs auto-detected in your uploaded file""")

            # Summary badges
            g_cols = st.columns(3)
            with g_cols[0]:
                st.markdown(f'<span class="badge badge-cyan">Total: {len(gstin_data)}</span>', unsafe_allow_html=True)
            with g_cols[1]:
                st.markdown(f'<span class="badge badge-success">✅ Valid: {valid_count}</span>', unsafe_allow_html=True)
            with g_cols[2]:
                st.markdown(f'<span class="badge badge-danger">❌ Invalid: {invalid_count}</span>', unsafe_allow_html=True)

            st.markdown("")

            # Filters
            gstin_filter_col1, gstin_filter_col2 = st.columns([3, 1])
            with gstin_filter_col1:
                gstin_search = st.text_input("🔍 Search GSTIN, state, or PAN...", key="gstin_auto_search")
            with gstin_filter_col2:
                gstin_status = st.selectbox("Status", ["All", "Valid", "Invalid"], key="gstin_auto_filter")

            # Apply filters
            filtered_gstin = gstin_data
            if gstin_search:
                q = gstin_search.lower()
                filtered_gstin = [
                    g for g in filtered_gstin
                    if q in g["gstin"].lower() or q in g["state"].lower() or q in g["pan"].lower()
                ]
            if gstin_status == "Valid":
                filtered_gstin = [g for g in filtered_gstin if g["valid"]]
            elif gstin_status == "Invalid":
                filtered_gstin = [g for g in filtered_gstin if not g["valid"]]

            # Results table
            if filtered_gstin:
                g_table = pd.DataFrame([{
                    "Row": g["row"],
                    "GSTIN": g["gstin"],
                    "Status": "✅ Valid" if g["valid"] else "❌ Invalid",
                    "State Code": g["state_code"],
                    "State": g["state"],
                    "PAN": g["pan"],
                    "Details": g["message"],
                } for g in filtered_gstin])
                st.dataframe(g_table, hide_index=True, height=500)

                # Export
                csv_out = g_table.to_csv(index=False)
                st.download_button(
                    "⬇ Export GSTIN Validation CSV",
                    data=csv_out,
                    file_name="gstin_validation_results.csv",
                    mime="text/csv",
                    key="dl_gstin_csv",
                )

                # Detail cards for invalid GSTINs
                invalid_list = [g for g in filtered_gstin if not g["valid"]]
                if invalid_list:
                    st.markdown("### ⚠️ Invalid GSTINs — Action Required")
                    for g in invalid_list:
                        st.markdown(f"""
                        <div class="insight-card" style="border-left-color: #ef4444;">
                            <strong>Row {g['row']}</strong> — <code>{g['gstin']}</code><br>
                            <span style="color:#64748b;">{g['message']}</span>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No GSTINs match the current filter.")


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORY PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_history():
    st.markdown("""
    <div class="page-header">
        <h1>📜 Audit <span class="accent">History</span></h1>
        <p>All previous audit sessions saved to database</p>
    </div>
    """, unsafe_allow_html=True)

    if not MYSQL_AVAILABLE:
        st.warning("⚠️ MySQL not connected. History is only available when MySQL is running.")
        st.info("No audit sessions found. Upload a file from the Dashboard to get started.")
        return

    user = st.session_state.user or {}
    user_id = user.get("id", 1)

    try:
        history = get_cached_history(user_id, limit=30)
        stats = get_cached_stats(user_id)

        # Stats
        if stats and stats.get("total_audits"):
            s_cols = st.columns(4)
            kpis = [
                ("Total Audits", str(stats.get("total_audits", 0))),
                ("Transactions", f"{int(stats.get('total_txns', 0) or 0):,}"),
                ("Total Flagged", f"{int(stats.get('total_flagged', 0) or 0):,}"),
                ("Avg Flag Rate", f"{float(stats.get('avg_flag_rate', 0) or 0):.1f}%"),
            ]
            for col, (label, value) in zip(s_cols, kpis):
                with col:
                    st.metric(label=label, value=value)

        st.markdown("")

        if not history:
            st.info("No audit sessions found. Upload a file from the Dashboard to get started.")
            return

        # History table
        st.markdown("### Sessions")
        hist_data = []
        for h in history:
            hist_data.append({
                "ID": h.get("id"),
                "Date": str(h.get("upload_date", ""))[:16],
                "File": h.get("filename", ""),
                "Transactions": h.get("total_transactions", 0),
                "Flagged": h.get("total_flagged", 0),
                "Flag Rate": f"{float(h.get('flag_rate', 0)):.1f}%",
                "Duplicates": h.get("duplicate_invoices", 0),
                "Cash": h.get("cash_violations", 0),
                "AI Anomalies": h.get("ai_anomalies", 0),
                "Status": h.get("status", "completed"),
            })

        hist_df = pd.DataFrame(hist_data)
        st.dataframe(hist_df, hide_index=True, height=500)

        csv_data = hist_df.to_csv(index=False)
        st.download_button(
            "⬇ Export History CSV",
            data=csv_data,
            file_name="audit_history.csv",
            mime="text/csv",
            key="dl_history_csv",
        )

    except Exception as e:
        st.error(f"Error loading history: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
#  GSTIN VALIDATOR PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_gstin():
    st.markdown("""
    <div class="page-header">
        <h1>🔍 GSTIN <span class="accent">Validator</span></h1>
        <p>Validate Indian GST Numbers — Format check + State identification</p>
    </div>
    """, unsafe_allow_html=True)

    tab_single, tab_bulk = st.tabs(["Single Check", "Bulk Check"])

    # ── Single ─────────────────────────────────────────────────────────────────
    with tab_single:
        col_input, col_guide = st.columns([1, 1])

        with col_input:
            st.markdown("#### Enter GSTIN (15 characters)")
            gstin_input = st.text_input(
                "GSTIN",
                placeholder="e.g. 27AAPFU0939F1ZV",
                max_chars=15,
                key="gstin_single",
                label_visibility="collapsed",
            ).strip().upper()

            if st.button("✅ Validate", key="validate_single", type="primary"):
                if not gstin_input:
                    st.error("Please enter a GSTIN.")
                else:
                    result = validate_gstin_format(gstin_input)
                    if result["valid"]:
                        st.success("✅ **VALID GSTIN**")
                        r_cols = st.columns(2)
                        with r_cols[0]:
                            st.markdown(f"**GSTIN:** `{result['gstin']}`")
                            st.markdown(f"**State Code:** `{result['state_code']}`")
                        with r_cols[1]:
                            st.markdown(f"**State:** {result['state']}")
                            st.markdown(f"**PAN:** `{result['pan']}`")
                    else:
                        st.error(f"❌ **INVALID GSTIN** — {result['message']}")

        with col_guide:
            st.markdown("#### GSTIN Format Guide")
            guide_data = pd.DataFrame({
                "Position": ["1–2", "3–7", "8–11", "12", "13", "14", "15"],
                "Characters": ["Digits", "Letters", "Digits", "Letter", "1–9 or A–Z", "Z", "Digit/Letter"],
                "Description": [
                    "State Code (01–37)", "PAN first 5 characters", "PAN digits",
                    "PAN last character", "Entity number", "Always Z", "Checksum"
                ],
            })
            st.dataframe(guide_data, hide_index=True)
            st.caption("Example: **27AAPFU0939F1ZV** → Maharashtra")

    # ── Bulk ───────────────────────────────────────────────────────────────────
    with tab_bulk:
        st.markdown("#### Enter GSTINs (one per line)")
        bulk_input = st.text_area(
            "GSTINs",
            placeholder="27AAPFU0939F1ZV\n29ABCDE1234F1Z5\n33XYZAB5678G2ZK",
            height=200,
            key="gstin_bulk",
            label_visibility="collapsed",
        )

        if st.button("✅ Validate All", key="validate_bulk", type="primary"):
            lines = [line.strip().upper() for line in bulk_input.split("\n") if line.strip()]
            if not lines:
                st.error("Please enter at least one GSTIN.")
            else:
                results_list = validate_gstin_list(lines)
                valid_count = sum(1 for r in results_list if r["valid"])
                invalid_count = len(results_list) - valid_count

                # Stats badges
                stat_cols = st.columns(3)
                with stat_cols[0]:
                    st.markdown(f'<span class="badge badge-cyan">Total: {len(results_list)}</span>',
                                unsafe_allow_html=True)
                with stat_cols[1]:
                    st.markdown(f'<span class="badge badge-success">✅ Valid: {valid_count}</span>',
                                unsafe_allow_html=True)
                with stat_cols[2]:
                    st.markdown(f'<span class="badge badge-danger">❌ Invalid: {invalid_count}</span>',
                                unsafe_allow_html=True)

                # Results table
                bulk_data = []
                for i, r in enumerate(results_list):
                    bulk_data.append({
                        "GSTIN": lines[i],
                        "Status": "✅ Valid" if r["valid"] else "❌ Invalid",
                        "State": r.get("state", "—") or "—",
                        "Message": r.get("message", ""),
                    })

                bulk_df = pd.DataFrame(bulk_data)
                st.dataframe(bulk_df, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════

def page_home():
    # ── Hero Section ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-section">
        <div class="hero-badge">🛡️ AI-POWERED AUDIT PLATFORM</div>
        <h1 class="hero-title">
            Detect Financial Fraud<br>
            with <span class="accent">Artificial Intelligence</span>
        </h1>
        <p class="hero-subtitle">
            Audit Intelligence uses Isolation Forest machine learning and rule-based compliance
            checks to analyze financial transactions, flag anomalies, and score vendor risk
            — all from a single CSV upload.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # CTA buttons
    btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 2])
    with btn_col2:
        if st.button("🚀 Get Started", type="primary", key="home_cta"):
            st.session_state.show_home = False
            st.rerun()

    # ── Stats bar ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-value">4</div>
            <div class="stat-label">Compliance Rules</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">AI</div>
            <div class="stat-label">Anomaly Detection</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">100</div>
            <div class="stat-label">Vendor Risk Score</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">PDF</div>
            <div class="stat-label">Instant Reports</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Features Section ───────────────────────────────────────────────────────
    st.markdown("""
    <div class="home-section-title">Powerful Audit <span style="color:#2563eb">Features</span></div>
    <div class="home-section-sub">Everything you need to detect fraud, ensure compliance, and protect your organization.</div>
    """, unsafe_allow_html=True)

    features = [
        ("🤖", "Isolation Forest AI", "Machine learning model detects statistical anomalies in transaction amounts, frequencies, and patterns that rules alone would miss.", "glow-cyan"),
        ("📋", "4 Compliance Rules", "Duplicate invoices, daily cash limit (Section 40A), structured payments detection, and transaction-type validation.", "glow-purple"),
        ("🏢", "Vendor Risk Scoring", "Every vendor gets a 0-100 risk score combining compliance violations, duplicate history, and AI anomaly rates.", "glow-green"),
        ("🔍", "GSTIN Validator", "Validate Indian GST numbers with format checks, state identification, and PAN extraction — single or bulk.", "glow-warning"),
        ("📊", "Interactive Analytics", "Monthly trends, category spending, payment mode distribution, and top vendor charts with live filtering.", "glow-danger"),
        ("📄", "PDF & CSV Export", "Download professional audit reports as PDF, or export flagged transactions and vendor risk tables as CSV.", "glow-teal"),
    ]

    rows = [features[i:i+3] for i in range(0, len(features), 3)]
    for row in rows:
        cols = st.columns(3)
        for col, (icon, title, desc, glow) in zip(cols, row):
            with col:
                st.markdown(f"""
                <div class="glass-card {glow}">
                    <span class="glass-icon">{icon}</span>
                    <div class="glass-title">{title}</div>
                    <div class="glass-desc">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("")

    # ── How It Works ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="home-section-title">How It <span style="color:#2563eb">Works</span></div>
    <div class="home-section-sub">From upload to actionable insights in seconds.</div>
    """, unsafe_allow_html=True)

    steps = [
        ("1", "Upload Your Data", "Upload a CSV or Excel file containing your financial transactions. We accept common formats with columns like Date, Invoice, Vendor, Amount, and Payment Mode."),
        ("2", "AI Analysis Runs", "The Isolation Forest ML model processes every transaction alongside 4 compliance rule checks. Duplicate invoices, cash limit violations, and structured payment patterns are identified."),
        ("3", "Review Flagged Items", "Explore flagged transactions with detailed reasons, suggested corrected amounts, and vendor-level risk scores. Filter, search, and sort interactively."),
        ("4", "Export Reports", "Download a comprehensive PDF report or export detailed CSV data for each section. Share findings with your audit team instantly."),
    ]

    step_col1, step_col2 = st.columns(2)
    for i, (num, title, desc) in enumerate(steps):
        with step_col1 if i % 2 == 0 else step_col2:
            st.markdown(f"""
            <div class="step-card">
                <div class="step-num">{num}</div>
                <div class="step-body">
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    # ── Tech Stack ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="home-section-title">Built With <span style="color:#2563eb">Modern Tech</span></div>
    <div class="home-section-sub">Production-grade open-source stack.</div>
    <div style="text-align:center; margin-bottom:30px;">
        <span class="tech-pill"><span class="pill-icon">🐍</span> Python</span>
        <span class="tech-pill"><span class="pill-icon">🎯</span> Streamlit</span>
        <span class="tech-pill"><span class="pill-icon">🧠</span> Scikit-Learn</span>
        <span class="tech-pill"><span class="pill-icon">📊</span> Plotly</span>
        <span class="tech-pill"><span class="pill-icon">🐬</span> MySQL</span>
        <span class="tech-pill"><span class="pill-icon">🐼</span> Pandas</span>
        <span class="tech-pill"><span class="pill-icon">📄</span> FPDF2</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Bottom CTA ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cta-banner">
        <h2>Ready to Audit <span style="color:#2563eb">Smarter?</span></h2>
        <p>Sign in to upload your first file and discover AI-powered insights.</p>
    </div>
    """, unsafe_allow_html=True)

    cta_col1, cta_col2, cta_col3 = st.columns([2, 1, 2])
    with cta_col2:
        if st.button("Sign In →", type="primary", key="home_signin"):
            st.session_state.show_home = False
            st.rerun()

    # Footer
    st.markdown("""
    <div class="footer">
        Medi-Caps University · Jay Solanki & Jaydeep Patidar · B.Tech CSE 2023-27<br>
        <span style="font-size:10px; color:#94a3b8;">Audit Intelligence v3.0 · Streamlit Edition</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Home page first (before login)
    if st.session_state.show_home and not st.session_state.logged_in:
        page_home()
        return

    if not st.session_state.logged_in:
        page_login()
        return

    # Render sidebar for logged-in users
    render_sidebar()

    # Route to the selected page
    page = st.session_state.current_page
    if page == "Dashboard":
        page_dashboard()
    elif page == "History":
        page_history()
    elif page == "GSTIN":
        page_gstin()
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
