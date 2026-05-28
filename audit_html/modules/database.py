"""
database.py - SQLite Database Module (Auto-creates local DB)
"""
import sqlite3
import hashlib
import os
from datetime import datetime

DB_AVAILABLE = True
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit_history.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Create users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'auditor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create audit_sessions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS audit_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_transactions INTEGER,
                total_flagged INTEGER,
                total_amount REAL,
                flag_rate REAL,
                duplicate_invoices INTEGER,
                cash_violations INTEGER,
                structured_payments INTEGER,
                ai_anomalies INTEGER,
                high_risk_vendors INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Create flagged_transactions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS flagged_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                txn_row INTEGER,
                txn_date TEXT,
                invoice_number TEXT,
                vendor_name TEXT,
                amount REAL,
                payment_mode TEXT,
                category TEXT,
                anomaly_score REAL,
                flag_duplicate_invoice BOOLEAN,
                flag_same_amount_date BOOLEAN,
                flag_cash_limit BOOLEAN,
                flag_structured BOOLEAN,
                flag_anomaly BOOLEAN,
                FOREIGN KEY(session_id) REFERENCES audit_sessions(id)
            )
        ''')
        
        # Create vendor_risk table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vendor_risk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                vendor_name TEXT,
                total_transactions INTEGER,
                total_amount REAL,
                flagged_transactions INTEGER,
                compliance_score REAL,
                duplicate_score REAL,
                anomaly_score REAL,
                risk_score REAL,
                risk_level TEXT,
                FOREIGN KEY(session_id) REFERENCES audit_sessions(id)
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB init error:", e)
        return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def create_user(username, email, password, full_name="", role="auditor"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?,?,?,?,?)",
            (username, email, hash_password(password), full_name, role)
        )
        conn.commit()
        cur.close(); conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        err = str(e).lower()
        if "username" in err:
            return False, "Username already taken. Choose another."
        if "email" in err:
            return False, "Email already registered. Try logging in."
        return False, str(e)
    except Exception as e:
        return False, str(e)

def login_user(username, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        
        if not row:
            cur.close(); conn.close()
            return None, "Username not found."
            
        user = dict(row)
        if not verify_password(password, user["password_hash"]):
            cur.close(); conn.close()
            return None, "Incorrect password."
            
        # Update last login
        cur.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user["id"],))
        conn.commit()
        cur.close(); conn.close()
        return user, "Login successful!"
    except Exception as e:
        return None, "Database error: " + str(e)

def save_audit_session(user_id, filename, results):
    try:
        s = results["summary"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_sessions
            (user_id, filename, total_transactions, total_flagged, total_amount,
             flag_rate, duplicate_invoices, cash_violations, structured_payments,
             ai_anomalies, high_risk_vendors)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user_id, filename,
            s["total_transactions"], s["total_flagged"], s["total_amount"],
            s["flag_rate"], s["duplicate_invoices"], s["cash_violations"],
            s["structured_payments"], s["ai_anomalies"], s["high_risk_vendors"]
        ))
        session_id = cur.lastrowid

        for t in results["suspicious_transactions"]:
            reasons = t["reasons"]
            cur.execute("""
                INSERT INTO flagged_transactions
                (session_id, txn_row, txn_date, invoice_number, vendor_name,
                 amount, payment_mode, category, anomaly_score,
                 flag_duplicate_invoice, flag_same_amount_date,
                 flag_cash_limit, flag_structured, flag_anomaly)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id, t["row"], t["date"], t["invoice"], t["vendor"],
                t["amount"], t["mode"], t["category"], t["anomaly_score"],
                "Duplicate Invoice" in reasons, False,
                "Cash Limit Breach" in reasons,
                "Structured Payment" in reasons,
                "AI Anomaly" in reasons
            ))

        for v in results["vendor_risk"]:
            cur.execute("""
                INSERT INTO vendor_risk
                (session_id, vendor_name, total_transactions, total_amount,
                 flagged_transactions, compliance_score, duplicate_score,
                 anomaly_score, risk_score, risk_level)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id, v["Vendor_Name"], v["Total_Transactions"],
                v["Total_Amount"], v["Flagged_Transactions"],
                v["Compliance_Score"], v["Duplicate_Score"],
                v["Anomaly_Score"], v["Risk_Score"], v["Risk_Level"]
            ))

        conn.commit()
        cur.close(); conn.close()
        return session_id
    except Exception as e:
        print("Save session error:", e)
        return None

def get_audit_history(user_id, limit=20):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM audit_sessions
            WHERE user_id=? ORDER BY upload_date DESC LIMIT ?
        """, (user_id, limit))
        rows = [dict(row) for row in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print("get_audit_history error:", e)
        return []

def get_dashboard_stats(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total_audits,
                   SUM(total_transactions) as total_txns,
                   SUM(total_flagged) as total_flagged,
                   AVG(flag_rate) as avg_flag_rate,
                   MAX(upload_date) as last_audit
            FROM audit_sessions WHERE user_id=?
        """, (user_id,))
        row = cur.fetchone()
        stats = dict(row) if row else None
        cur.close(); conn.close()
        return stats
    except Exception as e:
        print("get_dashboard_stats error:", e)
        return None
