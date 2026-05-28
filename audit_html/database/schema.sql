-- -----------------------------------------------------------------------------
-- PostgreSQL Schema for Audit Intelligence (Supabase Compatible)
-- -----------------------------------------------------------------------------

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'auditor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 2. Audit Sessions Table
CREATE TABLE IF NOT EXISTS audit_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_transactions INTEGER,
    total_flagged INTEGER,
    total_amount NUMERIC(15,2),
    flag_rate NUMERIC(5,2),
    duplicate_invoices INTEGER,
    cash_violations INTEGER,
    structured_payments INTEGER,
    ai_anomalies INTEGER,
    high_risk_vendors INTEGER
);

-- 3. Flagged Transactions Table
CREATE TABLE IF NOT EXISTS flagged_transactions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES audit_sessions(id) ON DELETE CASCADE,
    txn_row INTEGER,
    txn_date VARCHAR(50),
    invoice_number VARCHAR(100),
    vendor_name VARCHAR(255),
    amount NUMERIC(15,2),
    payment_mode VARCHAR(50),
    category VARCHAR(100),
    anomaly_score NUMERIC(5,2),
    flag_duplicate_invoice BOOLEAN DEFAULT FALSE,
    flag_same_amount_date BOOLEAN DEFAULT FALSE,
    flag_cash_limit BOOLEAN DEFAULT FALSE,
    flag_structured BOOLEAN DEFAULT FALSE,
    flag_anomaly BOOLEAN DEFAULT FALSE
);

-- 4. Vendor Risk Table
CREATE TABLE IF NOT EXISTS vendor_risk (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES audit_sessions(id) ON DELETE CASCADE,
    vendor_name VARCHAR(255),
    total_transactions INTEGER,
    total_amount NUMERIC(15,2),
    flagged_transactions INTEGER,
    compliance_score NUMERIC(5,2),
    duplicate_score NUMERIC(5,2),
    anomaly_score NUMERIC(5,2),
    risk_score NUMERIC(5,2),
    risk_level VARCHAR(20)
);
