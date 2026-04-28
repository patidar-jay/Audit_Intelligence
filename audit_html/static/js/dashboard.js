// dashboard.js — All dashboard logic

const user = requireAuth();
fillSidebarUser();

let auditResults = null;
let allTxns = [];
let allVendors = [];

// ── Drag and drop upload ─────────────────────────────────────────────────────
const zone = document.getElementById("upload-zone");
zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("dragover"); });
zone.addEventListener("dragleave", ()  => zone.classList.remove("dragover"));
zone.addEventListener("drop", e => {
  e.preventDefault(); zone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

function handleFileSelect(input) {
  if (input.files[0]) uploadFile(input.files[0]);
}

function downloadSample() {
  window.location.href = "/api/sample-data";
}

async function runDemo() {
  const res  = await fetch("/api/sample-data");
  const blob = await res.blob();
  const file = new File([blob], "sample_transactions.csv", { type: "text/csv" });
  uploadFile(file);
}

// ── Upload and run audit ─────────────────────────────────────────────────────
async function uploadFile(file) {
  const exts = [".csv",".xlsx",".xls"];
  const ext  = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!exts.includes(ext)) { toast("Only CSV and Excel files allowed.", "error"); return; }

  // Show progress
  const progSection = document.getElementById("progress-section");
  const progBar     = document.getElementById("progress-bar");
  const progLabel   = document.getElementById("progress-label");
  const alertEl     = document.getElementById("main-alert");
  alertEl.style.display = "none";
  progSection.style.display = "block";

  function setProgress(pct, label) {
    progBar.style.width = pct + "%";
    progLabel.textContent = label;
  }

  setProgress(10, "Uploading file...");
  setLoading(true, "Running AI Audit Pipeline...");

  try {
    setProgress(30, "Running compliance rules...");
    await new Promise(r => setTimeout(r, 100));
    setProgress(60, "Running Isolation Forest AI...");

    const form = new FormData();
    form.append("file", file);
    form.append("user_id", user.id || 1);

    const data = await api("/api/audit", "POST", form, true);
    setProgress(100, "✅ Done!");
    auditResults = data.results;

    await new Promise(r => setTimeout(r, 400));
    progSection.style.display = "none";

    // Show success alert
    const s = auditResults.summary;
    alertEl.className = "alert alert-success mb-16";
    alertEl.textContent = `✅ Audit complete! ${fmtNum(s.total_transactions)} transactions analyzed — ${s.total_flagged} flagged (${s.flag_rate}%).`;
    alertEl.style.display = "block";

    renderResults(auditResults);
    toast("Audit complete!", "success");

  } catch(e) {
    progSection.style.display = "none";
    alertEl.className = "alert alert-error mb-16";
    alertEl.textContent = "❌ Audit failed: " + e.message;
    alertEl.style.display = "block";
    toast("Audit failed!", "error");
  } finally {
    setLoading(false);
  }
}

// ── Render all results ───────────────────────────────────────────────────────
function renderResults(results) {
  document.getElementById("landing-section").style.display = "none";
  document.getElementById("results-section").style.display = "block";
  initTabs();

  const s = results.summary;
  allTxns    = results.suspicious_transactions || [];
  allVendors = results.vendor_risk || [];

  // KPIs
  const kpis = [
    { label:"Transactions",      value: fmtNum(s.total_transactions), sub:"Total analyzed",       cls:"cyan"    },
    { label:"Total Amount",      value: fmtINR(s.total_amount),       sub:"Sum of all amounts",   cls:"green"   },
    { label:"Flagged",           value: s.total_flagged,              sub: s.flag_rate+"% rate",  cls:"danger"  },
    { label:"High Risk Vendors", value: s.high_risk_vendors,          sub:"Need investigation",   cls:"warning" },
    { label:"Duplicate Invoices",value: s.duplicate_invoices,         sub:"Same type duplicates", cls:"danger"  },
    { label:"Cash Violations",   value: s.cash_violations,            sub:"Daily total >Rs 10K",  cls:"warning" },
    { label:"Structured Pmts",   value: s.structured_payments,        sub:"Rs 8K-9.9K pattern",   cls:"purple"  },
    { label:"AI Anomalies",      value: s.ai_anomalies,               sub:"Isolation Forest",     cls:"cyan"    },
  ];
  document.getElementById("kpi-grid").innerHTML = kpis.map(k => `
    <div class="kpi-card ${k.cls}">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>`).join("");

  // Insights
  const ins = results.insights || [];
  document.getElementById("insights-container").innerHTML = ins.map(i =>
    `<div class="insight-card">${i}</div>`).join("") || "<p style='color:var(--muted)'>No insights generated.</p>";

  // Charts - overview
  const fd = results.charts?.flag_distribution || {};
  drawBarChart("chart-flags",   Object.keys(fd),  Object.values(fd), "#ef4444");
  const pm = results.charts?.payment_mode || {};
  drawBarChart("chart-payment", pm.labels||[], pm.values||[], "#00d4ff");

  // PDF button
  document.getElementById("pdf-btn").style.display = s.total_flagged > 0 ? "inline-flex" : "none";

  // Flagged transactions table
  renderTxnTable(allTxns);

  // Vendor risk table
  renderVendorTable(allVendors);

  // Analytics charts
  const mt = results.charts?.monthly_trend || {};
  drawLineChart("chart-monthly",   mt.labels||[], mt.values||[], "#00d4ff");
  const cs = results.charts?.category_spend || {};
  drawBarChart("chart-category",   cs.labels||[], cs.values||[], "#7c3aed");
  const tv = results.charts?.top_vendors || {};
  drawBarChart("chart-vendors",    tv.labels||[], tv.values||[], "#10b981");
}

// ── Flagged Transactions Table ───────────────────────────────────────────────
function renderTxnTable(txns) {
  const tbody = document.getElementById("txn-tbody");
  const count = document.getElementById("txn-count");
  count.textContent = txns.length + " transactions shown";
  tbody.innerHTML = txns.map(t => {
    const flags = (t.reasons || []).map(flagBadge).join(" ");
    const scoreColor = t.anomaly_score > 70 ? "#fca5a5" : t.anomaly_score > 40 ? "#fcd34d" : "var(--muted)";
    const suggested  = t.suggested_amount ? `<span style="color:#10b981">Rs ${parseFloat(t.suggested_amount).toLocaleString()}</span>` : "—";
    return `<tr data-flags='${JSON.stringify(t.reasons||[])}' data-vendor='${t.vendor}' data-invoice='${t.invoice}'>
      <td>${t.row}</td>
      <td>${t.date}</td>
      <td>${t.invoice}</td>
      <td><strong>${t.vendor}</strong></td>
      <td><span class="badge ${t.txn_type==='Credit'?'badge-success':'badge-cyan'}">${t.txn_type||'Debit'}</span></td>
      <td>Rs ${parseFloat(t.amount).toLocaleString()}</td>
      <td>${suggested}</td>
      <td>${t.mode}</td>
      <td>${t.category}</td>
      <td style="color:${scoreColor};font-weight:700">${parseFloat(t.anomaly_score).toFixed(1)}</td>
      <td>${flags}</td>
    </tr>`;
  }).join("") || "<tr><td colspan='11' style='text-align:center;color:var(--muted);padding:24px'>No flagged transactions</td></tr>";
  initSortableTable("txn-table");
}

function filterTxnTable() {
  const search     = document.getElementById("txn-search").value.toLowerCase();
  const flagFilter = document.getElementById("flag-filter").value;
  let filtered = allTxns.filter(t => {
    const matchSearch = !search ||
      t.vendor.toLowerCase().includes(search) ||
      t.invoice.toLowerCase().includes(search);
    const matchFlag = !flagFilter || (t.reasons||[]).includes(flagFilter);
    return matchSearch && matchFlag;
  });
  renderTxnTable(filtered);
}

// ── Vendor Risk Table ────────────────────────────────────────────────────────
function renderVendorTable(vendors) {
  // Risk summary badges
  const h = vendors.filter(v=>v.Risk_Level==="High").length;
  const m = vendors.filter(v=>v.Risk_Level==="Medium").length;
  const l = vendors.filter(v=>v.Risk_Level==="Low").length;
  document.getElementById("risk-summary").innerHTML = `
    <span class="badge badge-danger">🔴 High: ${h}</span>
    <span class="badge badge-warning">🟡 Medium: ${m}</span>
    <span class="badge badge-success">🟢 Low: ${l}</span>`;

  const tbody = document.getElementById("vendor-tbody");
  tbody.innerHTML = vendors.map(v => {
    const sc = v.Risk_Score || 0;
    const color = scoreColor(sc);
    return `<tr data-level='${v.Risk_Level}' data-vendor='${v.Vendor_Name}'>
      <td><strong>${v.Vendor_Name}</strong></td>
      <td>${v.Total_Transactions}</td>
      <td>Rs ${parseFloat(v.Total_Amount).toLocaleString()}</td>
      <td>${v.Flagged_Transactions}</td>
      <td>
        <div class="score-bar-wrap">
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:${sc}%;background:${color}"></div>
          </div>
          <span style="color:${color};font-weight:700;min-width:40px">${sc}/100</span>
        </div>
      </td>
      <td>${riskBadge(v.Risk_Level)}</td>
    </tr>`;
  }).join("") || "<tr><td colspan='6' style='text-align:center;color:var(--muted);padding:24px'>No vendor data</td></tr>";
  initSortableTable("vendor-table");
}

function filterVendorTable() {
  const search = document.getElementById("vendor-search").value.toLowerCase();
  const high   = document.getElementById("chk-high").checked;
  const med    = document.getElementById("chk-med").checked;
  const low    = document.getElementById("chk-low").checked;
  const filtered = allVendors.filter(v => {
    const matchSearch = !search || v.Vendor_Name.toLowerCase().includes(search);
    const matchLevel  = (v.Risk_Level==="High"&&high)||(v.Risk_Level==="Medium"&&med)||(v.Risk_Level==="Low"&&low);
    return matchSearch && matchLevel;
  });
  renderVendorTable(filtered);
}

// ── Export full CSV ──────────────────────────────────────────────────────────
function exportFullCSV() {
  if (!allTxns.length) { toast("No data to export.", "error"); return; }
  const headers = ["Row","Date","Invoice","Vendor","Txn_Type","Amount","Suggested_Amount","Mode","Category","AI_Score","Flags"];
  const rows = allTxns.map(t => [
    t.row, t.date, t.invoice, t.vendor, t.txn_type||"Debit",
    t.amount, t.suggested_amount||"", t.mode, t.category,
    t.anomaly_score, (t.reasons||[]).join("|")
  ]);
  const csv = [headers, ...rows].map(r => r.map(c => '"'+String(c).replace(/"/g,'""')+'"').join(",")).join("\n");
  const blob = new Blob([csv], {type:"text/csv"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "full_audit_report.csv"; a.click();
  toast("CSV downloaded!", "success");
}

// ── PDF Download ─────────────────────────────────────────────────────────────
async function downloadPDF() {
  toast("PDF generation requires fpdf2. Install: pip install fpdf2", "info");
}
