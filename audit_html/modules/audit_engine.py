"""
audit_engine.py - Core AI Audit Engine
Fixes applied:
1. Duplicate invoice - skip if one is credit and other is debit (return/cancel)
2. Removed same amount+date rule
3. Cash limit - sum all cash per vendor per day, flag if total > 10000
4. AI anomaly - replace outlier value with average, dont just flag
"""

import pandas as pd
import numpy as np
from datetime import datetime


class AuditEngine:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_and_preprocess(self):
        # Load file
        if self.file_path.endswith(".csv"):
            self.df = pd.read_csv(self.file_path)
        else:
            self.df = pd.read_excel(self.file_path)

        # Normalize column names
        self.df.columns = [c.strip().replace(" ", "_").title() for c in self.df.columns]

        # Map common column name variations
        col_map = {}
        for col in self.df.columns:
            low = col.lower()
            if "date" in low:                           col_map[col] = "Date"
            elif "invoice" in low:                      col_map[col] = "Invoice_Number"
            elif "vendor" in low or "supplier" in low:  col_map[col] = "Vendor_Name"
            elif "amount" in low or "value" in low:     col_map[col] = "Amount"
            elif "payment_mode" in low or low == "mode":   col_map[col] = "Payment_Mode"
            elif "category" in low:                        col_map[col] = "Category"
            elif "txn_type" in low or low == "txn_type":   col_map[col] = "Txn_Type"
        self.df.rename(columns=col_map, inplace=True)

        # Ensure required columns exist
        required = ["Date", "Invoice_Number", "Vendor_Name", "Amount", "Payment_Mode", "Category"]
        for col in required:
            if col not in self.df.columns:
                self.df[col] = "Unknown" if col != "Amount" else 0

        # If Txn_Type not present, default to Debit
        if "Txn_Type" not in self.df.columns:
            self.df["Txn_Type"] = "Debit"

        # Clean data
        self.df.dropna(subset=["Amount"], inplace=True)
        self.df["Amount"] = (
            self.df["Amount"].astype(str)
            .str.replace("[^0-9.]", "", regex=True)
            .replace("", "0")
            .astype(float)
        )
        self.df = self.df[self.df["Amount"] > 0].copy()
        self.df["Date"] = pd.to_datetime(self.df["Date"], errors="coerce", dayfirst=False)
        self.df.dropna(subset=["Date"], inplace=True)
        self.df["Vendor_Name"] = self.df["Vendor_Name"].astype(str).str.strip().str.title()
        self.df["Payment_Mode"] = self.df["Payment_Mode"].astype(str).str.strip().str.title()
        self.df["Category"] = self.df["Category"].astype(str).str.strip().str.title()
        self.df["Invoice_Number"] = self.df["Invoice_Number"].astype(str).str.strip()
        self.df["Txn_Type"] = self.df["Txn_Type"].astype(str).str.strip().str.title()
        self.df.reset_index(drop=True, inplace=True)

        # Initialize flag columns
        self.df["Flag_Duplicate_Invoice"]  = False
        self.df["Flag_Cash_Limit"]         = False
        self.df["Flag_Structured_Payment"] = False
        self.df["Flag_Anomaly"]            = False
        self.df["Anomaly_Score"]           = 0.0
        self.df["Suggested_Amount"]        = np.nan  # for outlier replacement
        self.df["Overall_Flag"]            = False

        return self.df

    def run_compliance_rules(self):
        df = self.df

        # ── RULE 1: Duplicate Invoice ─────────────────────────────────────────
        # Only flag if SAME invoice appears more than once AND both are same
        # transaction type (both Debit or both Credit).
        # If one is Debit and other is Credit = return/cancel = NOT a duplicate.
        inv_groups = df.groupby("Invoice_Number")
        for inv, group in inv_groups:
            if inv in ["Unknown", "nan", "", "0"]:
                continue
            if len(group) < 2:
                continue

            # Check transaction types in this group
            types = group["Txn_Type"].str.lower().tolist()
            has_debit  = any(t in ["debit", "dr", "purchase", "expense"] for t in types)
            has_credit = any(t in ["credit", "cr", "return", "refund", "cancel"] for t in types)

            # If mix of debit+credit = return scenario = NOT duplicate
            if has_debit and has_credit:
                continue

            # Same type appearing multiple times = genuine duplicate
            if len(group) >= 2:
                self.df.loc[group.index, "Flag_Duplicate_Invoice"] = True

        # ── RULE 2: Cash Limit Per Vendor Per Day ─────────────────────────────
        # Sum ALL cash transactions for same vendor on same date.
        # If total > 10000 that day = flag ALL those transactions.
        # (Not per single transaction - per daily total)
        cash_df = df[df["Payment_Mode"].str.lower().isin(["cash"])].copy()
        cash_df["Date_Only"] = cash_df["Date"].dt.date

        daily_cash = cash_df.groupby(["Vendor_Name", "Date_Only"])["Amount"].sum().reset_index()
        daily_cash.columns = ["Vendor_Name", "Date_Only", "Daily_Cash_Total"]

        # Flag vendors where daily cash total > 10000
        flagged_combos = daily_cash[daily_cash["Daily_Cash_Total"] > 10000]

        for _, row in flagged_combos.iterrows():
            mask = (
                (df["Vendor_Name"] == row["Vendor_Name"]) &
                (df["Date"].dt.date == row["Date_Only"]) &
                (df["Payment_Mode"].str.lower() == "cash")
            )
            self.df.loc[mask, "Flag_Cash_Limit"] = True

        # ── RULE 3: Structured Payments ───────────────────────────────────────
        # Multiple cash payments to same vendor in same month
        # each between 8000-9999 (just below 10000 limit)
        cash_structured = df[
            (df["Payment_Mode"].str.lower() == "cash") &
            (df["Amount"] >= 8000) &
            (df["Amount"] <= 9999)
        ].copy()
        cash_structured["Month_Year"] = cash_structured["Date"].dt.to_period("M")

        struct_groups = cash_structured.groupby(["Vendor_Name", "Month_Year"])
        for (vendor, month), group in struct_groups:
            if len(group) >= 2:
                self.df.loc[group.index, "Flag_Structured_Payment"] = True

        return self.df

    def run_anomaly_detection(self):
        df = self.df
        if len(df) < 10:
            return self.df

        try:
            from sklearn.ensemble import IsolationForest

            # Features for anomaly detection
            df["Month"]       = df["Date"].dt.month
            df["DayOfWeek"]   = df["Date"].dt.dayofweek
            df["Vendor_Freq"] = df["Vendor_Name"].map(df["Vendor_Name"].value_counts())

            cat_avg = df.groupby("Category")["Amount"].transform("mean")
            df["Cat_Spend_Ratio"] = df["Amount"] / (cat_avg + 1)

            features = df[["Amount", "Month", "DayOfWeek", "Vendor_Freq", "Cat_Spend_Ratio"]].fillna(0)

            model = IsolationForest(
                contamination=0.08,
                n_estimators=100,
                random_state=42
            )
            preds  = model.fit_predict(features)
            scores = model.score_samples(features)

            # Normalize scores to 0-100
            min_s, max_s = scores.min(), scores.max()
            norm_scores = 100 * (1 - (scores - min_s) / (max_s - min_s + 1e-9))

            self.df["Anomaly_Score"] = norm_scores.round(2)
            self.df["Flag_Anomaly"]  = preds == -1

            # ── KEY FIX: Replace outlier amount with category average ─────────
            # Instead of just flagging, suggest what the amount SHOULD be
            category_avg = df.groupby("Category")["Amount"].median()
            for idx in self.df[self.df["Flag_Anomaly"]].index:
                cat = self.df.loc[idx, "Category"]
                avg = category_avg.get(cat, df["Amount"].median())
                self.df.loc[idx, "Suggested_Amount"] = round(avg, 2)

        except ImportError:
            # Fallback: Z-score method if sklearn not available
            mean_amt = df["Amount"].mean()
            std_amt  = df["Amount"].std()
            z_scores = ((df["Amount"] - mean_amt) / (std_amt + 1e-9)).abs()
            self.df["Flag_Anomaly"]  = z_scores > 2.5
            self.df["Anomaly_Score"] = (z_scores * 20).clip(0, 100).round(2)

            category_avg = df.groupby("Category")["Amount"].median()
            for idx in self.df[self.df["Flag_Anomaly"]].index:
                cat = self.df.loc[idx, "Category"]
                avg = category_avg.get(cat, mean_amt)
                self.df.loc[idx, "Suggested_Amount"] = round(avg, 2)

        return self.df

    def calculate_vendor_risk(self):
        df = self.df
        vendors = df["Vendor_Name"].unique()
        vendor_risk = []

        for vendor in vendors:
            vdf = df[df["Vendor_Name"] == vendor]
            total = len(vdf)
            if total == 0:
                continue

            flagged = vdf["Overall_Flag"].sum()

            compliance_pct = (
                (vdf["Flag_Cash_Limit"].sum() + vdf["Flag_Structured_Payment"].sum()) / total * 100
            )
            duplicate_pct = vdf["Flag_Duplicate_Invoice"].sum() / total * 100
            anomaly_pct   = vdf["Flag_Anomaly"].sum() / total * 100

            risk_score = (
                0.40 * compliance_pct +
                0.30 * duplicate_pct  +
                0.30 * anomaly_pct
            )
            risk_score = min(round(risk_score, 2), 100)

            if risk_score >= 60:   risk_level = "High"
            elif risk_score >= 30: risk_level = "Medium"
            else:                  risk_level = "Low"

            vendor_risk.append({
                "Vendor_Name":          vendor,
                "Total_Transactions":   total,
                "Total_Amount":         round(vdf["Amount"].sum(), 2),
                "Flagged_Transactions": int(flagged),
                "Compliance_Score":     round(compliance_pct, 2),
                "Duplicate_Score":      round(duplicate_pct, 2),
                "Anomaly_Score":        round(anomaly_pct, 2),
                "Risk_Score":           risk_score,
                "Risk_Level":           risk_level,
            })

        return sorted(vendor_risk, key=lambda x: x["Risk_Score"], reverse=True)

    def generate_insights(self, summary, vendor_risk):
        insights = []
        s = summary

        if s["total_flagged"] == 0:
            insights.append("No suspicious transactions found. All records appear clean.")
            return insights

        flag_pct = s["flag_rate"]
        if flag_pct > 20:
            insights.append(f"HIGH ALERT: {flag_pct}% of transactions are flagged - immediate review required.")
        elif flag_pct > 10:
            insights.append(f"WARNING: {flag_pct}% of transactions flagged - review recommended.")
        else:
            insights.append(f"Low risk: Only {flag_pct}% of transactions flagged.")

        if s["duplicate_invoices"] > 0:
            insights.append(
                f"{s['duplicate_invoices']} duplicate invoices detected (excluding credit/debit pairs). "
                f"Possible double payment or billing fraud."
            )

        if s["cash_violations"] > 0:
            insights.append(
                f"{s['cash_violations']} transactions where daily cash total to a vendor exceeds Rs 10,000. "
                f"This violates Section 40A(3) of the Income Tax Act."
            )

        if s["structured_payments"] > 0:
            insights.append(
                f"{s['structured_payments']} structured cash payments found (Rs 8000-9999 range). "
                f"Possible attempt to avoid the Rs 10,000 cash limit."
            )

        if s["ai_anomalies"] > 0:
            insights.append(
                f"AI detected {s['ai_anomalies']} unusual transactions. "
                f"Suggested amounts based on category averages are shown in the flagged table."
            )

        high_risk = [v for v in vendor_risk if v["Risk_Level"] == "High"]
        if high_risk:
            names = ", ".join([v["Vendor_Name"] for v in high_risk[:3]])
            insights.append(f"High risk vendors: {names}. Detailed investigation recommended.")

        return insights

    def prepare_chart_data(self):
        df = self.df
        charts = {}

        # Monthly trend
        monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum()
        charts["monthly_trend"] = {
            "labels": [str(p) for p in monthly.index],
            "values": monthly.values.tolist()
        }

        # Category spend
        cat = df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(8)
        charts["category_spend"] = {
            "labels": cat.index.tolist(),
            "values": cat.values.tolist()
        }

        # Payment mode
        pm = df["Payment_Mode"].value_counts()
        charts["payment_mode"] = {
            "labels": pm.index.tolist(),
            "values": pm.values.tolist()
        }

        # Top vendors by amount
        tv = df.groupby("Vendor_Name")["Amount"].sum().sort_values(ascending=False).head(8)
        charts["top_vendors"] = {
            "labels": tv.index.tolist(),
            "values": tv.values.tolist()
        }

        # Flag distribution
        charts["flag_distribution"] = {
            "Duplicate Invoice":  int(df["Flag_Duplicate_Invoice"].sum()),
            "Cash Limit":         int(df["Flag_Cash_Limit"].sum()),
            "Structured Payment": int(df["Flag_Structured_Payment"].sum()),
            "AI Anomaly":         int(df["Flag_Anomaly"].sum()),
        }

        # Risk distribution
        charts["risk_distribution"] = {
            "High":   0,
            "Medium": 0,
            "Low":    0
        }

        return charts

    def run_full_audit(self):
        self.load_and_preprocess()
        self.run_compliance_rules()
        self.run_anomaly_detection()

        # Set overall flag
        self.df["Overall_Flag"] = (
            self.df["Flag_Duplicate_Invoice"] |
            self.df["Flag_Cash_Limit"]        |
            self.df["Flag_Structured_Payment"] |
            self.df["Flag_Anomaly"]
        )

        vendor_risk = self.calculate_vendor_risk()

        # Summary
        total  = len(self.df)
        flagged = int(self.df["Overall_Flag"].sum())
        summary = {
            "total_transactions":  total,
            "total_flagged":       flagged,
            "total_amount":        round(self.df["Amount"].sum(), 2),
            "flag_rate":           round(flagged / total * 100, 2) if total > 0 else 0,
            "duplicate_invoices":  int(self.df["Flag_Duplicate_Invoice"].sum()),
            "cash_violations":     int(self.df["Flag_Cash_Limit"].sum()),
            "structured_payments": int(self.df["Flag_Structured_Payment"].sum()),
            "ai_anomalies":        int(self.df["Flag_Anomaly"].sum()),
            "high_risk_vendors":   len([v for v in vendor_risk if v["Risk_Level"] == "High"]),
        }

        # Suspicious transactions list
        flagged_df = self.df[self.df["Overall_Flag"]].copy()
        suspicious = []
        for idx, row in flagged_df.iterrows():
            reasons = []
            if row["Flag_Duplicate_Invoice"]:  reasons.append("Duplicate Invoice")
            if row["Flag_Cash_Limit"]:         reasons.append("Cash Limit Breach")
            if row["Flag_Structured_Payment"]: reasons.append("Structured Payment")
            if row["Flag_Anomaly"]:            reasons.append("AI Anomaly")

            suggested = ""
            if not pd.isna(row["Suggested_Amount"]):
                suggested = row["Suggested_Amount"]

            suspicious.append({
                "row":             int(idx) + 1,
                "date":            str(row["Date"].date()),
                "invoice":         row["Invoice_Number"],
                "vendor":          row["Vendor_Name"],
                "amount":          row["Amount"],
                "suggested_amount":suggested,
                "mode":            row["Payment_Mode"],
                "category":        row["Category"],
                "txn_type":        row["Txn_Type"],
                "anomaly_score":   row["Anomaly_Score"],
                "reasons":         reasons,
            })

        insights = self.generate_insights(summary, vendor_risk)
        charts   = self.prepare_chart_data()

        return {
            "summary":                 summary,
            "suspicious_transactions": suspicious,
            "vendor_risk":             vendor_risk,
            "insights":                insights,
            "charts":                  charts,
        }
