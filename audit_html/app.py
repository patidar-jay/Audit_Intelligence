"""
app.py - FastAPI Backend
Audit Intelligence - HTML/CSS/JS Frontend Version
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import tempfile, os, io, uuid
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from modules.audit_engine   import AuditEngine
from modules.database       import (login_user, create_user, save_audit_session,
                                     get_audit_history, get_dashboard_stats,
                                     init_database, MYSQL_AVAILABLE)
from modules.gstin_validator import validate_gstin_format, validate_gstin_list

app = FastAPI(title="Audit Intelligence", version="3.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    if MYSQL_AVAILABLE:
        init_database()


# ── Pages ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/gstin", response_class=HTMLResponse)
async def gstin_page(request: Request):
    return templates.TemplateResponse("gstin.html", {"request": request})


# ── Auth API ───────────────────────────────────────────────────────────────────
@app.post("/api/login")
async def api_login(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        raise HTTPException(400, "Username and password required.")
    if not MYSQL_AVAILABLE:
        # Demo mode
        return {"success": True, "user": {"id": 1, "username": username,
                "full_name": username.title(), "email": "demo@example.com",
                "role": "auditor"}, "demo": True}
    user, msg = login_user(username, password)
    if not user:
        raise HTTPException(401, msg)
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    # Convert datetime to string
    for k, v in safe.items():
        if hasattr(v, 'isoformat'):
            safe[k] = str(v)
    return {"success": True, "user": safe}


@app.post("/api/register")
async def api_register(data: dict):
    username  = data.get("username", "").strip()
    email     = data.get("email", "").strip()
    password  = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    if not all([username, email, password, full_name]):
        raise HTTPException(400, "All fields are required.")
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters.")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address.")
    if not MYSQL_AVAILABLE:
        raise HTTPException(503, "Database not connected. Use Demo Login.")
    ok, msg = create_user(username, email, password, full_name)
    if not ok:
        raise HTTPException(400, msg)
    return {"success": True, "message": msg}


# ── Audit API ──────────────────────────────────────────────────────────────────
@app.post("/api/audit")
async def run_audit(file: UploadFile = File(...), user_id: int = 1):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(400, f"Only CSV and Excel files supported.")
    tmp_path = None
    try:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "File too large. Max 20MB.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content); tmp_path = tmp.name
        engine  = AuditEngine(tmp_path)
        results = engine.run_full_audit()
        if MYSQL_AVAILABLE:
            save_audit_session(user_id, file.filename, results)
        return {"success": True, "filename": file.filename, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Audit failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/api/sample-data")
def sample_data():
    np.random.seed(42); n = 200
    vendors    = ["Tech Supplies","Office Depot","Apex Solutions","Global Traders",
                  "Swift Logistics","Alpha Corp","Beta Services","Gamma Ltd"]
    categories = ["IT Equipment","Office Supplies","Travel","Consulting",
                  "Marketing","Utilities","Maintenance","Software"]
    from datetime import timedelta
    dates = [datetime(2024,1,1)+timedelta(days=int(x)) for x in np.random.randint(0,365,n)]
    df = pd.DataFrame({
        "Date":           [d.strftime("%Y-%m-%d") for d in dates],
        "Invoice_Number": [f"INV-{1000+i}" for i in range(n)],
        "Vendor_Name":    np.random.choice(vendors, n),
        "Amount":         np.random.lognormal(9,1.5,n).round(2),
        "Payment_Mode":   np.random.choice(["Bank","UPI","Cash"], n, p=[0.6,0.25,0.15]),
        "Category":       np.random.choice(categories, n),
        "Txn_Type":       np.random.choice(["Debit","Debit","Debit","Credit"], n),
    })
    df.loc[10,"Invoice_Number"] = df.loc[5,"Invoice_Number"]
    df.loc[11,"Invoice_Number"] = df.loc[5,"Invoice_Number"]
    df.loc[20,["Amount","Payment_Mode","Date","Vendor_Name"]] = [6000,"Cash","2024-03-15","Alpha Corp"]
    df.loc[21,["Amount","Payment_Mode","Date","Vendor_Name"]] = [5500,"Cash","2024-03-15","Alpha Corp"]
    df.loc[30,"Amount"] = 850000
    df.loc[40,["Amount","Payment_Mode"]] = [9500,"Cash"]
    df.loc[41,["Amount","Payment_Mode"]] = [9600,"Cash"]
    buf = io.StringIO(); df.to_csv(buf, index=False); buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_transactions.csv"})


# ── History API ────────────────────────────────────────────────────────────────
@app.get("/api/history/{user_id}")
def get_history(user_id: int):
    if not MYSQL_AVAILABLE:
        return {"history": [], "stats": None, "demo": True}
    history = get_audit_history(user_id, limit=30)
    stats   = get_dashboard_stats(user_id)
    # Serialize datetimes
    for h in history:
        for k, v in h.items():
            if hasattr(v, 'isoformat'): h[k] = str(v)
    if stats:
        for k, v in stats.items():
            if hasattr(v, 'isoformat'): stats[k] = str(v)
    return {"history": history, "stats": stats}


# ── GSTIN API ──────────────────────────────────────────────────────────────────
@app.post("/api/gstin/validate")
async def gstin_validate(data: dict):
    gstin = data.get("gstin", "").strip().upper()
    return validate_gstin_format(gstin)


@app.post("/api/gstin/bulk")
async def gstin_bulk(data: dict):
    gstins = [g.strip().upper() for g in data.get("gstins", []) if g.strip()]
    return {"results": validate_gstin_list(gstins)}


@app.get("/health")
def health():
    return {"status": "online", "mysql": MYSQL_AVAILABLE, "version": "3.0.0"}
