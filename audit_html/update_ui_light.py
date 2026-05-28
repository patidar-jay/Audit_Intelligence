import re

with open('audit_html/streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_css = """
<style>
/* ── Font applied ────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

/* ── Root vars (Light Premium) ────────────────────────────── */
:root {
    --primary:   #ffffff;
    --primary-gradient: linear-gradient(135deg, #0f172a, #334155);
    --accent:    #2563eb;
    --accent-gradient: linear-gradient(135deg, #2563eb, #8b5cf6);
    --card-bg:   rgba(255, 255, 255, 0.95);
    --card-hover: #ffffff;
    --text:      #0f172a;
    --muted:     #64748b;
    --border:    #e2e8f0;
}

/* ── Animations ──────────────────────────────────────────── */
@keyframes fadeInUp {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-5px); }
    100% { transform: translateY(0px); }
}
@keyframes slideInRight {
    0% { opacity: 0; transform: translateX(20px); }
    100% { opacity: 1; transform: translateX(0); }
}

/* ── Global ──────────────────────────────────────────────── */
* {
    cursor: url("data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' cy='12' r='5' fill='%230f172a' stroke='%23ffffff' stroke-width='2'/%3E%3C/svg%3E") 12 12, auto;
}
a, button, [role="button"], .stButton > button, section[data-testid="stSidebar"] .stButton > button, section[data-testid="stFileUploader"] {
    cursor: url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='16' cy='16' r='6' fill='%232563eb' stroke='%23ffffff' stroke-width='2'/%3E%3Ccircle cx='16' cy='16' r='14' stroke='%232563eb' stroke-width='1.5' stroke-dasharray='4 4' opacity='0.7'/%3E%3C/svg%3E") 16 16, pointer !important;
}

.stApp {
    font-family: 'Outfit', sans-serif;
    background: #f8fafc !important; /* Soft light background */
    color: var(--text);
}
.block-container { padding-top: 1.5rem !important; }
h1, h2, h3, h4, h5, h6 { font-family: 'Outfit', sans-serif; letter-spacing: -0.02em; color: #0f172a !important; }
p, span, div, label { color: var(--text); }

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border);
    box-shadow: 2px 0 20px rgba(0,0,0,0.03);
}
section[data-testid="stSidebar"] * {
    font-family: 'Outfit', sans-serif;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #0f172a !important;
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    text-align: left;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #64748b !important;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 600;
    transition: all 0.25s;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #f1f5f9 !important;
    color: #2563eb !important;
    transform: translateX(4px);
    border: 1px solid #e2e8f0 !important;
}

/* ── Upload zone ─────────────────────────────────────────── */
section[data-testid="stFileUploader"] {
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    background: #f8fafc;
    transition: all 0.3s ease;
    padding: 16px;
}
section[data-testid="stFileUploader"]:hover {
    border-color: #2563eb;
    background: #eff6ff;
}
section[data-testid="stFileUploader"] small {
    color: #64748b !important;
}
section[data-testid="stFileUploader"] button {
    background: #ffffff !important;
    color: #2563eb !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
section[data-testid="stFileUploader"] button:hover {
    border-color: #2563eb !important;
    background: #eff6ff !important;
}

/* ── CARD component (Light Mode) ──────────────────────────── */
.card {
    background: var(--card-bg);
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 20px;
    border: 1px solid var(--border);
    box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    animation: fadeInUp 0.6s ease forwards;
}

/* ── KPI metric cards ────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px 24px;
    border-left: 4px solid #2563eb; /* Blue border */
    box-shadow: 0 4px 20px rgba(0,0,0,0.02);
    transition: all 0.3s ease;
    animation: fadeInUp 0.6s ease forwards;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    background: var(--card-hover);
    border-left-color: #8b5cf6;
    box-shadow: 0 8px 30px rgba(0,0,0,0.06);
}
div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 12px !important;
    text-transform: uppercase;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 900 !important;
    font-size: 32px !important;
}

/* ── Tabs styling ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid var(--border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    color: #64748b;
    font-weight: 600;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0f172a;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

/* ── Data tables ─────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid var(--border);
    border-radius: 16px;
    background: #ffffff;
    box-shadow: 0 4px 15px rgba(0,0,0,0.02);
}
.stDataFrame [data-testid="stTable"] * {
    color: #334155 !important;
}
.stDataFrame [data-testid="stTable"] th {
    background: #f8fafc !important;
    color: #0f172a !important;
}

/* ── Buttons (Fixed contrast for light mode) ─────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--accent-gradient) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 12px 28px !important;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(37, 99, 235, 0.3) !important;
}
/* Secondary buttons - Light Theme Fix */
.stButton > button {
    background: #f8fafc !important; /* light gray background */
    color: #334155 !important;
    border: 1px solid #cbd5e1 !important; /* visible border */
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.3s;
}
.stButton > button:hover {
    background: #ffffff !important;
    border-color: #2563eb !important;
    color: #2563eb !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
}

/* ── Inputs ──────────────────────────────────────────────── */
.stTextInput input, .stNumberInput input {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #0f172a !important;
    border-radius: 8px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 8px rgba(37, 99, 235, 0.2) !important;
}

/* ── Insight cards ───────────────────────────────────────── */
.insight-card {
    border-left: 4px solid #8b5cf6;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 0 16px 16px 0;
    padding: 18px 22px;
    margin-bottom: 14px;
    color: #334155;
    box-shadow: 0 4px 15px rgba(0,0,0,0.02);
}

/* ── Badges ──────────────────────────────────────────────── */
.badge {
    padding: 6px 14px;
    border-radius: 24px;
    font-size: 12px;
    font-weight: 700;
    margin: 2px 4px;
    text-transform: uppercase;
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
}
.badge-danger  { color: #dc2626; border-color: #fca5a5; background: #fef2f2; }
.badge-warning { color: #d97706; border-color: #fcd34d; background: #fffbeb; }
.badge-success { color: #059669; border-color: #6ee7b7; background: #ecfdf5; }

/* ── Page header ─────────────────────────────────────────── */
.page-header {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 32px 36px;
    margin-bottom: 32px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.03);
    animation: fadeInUp 0.6s ease forwards;
}
.page-header h1 { 
    font-size: 32px; 
    font-weight: 900; 
    margin: 0;
    color: #0f172a;
}
.page-header .accent { 
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.page-header p { color: #64748b; font-size: 15px; margin: 8px 0 0 0; }

/* ── Login box ───────────────────────────────────────────── */
.login-box {
    max-width: 480px;
    margin: 60px auto;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 44px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.06);
    animation: fadeInUp 0.8s ease forwards;
}
.login-logo { text-align: center; margin-bottom: 36px; }
.login-logo .icon { font-size: 56px; animation: float 4s ease-in-out infinite; display: inline-block; }
.login-logo h1 { font-size: 32px; font-weight: 900; color: #0f172a; }
.login-logo .accent { background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.login-logo p { color: #64748b; }

/* ── Feature cards grid ──────────────────────────────────── */
.feature-grid { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-top: 24px; }
.feature-card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 24px 28px;
    text-align: center;
    min-width: 170px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.02);
    transition: all 0.3s;
}
.feature-card:hover {
    transform: translateY(-6px);
    border-color: #2563eb;
    box-shadow: 0 12px 30px rgba(37,99,235,0.1);
}
.feature-card .feat-icon { font-size: 36px; margin-bottom: 12px; }
.feature-card .feat-title { font-weight: 800; color: #0f172a; font-size: 16px;}
.feature-card .feat-sub { color: #64748b; font-size: 13px; margin-top: 4px; }

/* ── Footer ──────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #64748b;
    font-size: 13px;
    margin-top: 60px;
    padding: 24px;
    border-top: 1px solid var(--border);
}

/* ══════════════════════════════════════════════════════════ */
/*  HOME PAGE STYLES                                         */
/* ══════════════════════════════════════════════════════════ */
.hero-section { text-align: center; padding: 80px 20px 60px; position: relative; }
.hero-section::before {
    content: ''; position: absolute; top: -60px; left: 50%; transform: translateX(-50%);
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(37,99,235,0.06) 0%, transparent 60%);
    border-radius: 50%; pointer-events: none; z-index: 0;
}
.hero-badge {
    display: inline-block; padding: 10px 24px; border-radius: 30px;
    font-size: 13px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;
    background: #eff6ff; border: 1px solid #bfdbfe;
    color: #2563eb; margin-bottom: 28px;
}
.hero-title {
    font-size: 56px; font-weight: 900; line-height: 1.1; color: #0f172a; margin: 0 0 20px 0;
}
.hero-title .accent {
    background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-subtitle { font-size: 20px; color: #64748b; max-width: 680px; margin: 0 auto 40px; }
.stats-bar {
    display: flex; justify-content: center; gap: 56px; flex-wrap: wrap;
    padding: 40px 0; margin: 40px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
}
.stat-item { text-align: center; min-width: 130px; }
.stat-value {
    font-size: 42px; font-weight: 900; color: #0f172a;
    background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.stat-label { font-size: 13px; color: #64748b; text-transform: uppercase; font-weight: 700; margin-top: 8px; }
.home-section-title { text-align: center; font-size: 38px; font-weight: 900; color: #0f172a; margin: 64px 0 12px; }
.home-section-sub { text-align: center; font-size: 16px; color: #64748b; margin-bottom: 48px; max-width: 580px; margin: 0 auto 48px; }
.glass-card {
    background: #ffffff; border: 1px solid var(--border);
    border-radius: 24px; padding: 36px 28px; text-align: center;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.02);
}
.glass-card:hover {
    transform: translateY(-8px); border-color: #2563eb;
    box-shadow: 0 12px 30px rgba(37,99,235,0.08);
}
</style>
"""

# Update CSS
pattern = re.compile(r'<style>.*?</style>', re.DOTALL)
new_content = pattern.sub(new_css, content)

# Update CHART_LAYOUT for Light mode
chart_pattern = re.compile(r'CHART_LAYOUT = dict\(.*?\)', re.DOTALL)
light_chart = """CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#0f172a", family="Outfit, sans-serif", size=13),
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis=dict(showgrid=False, zeroline=False, linecolor="#e2e8f0", tickfont=dict(color="#64748b")),
    yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False, linecolor="#e2e8f0", tickfont=dict(color="#64748b")),
    hoverlabel=dict(bgcolor="#ffffff", font_size=14, font_family="Outfit, sans-serif", bordercolor="#cbd5e1"),
)"""
new_content = chart_pattern.sub(light_chart, new_content)

with open('audit_html/streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
