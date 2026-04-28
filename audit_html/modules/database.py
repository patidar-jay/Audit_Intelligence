"""
database.py - MySQL Database Module
"""
import hashlib
import os
from datetime import datetime

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "audit_intelligence"),
}


def get_connection():
    if not MYSQL_AVAILABLE:
        raise RuntimeError("mysql-connector-python not installed.")
    return mysql.connector.connect(**DB_CONFIG)


def init_database():
    if not MYSQL_AVAILABLE:
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchall()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB connection error:", e)
        return False


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def create_user(username, email, password, full_name="", role="auditor"):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (%s,%s,%s,%s,%s)",
            (username, email, hash_password(password), full_name, role)
        )
        conn.commit()
        cur.close(); conn.close()
        return True, "Account created successfully!"
    except Exception as e:
        err = str(e)
        if "Duplicate" in err and "username" in err:
            return False, "Username already taken. Choose another."
        if "Duplicate" in err and "email" in err:
            return False, "Email already registered. Try logging in."
        return False, err


def login_user(username, password):
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if not user:
            return None, "Username not found."
        if not verify_password(password, user["password_hash"]):
            return None, "Incorrect password."
        # Update last login
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user["id"],))
        conn.commit()
        cur.close(); conn.close()
        return user, "Login successful!"
    except Exception as e:
        return None, "Database error: " + str(e)


def save_audit_session(user_id, filename, results):
    try:
        s    = results["summary"]
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO audit_sessions
            (user_id, filename, total_transactions, total_flagged, total_amount,
             flag_rate, duplicate_invoices, cash_violations, structured_payments,
             ai_anomalies, high_risk_vendors)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM audit_sessions
            WHERE user_id=%s ORDER BY upload_date DESC LIMIT %s
        """, (user_id, limit))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except:
        return []


def get_dashboard_stats(user_id):
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT COUNT(*) as total_audits,
                   SUM(total_transactions) as total_txns,
                   SUM(total_flagged) as total_flagged,
                   AVG(flag_rate) as avg_flag_rate,
                   MAX(upload_date) as last_audit
            FROM audit_sessions WHERE user_id=%s
        """, (user_id,))
        stats = cur.fetchone()
        cur.close(); conn.close()
        return stats
    except:
        return None
