"""
database.py - Hybrid Database Module (Postgres + SQLite Fallback)
"""
import hashlib
import os
import sqlite3
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

CURRENT_DB_TYPE = "sqlite"

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_connection():
    global CURRENT_DB_TYPE
    if DB_AVAILABLE:
        try:
            import streamlit as st
            if "SUPABASE_URL" in st.secrets:
                conn = psycopg2.connect(st.secrets["SUPABASE_URL"])
                CURRENT_DB_TYPE = "postgres"
                return conn
                
            if "mysql" in st.secrets:
                db_cfg = {
                    "host":     st.secrets["mysql"]["host"],
                    "port":     int(st.secrets["mysql"].get("port", 3306)),
                    "user":     st.secrets["mysql"]["user"],
                    "password": st.secrets["mysql"]["password"],
                    "database": st.secrets["mysql"]["database"],
                }
                conn = psycopg2.connect(**db_cfg)
                CURRENT_DB_TYPE = "postgres"
                return conn
                
            db_url = os.getenv("SUPABASE_URL")
            if db_url:
                conn = psycopg2.connect(db_url)
                CURRENT_DB_TYPE = "postgres"
                return conn
        except Exception as e:
            print("Postgres connection failed, falling back to SQLite:", e)
            pass

    # Fallback to local SQLite
    CURRENT_DB_TYPE = "sqlite"
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit_history.db")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = dict_factory
    return conn


def init_database():
    try:
        conn = get_connection()
        if CURRENT_DB_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return True
            
        # SQLite Initialization
        cur = conn.cursor()
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

def execute_query(conn, sql, params=(), return_id=False):
    """Compatibility wrapper for Postgres vs SQLite"""
    cur = None
    if CURRENT_DB_TYPE == "postgres":
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if return_id and "RETURNING id" not in sql:
            sql += " RETURNING id"
        cur.execute(sql, params)
        if return_id:
            row = cur.fetchone()
            # Depending on if RealDictCursor was used
            return row["id"] if isinstance(row, dict) else row[0], cur
        return None, cur
    else:
        # SQLite
        sql = sql.replace("%s", "?")
        sql = sql.replace("RETURNING id", "")
        cur = conn.cursor()
        cur.execute(sql, params)
        if return_id:
            return cur.lastrowid, cur
        return None, cur

def create_user(username, email, password, full_name="", role="auditor"):
    try:
        conn = get_connection()
        sql = "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (%s,%s,%s,%s,%s)"
        _, cur = execute_query(conn, sql, (username, email, hash_password(password), full_name, role))
        conn.commit()
        cur.close(); conn.close()
        return True, "Account created successfully!"
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err and "username" in err or "unique" in err and "username" in err:
            return False, "Username already taken. Choose another."
        if "duplicate" in err and "email" in err or "unique" in err and "email" in err:
            return False, "Email already registered. Try logging in."
        return False, str(e)


def login_user(username, password):
    try:
        conn = get_connection()
        _, cur = execute_query(conn, "SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        if not user:
            conn.close()
            return None, "Username not found."
            
        user = dict(user) # ensure it's a dict
        if not verify_password(password, user["password_hash"]):
            conn.close()
            return None, "Incorrect password."
            
        # Update last login
        if CURRENT_DB_TYPE == "postgres":
            sql = "UPDATE users SET last_login=NOW() WHERE id=%s"
        else:
            sql = "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=%s"
            
        _, cur = execute_query(conn, sql, (user["id"],))
        conn.commit()
        cur.close(); conn.close()
        return user, "Login successful!"
    except Exception as e:
        return None, "Database error: " + str(e)


def save_audit_session(user_id, filename, results):
    try:
        s = results["summary"]
        conn = get_connection()
        
        sql = """
            INSERT INTO audit_sessions
            (user_id, filename, total_transactions, total_flagged, total_amount,
             flag_rate, duplicate_invoices, cash_violations, structured_payments,
             ai_anomalies, high_risk_vendors)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        session_id, cur = execute_query(conn, sql, (
            user_id, filename,
            s["total_transactions"], s["total_flagged"], s["total_amount"],
            s["flag_rate"], s["duplicate_invoices"], s["cash_violations"],
            s["structured_payments"], s["ai_anomalies"], s["high_risk_vendors"]
        ), return_id=True)

        for t in results["suspicious_transactions"]:
            reasons = t["reasons"]
            sql_flag = """
                INSERT INTO flagged_transactions
                (session_id, txn_row, txn_date, invoice_number, vendor_name,
                 amount, payment_mode, category, anomaly_score,
                 flag_duplicate_invoice, flag_same_amount_date,
                 flag_cash_limit, flag_structured, flag_anomaly)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            execute_query(conn, sql_flag, (
                session_id, t["row"], t["date"], t["invoice"], t["vendor"],
                t["amount"], t["mode"], t["category"], t["anomaly_score"],
                "Duplicate Invoice" in reasons, False,
                "Cash Limit Breach" in reasons,
                "Structured Payment" in reasons,
                "AI Anomaly" in reasons
            ))

        for v in results["vendor_risk"]:
            sql_vendor = """
                INSERT INTO vendor_risk
                (session_id, vendor_name, total_transactions, total_amount,
                 flagged_transactions, compliance_score, duplicate_score,
                 anomaly_score, risk_score, risk_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            execute_query(conn, sql_vendor, (
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
        _, cur = execute_query(conn, """
            SELECT * FROM audit_sessions
            WHERE user_id=%s ORDER BY upload_date DESC LIMIT %s
        """, (user_id, limit))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        print("History error:", e)
        return []


def get_dashboard_stats(user_id):
    try:
        conn = get_connection()
        _, cur = execute_query(conn, """
            SELECT COUNT(*) as total_audits,
                   SUM(total_transactions) as total_txns,
                   SUM(total_flagged) as total_flagged,
                   AVG(flag_rate) as avg_flag_rate,
                   MAX(upload_date) as last_audit
            FROM audit_sessions WHERE user_id=%s
        """, (user_id,))
        stats = cur.fetchone()
        cur.close(); conn.close()
        return dict(stats) if stats else None
    except Exception as e:
        print("Stats error:", e)
        return None
